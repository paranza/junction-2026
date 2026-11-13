#!/usr/bin/env python3
"""Evaluate Trace against frozen, evaluation-only Stoa preview questions.

Native mode is the default and never requests an API model. Gold answers are
read only by this process. The /api/ask request contains no labels or scores.
Text responses require manual review; evidence checks validate geometry syntax,
not whether a citation proves the answer.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time
from urllib import error, parse, request


HERE = Path(__file__).resolve().parent
ABSTENTION_STATUSES = {
    "unsupported", "abstained", "insufficient_evidence", "unavailable", "error",
    "needs_input", "clarification_required", "not_found", "not_supported",
}
NUMERIC_TYPES = {"count", "area", "length", "volume"}
ENGLISH_PREFIX = re.compile(
    r"^(?:How\b|What\b|Which\b|On\b|In\b|Calculate\b|List\b|Describe\b|"
    r"Where\b|Does\b|Do\b|Can\b|Could\b|Are\b|Is\b|Give\b|Find\b|"
    r"Total\b|Count\b|Provide\b|Identify\b|Summarize\b|Based\b|According\b|For\b)"
)
# A factor converts the unit to its dimension's SI base. Counts have no scaling.
UNITS = {
    "count": ("count", 1), "counts": ("count", 1), "unit": ("count", 1),
    "units": ("count", 1), "each": ("count", 1),
    "m": ("length", 1), "meter": ("length", 1), "meters": ("length", 1),
    "metre": ("length", 1), "metres": ("length", 1),
    "mm": ("length", .001), "cm": ("length", .01),
    "ft": ("length", .3048), "foot": ("length", .3048), "feet": ("length", .3048),
    "in": ("length", .0254), "inch": ("length", .0254), "inches": ("length", .0254),
    "m2": ("area", 1), "sqm": ("area", 1), "squaremeter": ("area", 1),
    "squaremeters": ("area", 1), "squaremetre": ("area", 1), "squaremetres": ("area", 1),
    "mm2": ("area", .000001), "cm2": ("area", .0001),
    "ft2": ("area", .09290304), "sqft": ("area", .09290304),
    "sf": ("area", .09290304), "squarefoot": ("area", .09290304),
    "squarefeet": ("area", .09290304),
    "m3": ("volume", 1), "cubicmeter": ("volume", 1), "cubicmeters": ("volume", 1),
    "cubicmetre": ("volume", 1), "cubicmetres": ("volume", 1),
    "ft3": ("volume", .028316846592), "cubicfeet": ("volume", .028316846592),
    "cm3": ("volume", .000001), "l": ("volume", .001), "litre": ("volume", .001),
}


def canonical_hash(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_manifest(path, dataset_root=None):
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = manifest.get("cases", [])
    if not cases or canonical_hash(cases) != manifest.get("cases_sha256"):
        raise ValueError("Manifest is empty or its frozen case hash does not match")
    ids, keys = set(), set()
    for case in cases:
        for field in ("id", "path", "question", "expected", "unit", "type", "source", "group", "source_line", "suites"):
            if field not in case:
                raise ValueError(f"Manifest case is missing {field}")
        if not ENGLISH_PREFIX.match(case["question"]):
            raise ValueError(f"Question does not pass frozen English selection rule: {case['id']}")
        key = (case["path"], case["question"])
        if case["id"] in ids or key in keys:
            raise ValueError("Duplicate case ID or exact path/question in manifest")
        ids.add(case["id"])
        keys.add(key)
        if case["type"] not in NUMERIC_TYPES | {"text"}:
            raise ValueError(f"Unknown question type: {case['type']}")
    root = Path(dataset_root or manifest["dataset"]["root"]).expanduser()
    label_path = root / manifest["dataset"]["questions_path"]
    validation = {"manifest_hash_valid": True, "local_labels_checked": False, "missing_drawing_paths": []}
    if label_path.is_file():
        raw = label_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest["dataset"]["questions_sha256"]:
            raise ValueError("Local questions.jsonl differs from the frozen preview source")
        labels = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        for case in cases:
            row = labels[case["source_line"] - 1]
            expected = {"path": case["path"], "question": case["question"], "answer": case["expected"],
                        "unit": case["unit"], "type": case["type"]}
            if row != expected:
                raise ValueError(f"Frozen case no longer matches its source row: {case['id']}")
        validation["local_labels_checked"] = True
        validation["missing_drawing_paths"] = sorted({c["path"] for c in cases if not (root / c["path"]).is_file()})
    else:
        validation["note"] = "Local labels are unavailable; evaluating self-contained frozen manifest."
    return manifest, validation


def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, str):
        value = value.strip()
        if re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", value):
            value = value.replace(",", "")
        if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value):
            result = float(value)
            return result if math.isfinite(result) else None
    return None


def unit_spec(unit):
    if not isinstance(unit, str):
        return None
    key = unit.casefold().replace("²", "2").replace("³", "3").replace("^", "")
    key = re.sub(r"[\s._-]+", "", key)
    return UNITS.get(key)


def score(case, response, tolerance=.02):
    status = str(response.get("status", "")).casefold()
    abstained = status in ABSTENTION_STATUSES
    if case["type"] == "text":
        answered = bool(str(response.get("answer") or "").strip()) and not abstained
        return {"answered": answered, "correct": None, "outcome": "manual_review" if answered else "unanswered",
                "reason": "Free-form text is excluded from automatic accuracy; a human must compare it to the label."}
    supplied = response.get("value")
    answered = supplied is not None and not abstained
    if not answered:
        return {"answered": False, "correct": False, "outcome": "unanswered"}
    actual, expected = number(supplied), number(case["expected"])
    if actual is None or expected is None:
        return {"answered": True, "correct": False, "outcome": "invalid_numeric_value"}
    actual_unit, expected_unit = unit_spec(response.get("unit")), unit_spec(case["unit"])
    if case["type"] == "count" and response.get("unit") in (None, ""):
        actual_unit = ("count", 1)
    if not actual_unit or not expected_unit:
        return {"answered": True, "correct": False, "outcome": "missing_or_unknown_unit"}
    if actual_unit[0] != expected_unit[0] or actual_unit[0] != case["type"]:
        return {"answered": True, "correct": False, "outcome": "incompatible_unit"}
    converted = actual * actual_unit[1] / expected_unit[1]
    absolute_error = abs(converted - expected)
    if case["type"] == "count":
        correct = converted == expected and converted.is_integer()
        threshold = 0
    else:
        # Zero labels cannot use relative error. Only a numerical zero matches.
        threshold = abs(expected) * tolerance if expected else 1e-9
        correct = absolute_error <= threshold + (1e-12 if expected else 0)
    return {"answered": True, "correct": correct, "outcome": "correct" if correct else "incorrect",
            "value_in_expected_unit": converted, "absolute_error": absolute_error,
            "relative_error": absolute_error / abs(expected) if expected else None,
            "allowed_absolute_error": threshold}


def finite_coordinate(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1


def valid_box(box):
    return (isinstance(box, (list, tuple)) and len(box) == 4 and all(finite_coordinate(x) for x in box)
            and box[0] < box[2] and box[1] < box[3])


def valid_polygon(poly):
    if not isinstance(poly, (list, tuple)) or len(poly) < 3:
        return False
    if not all(isinstance(p, (list, tuple)) and len(p) == 2 and all(finite_coordinate(v) for v in p) for p in poly):
        return False
    area2 = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                for i in range(len(poly)))
    return abs(area2) > 1e-12


def validate_evidence(response):
    evidence = response.get("evidence", [])
    result = {"items": 0, "valid_boxes": 0, "invalid_boxes": 0, "valid_polygons": 0,
              "invalid_polygons": 0, "items_without_geometry": 0, "items_with_source_id": 0,
              "invalid_pages": 0, "non_object_items": 0, "duplicate_source_ids": 0,
              "polygon_outside_bbox": 0, "schema_valid": isinstance(evidence, list)}
    if not isinstance(evidence, list):
        return result
    seen = set()
    for item in evidence:
        result["items"] += 1
        if not isinstance(item, dict):
            result["non_object_items"] += 1
            continue
        box, poly = item.get("bbox"), item.get("polygon")
        if box is not None:
            result["valid_boxes" if valid_box(box) else "invalid_boxes"] += 1
        if poly is not None:
            result["valid_polygons" if valid_polygon(poly) else "invalid_polygons"] += 1
        if box is None and poly is None:
            result["items_without_geometry"] += 1
        if valid_box(box) and valid_polygon(poly):
            if any(not (box[0] - 1e-6 <= x <= box[2] + 1e-6 and box[1] - 1e-6 <= y <= box[3] + 1e-6) for x, y in poly):
                result["polygon_outside_bbox"] += 1
        page = item.get("page")
        if (box is not None or poly is not None) and (not isinstance(page, int) or isinstance(page, bool) or page < 1):
            result["invalid_pages"] += 1
        source_id = item.get("guid") or item.get("id") or item.get("object_id")
        if source_id:
            result["items_with_source_id"] += 1
            identity = (str(item.get("source_path") or ""), str(source_id))
            result["duplicate_source_ids"] += identity in seen
            seen.add(identity)
    result["geometry_present"] = result["valid_boxes"] + result["invalid_boxes"] + result["valid_polygons"] + result["invalid_polygons"] > 0
    result["geometry_valid"] = not any(result[k] for k in ("invalid_boxes", "invalid_polygons", "invalid_pages", "non_object_items", "polygon_outside_bbox"))
    return result


def http_json(base_url, path, payload=None, timeout=180):
    body = json.dumps(payload).encode() if payload is not None else None
    req = request.Request(base_url.rstrip("/") + path, data=body,
                          headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        with request.urlopen(req, timeout=timeout) as reply:
            result = json.load(reply)
    except error.HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from None
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Backend request failed: {exc}") from None
    if not isinstance(result, dict):
        raise RuntimeError("Backend returned a non-object JSON response")
    return result


def document_map(base_url, timeout):
    documents, offset = {}, 0
    while True:
        query = parse.urlencode({"search": "", "limit": 200, "offset": offset})
        result = http_json(base_url, "/api/documents?" + query, timeout=timeout)
        batch = result.get("documents")
        if not isinstance(batch, list):
            raise RuntimeError("Document listing lacks a documents array")
        for doc in batch:
            if isinstance(doc, dict) and doc.get("path") and doc.get("id"):
                documents[doc["path"]] = doc
        offset += len(batch)
        if not batch or offset >= result.get("total", offset):
            break
    return documents


def aggregate(results):
    numeric = [r for r in results if r["type"] in NUMERIC_TYPES]
    answered = [r for r in results if r["score"]["answered"]]
    answered_numeric = [r for r in numeric if r["score"]["answered"]]
    correct = sum(r["score"]["correct"] is True for r in numeric)
    latency = sorted(r["client_duration_ms"] for r in results if r.get("request_attempted"))
    geometry = [r["evidence_validation"] for r in results]
    return {
        "cases": len(results), "answered": len(answered),
        "coverage": len(answered) / len(results) if results else None,
        "numeric_cases": len(numeric), "numeric_answered": len(answered_numeric), "numeric_correct": correct,
        "accuracy_all": correct / len(numeric) if numeric else None,
        "accuracy_answered": correct / len(answered_numeric) if answered_numeric else None,
        "accuracy_definition": "Numeric cases only; all includes unanswered and failed cases as incorrect. Free text requires manual review.",
        "text_cases": sum(r["type"] == "text" for r in results),
        "text_answered_for_manual_review": sum(r["type"] == "text" and r["score"]["answered"] for r in results),
        "review_flagged_answers": sum(r.get("response", {}).get("status") == "needs_review" and r["score"]["answered"] for r in results),
        "errors": sum(bool(r.get("error")) for r in results),
        "methods": dict(Counter(str(r.get("response", {}).get("method", "none")) for r in results)),
        "statuses": dict(Counter(str(r.get("response", {}).get("status", "no_response")) for r in results)),
        "latency_ms": {"requests": len(latency), "total": round(sum(latency), 2),
                       "p50": round(statistics.median(latency), 2) if latency else None,
                       "p95": round(latency[max(0, math.ceil(.95 * len(latency)) - 1)], 2) if latency else None},
        "evidence": {"items": sum(e["items"] for e in geometry),
                     "answers_with_evidence": sum(e["items"] > 0 for e in geometry),
                     "answers_with_geometry": sum(e.get("geometry_present", False) for e in geometry),
                     "answers_with_invalid_geometry": sum(not e.get("geometry_valid", e["schema_valid"]) for e in geometry),
                     "items_without_geometry": sum(e["items_without_geometry"] for e in geometry),
                     "human_verified_citation_correctness": None,
                     "note": "Only normalized geometry syntax and source-ID structure were checked; reference truth and detection completeness were not verified."},
    }


def grouped(results, key):
    groups = defaultdict(list)
    for result in results:
        groups[result[key]].append(result)
    return {name: aggregate(items) for name, items in sorted(groups.items())}


def markdown_report(report):
    lines = ["# Trace dataset benchmark", "", f"Mode: **{report['mode']}**. Suite: **{report['suite']}**. Frozen manifest: `{report['manifest_sha256']}`.", "",
             "Gold answers were used only by the evaluator. Text needs manual review. Geometry validation does not establish citation correctness.", ""]
    if report.get("dry_run"):
        return "\n".join(lines + ["Dry run only. No backend or model requests were made.", "", f"Selected cases: {report['selected_cases']}", ""])
    if report.get("setup_error"):
        return "\n".join(lines + [f"Backend setup error: {report['setup_error']}", "", "No question requests were made.", ""])
    def pct(value):
        return "n/a" if value is None else f"{value:.1%}"
    summary = report["summary"]
    lines += [f"Answered {summary['answered']}/{summary['cases']} ({pct(summary['coverage'])}). Numeric accuracy: {pct(summary['accuracy_all'])} across all numeric cases; {pct(summary['accuracy_answered'])} across answered numeric cases.",
              f"Text cases: {summary['text_cases']}, answered for manual review: {summary['text_answered_for_manual_review']}. Request latency p50/p95: {summary['latency_ms']['p50']} / {summary['latency_ms']['p95']} ms.", "",
              "| Source | Cases | Coverage | Numeric correct/all | Numeric accuracy answered |", "|---|---:|---:|---:|---:|"]
    for name, stats in report["by_source"].items():
        lines.append(f"| {name} | {stats['cases']} | {pct(stats['coverage'])} | {stats['numeric_correct']}/{stats['numeric_cases']} | {pct(stats['accuracy_answered'])} |")
    lines += ["", "| Type | Cases | Coverage | Correct/all numeric |", "|---|---:|---:|---:|"]
    for name, stats in report["by_type"].items():
        lines.append(f"| {name} | {stats['cases']} | {pct(stats['coverage'])} | {stats['numeric_correct']}/{stats['numeric_cases']} |")
    lines += ["", "## Case results", "", "| Case | Source line | Outcome | Method | Milliseconds |", "|---|---:|---|---|---:|"]
    for item in report["results"]:
        lines.append(f"| {item['id']} | {item['source_line']} | {item['score']['outcome']} | {item.get('response', {}).get('method', 'none')} | {item['client_duration_ms']:.1f} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=HERE / "benchmark-config.json")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--dataset-root", help="Optional local dataset location for source-label validation")
    parser.add_argument("--mode", choices=("native", "auto", "vision"), default="native")
    parser.add_argument("--suite", choices=("full", "native-smoke", "raster"), default="full")
    parser.add_argument("--case-id", action="append", help="Select a frozen case ID; may be repeated")
    parser.add_argument("--max-questions", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true", help="Validate the frozen selection without any network requests")
    parser.add_argument("--allow-paid", action="store_true", help="Explicit operator opt-in for auto/vision; capped at five questions")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--output", type=Path, help="JSON report path; a readable .md companion is also written")
    args = parser.parse_args(argv)
    if args.max_questions < 1 or args.timeout <= 0:
        parser.error("--max-questions and --timeout must be positive")
    if args.mode != "native" and not args.dry_run and (not args.allow_paid or args.max_questions > 5):
        parser.error("auto/vision may spend API credits: use --allow-paid and --max-questions 5 or fewer")
    try:
        manifest, validation = load_manifest(args.manifest, args.dataset_root)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        print(f"Manifest error: {exc}", file=sys.stderr)
        return 2
    if args.case_id and set(args.case_id) - {c["id"] for c in manifest["cases"]}:
        parser.error("--case-id must refer to an existing frozen manifest case")
    cases = [c for c in manifest["cases"] if (args.suite == "full" or args.suite in c["suites"])
             and (not args.case_id or c["id"] in args.case_id)][:args.max_questions]
    if not cases:
        parser.error("The requested suite/case selection is empty")
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
              "mode": args.mode, "suite": args.suite, "dry_run": args.dry_run,
              "manifest": str(args.manifest.resolve()), "manifest_sha256": manifest["cases_sha256"],
              "base_url": args.base_url, "selected_cases": len(cases), "validation": validation,
              "case_ids": [c["id"] for c in cases], "selected_groups": sorted({c["group"] for c in cases}),
              "selection_by_source_type": dict(Counter(f"{c['source']}/{c['type']}" for c in cases)),
              "evaluation_limits": manifest["evaluation_limits"]}
    exit_code = 0
    if not args.dry_run:
        try:
            documents = document_map(args.base_url, args.timeout)
        except RuntimeError as exc:
            report["setup_error"] = str(exc)
            exit_code = 2
        else:
            results = []
            for index, case in enumerate(cases, 1):
                item = {k: case[k] for k in ("id", "path", "question", "expected", "unit", "type", "source", "group", "source_line")}
                item.update(request_attempted=False, client_duration_ms=0.0)
                response = {}
                doc = documents.get(case["path"])
                if doc is None:
                    item["error"] = "document_not_listed_by_backend"
                else:
                    # Explicit allowlist: gold, type, units, groups and evaluation scores NEVER go to inference.
                    payload = {"document_id": doc["id"], "question": case["question"], "page": 1,
                               "scope": "document", "mode": args.mode}
                    started = time.perf_counter()
                    item["request_attempted"] = True
                    try:
                        response = http_json(args.base_url, "/api/ask", payload, args.timeout)
                    except RuntimeError as exc:
                        item["error"] = str(exc)
                    item["client_duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
                item["response"] = response
                item["score"] = score(case, response, manifest["scoring"]["measurement_relative_tolerance"])
                item["evidence_validation"] = validate_evidence(response)
                results.append(item)
                print(f"[{index}/{len(cases)}] {case['id']}: {item['score']['outcome']}", file=sys.stderr, flush=True)
            report.update(results=results, summary=aggregate(results), by_source=grouped(results, "source"),
                          by_type=grouped(results, "type"), by_group=grouped(results, "group"))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or HERE / "reports" / f"benchmark-{args.mode}-{args.suite}-{timestamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({"report": str(output.resolve()), "selected_cases": len(cases), "dry_run": args.dry_run,
                      **({"summary": report["summary"]} if "summary" in report else {}),
                      **({"setup_error": report["setup_error"]} if "setup_error" in report else {})}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

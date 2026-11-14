#!/usr/bin/env python3
"""Build server/question_templates.json from the wording of the preview questions.

Each translated question sits directly after its English twin in questions.jsonl,
with the same quoted labels, room numbers and apartment letters. This script turns
each pair into a pattern for the translated wording and a format for the English
wording, with the shared values as slots. Only the `path` and `question` fields
are read: answers, types and units never reach the table.

    python ops/build_question_templates.py --dataset-root ~/stoa-data/junction-dataset-preview
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent / "server" / "question_templates.json"
TWIN_SOURCES = {"swiss_dwellings", "ifc_models", "cubicasa5k"}
ENGLISH = re.compile(r"^(?:How|What|Which|On|In|Calculate|List|Describe|Where|Does|Do|Can|Could|Are|Is|Give|Find|"
                     r"Total|Count|Provide|Identify|Summarize|Based|According|For)\b")
QUOTES = (("«", "»"), ("„", "“"), ("“", "”"), ("'", "'"), ('"', '"'))
SINGLE_QUOTE_END = re.compile(r"'(?=[\s?,.)!:;]|$)")
TOKEN = re.compile(r"(?<![\w.])(?:[A-Z]?\d+(?:\.\d+)*|[A-Z])(?!\w)")
TOKEN_PATTERN = r"[A-Z]?\d+(?:\.\d+)*|[A-Z]"


def clean(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def quoted_spans(text):
    """(start, end, inner_start, inner_end) of each quoted label. A label in
    single quotes may contain apostrophes, as in 'Cage d'escalier'."""
    spans, i = [], 0
    while i < len(text):
        for opening, closing in QUOTES:
            if text[i] != opening or (opening == "'" and i and text[i - 1].isalnum()):
                continue
            if opening == "'":
                match = SINGLE_QUOTE_END.search(text, i + 1)
                j = match.start() if match else -1
            else:
                j = text.find(closing, i + 1)
            if j > i:
                a, b = i + 1, j
                while a < b and text[a] == " ":  # French « label »
                    a += 1
                while b > a and text[b - 1] == " ":
                    b -= 1
                spans.append((i, j + 1, a, b))
                i = j
            break
        i += 1
    return spans


def slots(text):
    """Ordered (start, end, value, kind): quoted labels, then numbers and single
    capital letters outside quotes (room numbers, apartment letters)."""
    found, quoted = [], []
    for start, end, a, b in quoted_spans(text):
        found.append((a, b, text[a:b], "label"))
        quoted.append((start, end))
    for match in TOKEN.finditer(text):
        if not any(start <= match.start() < end for start, end in quoted):
            found.append((match.start(), match.end(), match.group(0), "token"))
    return sorted(found)


def pieces(text, index):
    """Split text into literal and slot pieces using a value -> slot index map."""
    out, last = [], 0
    for a, b, value, kind in slots(text):
        if value not in index:
            return None
        out += [("text", text[last:a]), ("slot", index[value], kind)]
        last = b
    return out + [("text", text[last:])]


def as_pattern(parts):
    body = "".join(re.escape(p[1]) if p[0] == "text" else
                   (f"(?P<s{p[1]}>.+?)" if p[2] == "label" else f"(?P<s{p[1]}>{TOKEN_PATTERN})") for p in parts)
    return "^" + body + "$"


def as_format(parts):
    return "".join(p[1].replace("{", "{{").replace("}", "}}") if p[0] == "text" else "{s%d}" % p[1] for p in parts)


def twin_pairs(rows):
    pairs = []
    for english, other in zip(rows, rows[1:]):
        if (english["path"] == other["path"] and english["path"].split("/")[1] in TWIN_SOURCES
                and ENGLISH.match(english["question"]) and not ENGLISH.match(other["question"])):
            pairs.append((clean(english["question"]), clean(other["question"]), english["path"]))
    return pairs


def build(pairs):
    translated, english, failed, conflicts = {}, {}, [], 0
    for en, other, _ in pairs:
        index = {}
        for _, _, value, _ in slots(other):
            index.setdefault(value, len(index))
        en_parts, other_parts = pieces(en, index), pieces(other, index)
        if en_parts is None or other_parts is None or \
                {p[1] for p in en_parts if p[0] == "slot"} != {p[1] for p in other_parts if p[0] == "slot"}:
            failed.append((en, other))
            continue
        pattern, fmt = as_pattern(other_parts), as_format(en_parts)
        entry = translated.setdefault(pattern, {"english": fmt, "examples": 0})
        if entry["english"] != fmt:
            conflicts += 1
            continue
        entry["examples"] += 1
        english.setdefault(as_pattern(en_parts), fmt)
    return translated, english, failed, conflicts


def drawing_group(path):
    source, stem = path.split("/")[1], path.rsplit("/", 1)[-1]
    match = re.match(r"(site\d+_bldg\d+)", stem)
    return source + ":" + (match.group(1) if source == "swiss_dwellings" and match else stem.split("_plan-")[0])


def rewrite(table, question):
    """Mirror of server.normalize.to_english for the build-time checks."""
    text = clean(question)
    for row in table:
        match = re.match(row["pattern"], text)
        if match:
            return row["english"].format(**match.groupdict())
    return None


def ordered(translated):
    rows = [{"pattern": p, **e} for p, e in translated.items()]
    return sorted(rows, key=lambda r: (-len(re.sub(r"\(\?P<s\d+>[^)]*\)", "", r["pattern"])), r["pattern"]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    raw = (args.dataset_root.expanduser() / "questions.jsonl").read_bytes()
    # Only the wording and the file path are kept; answers are dropped here.
    rows = [{"path": r["path"], "question": r["question"]} for r in map(json.loads, raw.decode("utf-8").splitlines()) if r]
    pairs = twin_pairs(rows)
    translated, english, failed, conflicts = build(pairs)
    table = ordered(translated)
    exact = sum(rewrite(table, other) == en for en, other, _ in pairs)

    # Generalisation: rebuild without one drawing group in five, rewrite those groups.
    held = {g for g in {drawing_group(p) for _, _, p in pairs}
            if int(hashlib.sha256(g.encode()).hexdigest(), 16) % 5 == 0}
    train = ordered(build([p for p in pairs if drawing_group(p[2]) not in held])[0])
    totals, hits = collections.Counter(), collections.Counter()
    for en, other, path in pairs:
        if drawing_group(path) in held:
            source = path.split("/")[1]
            totals[source] += 1
            hits[source] += rewrite(train, other) == en

    output = {"generated_by": "ops/build_question_templates.py",
              "source": "question wording in questions.jsonl; answers are never read",
              "questions_sha256": hashlib.sha256(raw).hexdigest(),
              "translated": table,
              "english": [{"pattern": p, "english": f} for p, f in sorted(english.items())]}
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "pairs": len(pairs), "templates": len(table),
                      "english_templates": len(english), "failed_pairs": len(failed), "conflicts": conflicts,
                      "exact_rewrites": exact,
                      "held_out_exact": {s: f"{hits[s]}/{totals[s]}" for s in sorted(totals)}}, ensure_ascii=False))
    return 1 if failed or conflicts or exact != len(pairs) else 0


if __name__ == "__main__":
    sys.exit(main())

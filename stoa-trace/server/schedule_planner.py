"""Model-planned, deterministically executed queries over a sheet's schedule tables.

Real drawing sets phrase schedule questions in open ways ("Marvin Essential sliding patio
doors on the 3rd floor", "types whose description starts with SWING", "if every N-wide
window assembly has N units"). Fixed wording rules cannot cover that, so a language model
reads the question and the extracted tables and returns a small structured query plan:
which table, which row filters, which aggregate over which columns.

The model never produces the number. Python executes the plan over the extracted cells,
does the arithmetic, and cites every row it used. Invalid plans (unknown columns,
non-numeric sums, a value question matching other than one row) are refused, and the plan
is cached so a repeated question costs nothing.
"""
from __future__ import annotations

import hashlib
import json
import re

PLAN_REVISION = "schedule-plan-v1"

SYSTEM = """You plan queries over construction schedule tables (door, window, finish, room, type schedules).
You get the tables extracted from one drawing sheet and a question. Do NOT compute the answer.
Return a plan that a program executes exactly over the table cells:
- table: index of the one table that answers the question.
- filters: row conditions, all must hold (AND). Each has a column index, an op and values (OR within values).
  ops: "equals" (whole cell, case-insensitive), "has_token" (cell split on spaces , / & contains a value exactly,
  e.g. a code inside "W1 & W2"), "contains" (substring), "starts_with" (prefix).
  Use the exact spelling that appears in the cells. Write feet-inch values as they appear (e.g. 3' - 0").
- aggregate: "count_rows" (number of matching rows), "sum_column" (sum of numbers in value_columns[0]),
  "sum_column_times_leading_number" (sum over rows of value_columns[0] x the first integer in multiplier_column),
  "value" (read value_columns of the single matching row; for what/which questions).
- If the table has a quantity column (Count, Qty) and the question asks how many items are scheduled, sum that column.
  If each row is one item (one row per door number or room), count rows.
- answerable=false if the tables cannot answer the question (e.g. it asks about symbols drawn on a plan,
  not listed in a schedule), or if required information is missing.
Keep explanation to one sentence describing the filters in plain words."""

SCHEMA = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean"},
        "table": {"type": "integer"},
        "filters": {"type": "array", "items": {"type": "object", "properties": {
            "column": {"type": "integer"},
            "op": {"type": "string", "enum": ["equals", "has_token", "contains", "starts_with"]},
            "values": {"type": "array", "items": {"type": "string"}}},
            "required": ["column", "op", "values"], "additionalProperties": False}},
        "aggregate": {"type": "string", "enum": ["count_rows", "sum_column", "sum_column_times_leading_number", "value"]},
        "value_columns": {"type": "array", "items": {"type": "integer"}},
        "multiplier_column": {"type": ["integer", "null"]},
        "explanation": {"type": "string"},
    },
    "required": ["answerable", "table", "filters", "aggregate", "value_columns", "multiplier_column", "explanation"],
    "additionalProperties": False,
}


def _norm(text):
    t = str(text or "").replace("’", "'").replace("''", '"').upper()
    t = re.sub(r"'\s*-\s*", "'-", t)
    return re.sub(r"\s+", " ", t).strip()


def _tokens(text):
    return {t.strip("()[]:;.") for t in re.split(r"[\s,/&]+", _norm(text)) if t.strip("()[]:;.")}


def _number(text):
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(text or ""))
    return float(m.group(0).replace(",", "")) if m else None


def usable_tables(document):
    return [t for t in document.get("metadata", {}).get("schedule_tables", [])
            if t.get("header") and t.get("rows") and re.search(r"schedule", t.get("title", ""), re.I)]


def _prompt(question, tables):
    parts = [f"QUESTION: {question}", ""]
    for i, t in enumerate(tables):
        parts.append(f"TABLE {i}: {t['title']} (page {t.get('page')})")
        parts.append("columns: " + " | ".join(f"{j}={h or '?'}" for j, h in enumerate(t["header"])))
        for k, r in enumerate(t["rows"]):
            parts.append(f"r{k}: " + " | ".join(c.replace("|", "/") for c in r["cells"]))
        parts.append("")
    return "\n".join(parts)


def execute(plan, tables):
    """Run a plan over the tables. Returns dict(value, unit, rows, table, basis) or None."""
    if not plan.get("answerable"):
        return None
    ti = plan.get("table")
    if not isinstance(ti, int) or not 0 <= ti < len(tables):
        return None
    table = tables[ti]
    width = len(table["header"])
    rows = table["rows"]
    for f in plan.get("filters", []):
        if not isinstance(f.get("column"), int) or not 0 <= f["column"] < width or not f.get("values"):
            return None
    selected = []
    for r in rows:
        ok = True
        for f in plan["filters"]:
            cell = r["cells"][f["column"]] if f["column"] < len(r["cells"]) else ""
            values = [_norm(v) for v in f["values"]]
            c = _norm(cell)
            if f["op"] == "equals":
                hit = c in values
            elif f["op"] == "has_token":
                hit = bool(_tokens(cell) & set(values))
            elif f["op"] == "contains":
                hit = any(v in c for v in values)
            else:
                hit = any(c.startswith(v) for v in values)
            if not hit:
                ok = False
                break
        if ok and any(x.strip() for x in r["cells"]):
            selected.append(r)
    agg = plan.get("aggregate")
    cols = [c for c in plan.get("value_columns", []) if isinstance(c, int) and 0 <= c < width]
    if agg == "count_rows":
        return {"value": len(selected), "unit": "count", "rows": selected, "table": table,
                "basis": f"{len(selected)} matching rows"}
    if agg in ("sum_column", "sum_column_times_leading_number"):
        if len(cols) != 1:
            return None
        j = cols[0]
        terms = []
        for r in selected:
            v = _number(r["cells"][j] if j < len(r["cells"]) else "")
            if v is None:
                return None
            if agg == "sum_column_times_leading_number":
                m = plan.get("multiplier_column")
                if not isinstance(m, int) or not 0 <= m < width:
                    return None
                factor = _number(r["cells"][m] if m < len(r["cells"]) else "")
                if factor is None:
                    return None
                v *= factor
            terms.append(v)
        total = sum(terms)
        unit = "count" if re.search(r"count|qty|quant", table["header"][j], re.I) else ("ft²" if re.search(r"\bSF\b", " ".join(r["cells"][j] for r in selected)) else "")
        return {"value": int(total) if total == int(total) else round(total, 4), "unit": unit or "count",
                "rows": selected, "table": table, "terms": terms,
                "basis": f"sum of column '{table['header'][j]}' over {len(selected)} matching rows"
                         + (" x the leading number in column '" + table["header"][plan['multiplier_column']] + "'" if agg != "sum_column" else "")}
    if agg == "value":
        if len(selected) != 1 or not cols:
            return None
        r = selected[0]
        text = "; ".join(f"{table['header'][j] or 'value'}: {r['cells'][j]}" for j in cols if j < len(r["cells"]))
        return {"value": text, "unit": None, "rows": selected, "table": table, "basis": "read from the matching row"}
    return None


def answer(question, document, request=None, cache=None):
    """Plan with the model (via `request`, the app's llm._request) and execute. Returns a native-style
    result dict or None. `cache` is an optional (get, put) pair keyed by a stable digest."""
    tables = usable_tables(document)
    if not tables or request is None:
        return None
    prompt = _prompt(question, tables)
    key = hashlib.sha256((PLAN_REVISION + "\n" + prompt).encode()).hexdigest()
    plan = cache[0](key) if cache else None
    if plan is None:
        plan = request([{"type": "input_text", "text": prompt}], system=SYSTEM, schema=SCHEMA, max_tokens=8000)
        plan.pop("_usage", None)
        if cache:
            cache[1](key, plan)
    found = execute(plan, tables)
    if found is None:
        return None
    source = document.get("metadata", {}).get("source_path")
    table = found["table"]
    objects = [{"id": r["id"], "label": " | ".join(c for c in r["cells"][:3] if c), "type": "schedule_row",
                "page": table.get("page"), "bbox": r.get("bbox"), "source_path": source,
                "properties": {"cells": dict(zip(table["header"], r["cells"])), "schedule": table["title"]}}
               for r in found["rows"]]
    value = found["value"]
    numeric = isinstance(value, (int, float))
    return {"answer": (f"{value:g} {found['unit']}".strip() if numeric else str(value)) + f" ({found['basis']} in {table['title']})",
            "value": value, "unit": found["unit"], "method": "model_planned_schedule_query",
            "status": "supported", "evidence": objects, "scope": f"Schedule: {table['title']}",
            "warnings": ["A language model chose the table, filters and aggregate; the program read the cells and did the arithmetic. Check the highlighted rows."],
            "evidence_complete": True, "spatial_evidence_complete": all(o.get("bbox") for o in objects),
            "calculation": {"plan": plan, "basis": found["basis"], **({"terms": found["terms"]} if "terms" in found else {})}}

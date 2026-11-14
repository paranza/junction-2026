import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Re-score ifc_res.json (own v_ifc_check.py output) per family and per rule, official tolerance.
import json, os, re, collections
DS = _DATA + ""
OUT = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
res = json.load(open(os.path.join(OUT, "ifc_res.json")))
def ok(p, a, t):
    if p is None: return False
    p = float(p)
    return p == a if t == "count" else abs(p - a) <= 0.02 * abs(a)
T = collections.Counter(); rule = collections.Counter(); fails = []
for rec in res:
    r = rows[rec["i"]]; fam = re.sub(r"'[^']*'", "<Q>", r["question"])[:70]; where = rec["asked_on"]
    if rec.get("status"): T[(fam, rec["status"])] += 1; continue
    if r["type"] == "count": g = ok(rec.get("count"), r["answer"], "count"); rule[("count", g)] += 1
    else:
        gq = ok(rec.get("qto"), r["answer"], r["type"]); gg = ok(rec.get("geom"), r["answer"], r["type"])
        g = gq or gg; rule[(r["type"], "qto" if gq else "", "geom" if gg else "")] += 1
    T[(fam, where, "ok" if g else "FAIL")] += 1
    if not g: fails.append((r["question"][:90], r["answer"], rec.get("count"), rec.get("qto"), rec.get("geom")))
for k, v in sorted(T.items()): print(v, k)
print("rules", dict(rule))
print("ok", sum(v for k, v in T.items() if k[-1] == "ok"), "testable", sum(v for k, v in T.items() if k[-1] in ("ok", "FAIL")), "untestable", sum(v for k, v in T.items() if k[-1] not in ("ok", "FAIL")))
print("PDF-asked ok", sum(v for k, v in T.items() if k[-1] == "ok" and k[1] == ".pdf"), "PDF-asked testable", sum(v for k, v in T.items() if k[-1] in ("ok", "FAIL") and k[1] == ".pdf"))
for f in fails: print("FAIL", f)

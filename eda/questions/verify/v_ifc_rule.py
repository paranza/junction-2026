import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Is "Qto NetFloorArea if present, else geometry footprint" a single deterministic rule that matches every area answer?
import json, os, collections
DS = _DATA + ""
OUT = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
res = json.load(open(os.path.join(OUT, "ifc_res.json")))
T = collections.Counter(); bad = []; geom_only_err = []
for rec in res:
    r = rows[rec["i"]]
    if rec.get("status") or r["type"] != "area" or "geom" not in rec: continue
    a = r["answer"]; q = rec.get("qto"); g = rec.get("geom")
    pred = float(q) if q is not None else float(g)
    good = abs(pred - a) <= 0.02 * a
    model = rec["src"][:14]
    T[(model, "qto" if q is not None else "geom", good)] += 1
    if not good: bad.append((model, r["question"][:70], a, q, g))
    geom_only_err.append(abs(float(g) - a) / a)
for k, v in sorted(T.items()): print(v, k)
print("rule failures", len(bad))
for b in bad[:10]: print("  ", b)
geom_only_err.sort(); n = len(geom_only_err)
print("geometry-only rule: within 2%", sum(e <= 0.02 for e in geom_only_err), "/", n, " median rel err", round(geom_only_err[n // 2], 5), " p95", round(geom_only_err[int(0.95 * n)], 4), " max", round(geom_only_err[-1], 4))

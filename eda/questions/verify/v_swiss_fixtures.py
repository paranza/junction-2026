import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Shape-signature fixture counts from swiss DXF FIXTURE layer vs answers (signatures learned from ONE file, site1000; tested on all 65).
import json, os, collections, ezdxf
DS = _DATA + ""
OUT = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
def sig(e):
    pts = [p[:2] for p in e.get_points()]; xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    w, h = sorted((max(xs) - min(xs), max(ys) - min(ys))); return len(pts), w, h
T = collections.Counter(); res = collections.defaultdict(list)
for f in sorted(set(r["path"] for r in rows if r["path"].startswith("data/swiss_dwellings/"))):
    m = ezdxf.readfile(os.path.join(DS, f[:-4] + ".dxf")).modelspace()
    S = [sig(e) for e in m if e.dxf.layer == "FIXTURE" and e.dxftype() == "LWPOLYLINE"]
    pred = {"toilets": sum(1 for n, w, h in S if n == 48 and h > w * 1.3),
            "washbasins": sum(1 for n, w, h in S if n == 48 and h <= w * 1.3),
            "bathtubs": sum(1 for n, w, h in S if n == 69)}
    for i, r in enumerate(rows):
        if r["path"] != f or langs[i] != "en": continue
        for k in pred:
            if f"How many {k}" in r["question"]:
                T[(k, "n")] += 1; T[(k, "ok")] += pred[k] == r["answer"]; res[k].append(pred[k] - r["answer"])
for k, v in sorted(T.items()): print(v, k)
for k, v in res.items(): print(k, "pred-truth", sorted(collections.Counter(v).items()))

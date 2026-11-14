import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Split 48-vertex fixtures into toilets vs washbasins by rotated-rectangle aspect; threshold fitted on even-index files, tested on odd-index files.
import json, os, collections, ezdxf
from shapely.geometry import Polygon
DS = _DATA + ""
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
files = sorted(set(r["path"] for r in rows if r["path"].startswith("data/swiss_dwellings/")))
data = []
for f in files:
    m = ezdxf.readfile(os.path.join(DS, f[:-4] + ".dxf")).modelspace(); asp = []
    for e in m:
        if e.dxf.layer == "FIXTURE" and e.dxftype() == "LWPOLYLINE" and len(e) == 48:
            r = Polygon([p[:2] for p in e.get_points()]).minimum_rotated_rectangle
            xs = list(r.exterior.coords); a = Polygon(xs).length
            d1 = ((xs[0][0] - xs[1][0]) ** 2 + (xs[0][1] - xs[1][1]) ** 2) ** .5; d2 = ((xs[1][0] - xs[2][0]) ** 2 + (xs[1][1] - xs[2][1]) ** 2) ** .5
            asp.append(max(d1, d2) / max(min(d1, d2), 1e-9))
    a = {k: r["answer"] for r in rows if r["path"] == f for k in ("toilets", "washbasins") if r["question"].startswith(f"How many {k}")}
    data.append((asp, a["toilets"], a["washbasins"]))
def score(th, part):
    return sum((sum(x > th for x in asp) == t) + (sum(x <= th for x in asp) == w) for asp, t, w in part)
train, test = data[0::2], data[1::2]
best = max((score(th / 100, train), th / 100) for th in range(100, 250))
print("fitted threshold", best[1], "train", best[0], "/", 2 * len(train), " test", score(best[1], test), "/", 2 * len(test))

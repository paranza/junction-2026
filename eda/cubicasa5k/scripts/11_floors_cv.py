"""Classical-CV baseline for the floors template: count large blobs of dilated dark strokes.
Evaluates exact-match k/n against ground truth for all 241 images and a few parameter settings."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, itertools
import numpy as np, pandas as pd, cv2
cv2.setNumThreads(0)  # OpenCV thread pool deadlocks in this sandbox
from PIL import Image
DS = _DATA + "/data/cubicasa5k"
OUT = _ROOT + "/eda/cubicasa5k"
W = pd.read_csv(os.path.join(OUT, "answers_wide.csv"), index_col=0)
cache = {}
def mask(f, thr):
    if (f, thr) not in cache:
        g = np.asarray(Image.open(os.path.join(DS, f)).convert("L"))
        s = 1000 / max(g.shape)  # normalise long side to 1000 px
        g = cv2.resize(g, (round(g.shape[1] * s), round(g.shape[0] * s)), interpolation=cv2.INTER_AREA)
        cache[(f, thr)] = (g < thr).astype(np.uint8)
    return cache[(f, thr)]
def count(f, thr, dil, rel):
    m = mask(f, thr)
    m = cv2.dilate(m, np.ones((dil, dil), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1: return 0
    box = st[1:, 2] * st[1:, 3]  # bounding-box area per blob
    return int((box >= rel * box.max()).sum())
res = []
for thr, dil, rel in itertools.product([100, 160], [9, 15, 25], [0.15, 0.3]):
    pred = np.array([count(f, thr, dil, rel) for f in W.index])
    acc = (pred == W.floors.values).mean()
    res.append((thr, dil, rel, round(acc, 3), int((pred == W.floors.values).sum())))
R = pd.DataFrame(res, columns=["thr", "dilate", "rel_area", "acc", "k"]).sort_values("acc", ascending=False)
print(R.to_string(index=False)); print("n =", len(W), "| mode baseline (always 1):", round((W.floors == 1).mean(), 3))
best = R.iloc[0]
pred = np.array([count(f, int(best.thr), int(best.dilate), best.rel_area) for f in W.index])
print(pd.crosstab(W.floors.values, pred, rownames=["gt"], colnames=["pred"]))

"""Own floors estimator: dark-pixel mask, close with kernel k% of long side, count components whose bbox area
>= r * largest bbox area. Honest estimate via 2-fold CV (seed 99) over a small grid, vs always-1."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, random, itertools
import numpy as np, pandas as pd, cv2
DS = _DATA + "/data/cubicasa5k"
OUT = _ROOT + "/eda/cubicasa5k/verify"
W = pd.read_csv(os.path.join(OUT, "wide.csv"), index_col=0)
imgs = {}
for f in W.index:
    g = cv2.imread(os.path.join(DS, f), cv2.IMREAD_GRAYSCALE)
    s = 1000 / max(g.shape)
    imgs[f] = cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
KS, RS, TS = [10, 20, 30, 45], [0.15, 0.25, 0.35, 0.5], [100, 160]
def predict(g, k, r, t):
    m = (g < t).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    a = st[1:, 2] * st[1:, 3]
    return max(1, int((a >= r * a.max()).sum())) if len(a) else 1
P = {(k, r, t): {f: predict(g, k, r, t) for f, g in imgs.items()} for k, r, t in itertools.product(KS, RS, TS)}
files = sorted(W.index); random.Random(99).shuffle(files)
folds = [files[::2], files[1::2]]
gt = W.floors.astype(int)
tot = 0
for i in range(2):
    tr, te = folds[i], folds[1 - i]
    best = max(P, key=lambda p: sum(P[p][f] == gt[f] for f in tr))
    acc = sum(P[best][f] == gt[f] for f in te); tot += acc
    print("fold", i, "best", best, "train", sum(P[best][f] == gt[f] for f in tr), "/", len(tr), "test", acc, "/", len(te))
print("CV total", tot, "/ 241; always-1", (gt == 1).sum(), "/ 241")
bestall = max(P, key=lambda p: sum(P[p][f] == gt[f] for f in files))
pr = pd.Series(P[bestall])
print("in-sample best", bestall, (pr[gt.index] == gt).sum(), "/241; 2-floor recall", ((pr[gt.index] == 2) & (gt == 2)).sum(), "/", (gt == 2).sum())

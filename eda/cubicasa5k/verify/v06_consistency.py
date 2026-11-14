"""GT consistency, correlations, near-duplicate images (dHash), and room-template block selection."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, itertools
import numpy as np, pandas as pd
from PIL import Image
DS = _DATA + "/data/cubicasa5k"
OUT = _ROOT + "/eda/cubicasa5k/verify"
W = pd.read_csv(os.path.join(OUT, "wide_props.csv"), index_col=0)
b = W.wc_rooms.notna() & W.bathrooms.notna() & W.toilets.notna()
print("both wc&bath&toilets asked", b.sum(), "toilets > wc+bath", (W.toilets[b] > W.wc_rooms[b] + W.bathrooms[b]).sum(),
      "toilets < wc", (W.toilets[b] < W.wc_rooms[b]).sum())
d = W.doors.notna() & W.bedrooms.notna()
print("doors < bedrooms+1", (W.doors[d] < W.bedrooms[d] + 1).sum(), "of", d.sum())
print("wc_rooms > toilets", (W.wc_rooms > W.toilets).sum(), " toilets==0 & (wc>=1 or bath>=1)", ((W.toilets == 0) & ((W.wc_rooms >= 1) | (W.bathrooms >= 1))).sum())
print("sinks < toilets", (W.sinks < W.toilets).sum(), " shower_bath==0 & bathrooms>=1", ((W.shower_bath == 0) & (W.bathrooms >= 1)).sum())
print("saunas>=1 but shower_bath==0", ((W.saunas >= 1) & (W.shower_bath == 0)).sum())
W["mp"] = W.w * W.h / 1e6
print("corr windows~doors", round(W[["windows", "doors"]].dropna().corr().iloc[0, 1], 3), "windows~mp", round(W[["windows", "mp"]].corr().iloc[0, 1], 3),
      "spearman windows~mp", round(W[["windows", "mp"]].corr(method="spearman").iloc[0, 1], 3))
# windows by floors
print("median windows by floors", W.groupby("floors").windows.median().to_dict())
# room-block selection
room = ["saunas", "kitchens", "bedrooms"]
blk = W[room].notna().any(axis=1)
print("room block asked", blk.sum(), "not asked", (~blk).sum())
for c in ["windows", "toilets", "sinks", "floors", "L"]:
    print(f"  {c}: median asked {W[c][blk].median()} / not {W[c][~blk].median()}  mean {W[c][blk].mean():.2f}/{W[c][~blk].mean():.2f}")
print("  style share not asked:", (W[~blk].style.value_counts() / W.style.value_counts()).round(2).to_dict())
# dHash near duplicates
def dh(f):
    im = Image.open(os.path.join(DS, f)).convert("L").resize((17, 16), Image.LANCZOS)
    a = np.asarray(im, dtype=np.int16); return (a[:, 1:] > a[:, :-1]).flatten()
H = {f: dh(f) for f in W.index}
pairs = sorted((int((H[a] != H[b]).sum()), a, b) for a, b in itertools.combinations(W.index, 2))
print("closest dHash pairs (bits of 256):", pairs[:6])

"""Image properties (size, mode, dpi) and whether template omission depends on anything measurable."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, collections
import numpy as np, pandas as pd
from PIL import Image
DS = _DATA + "/data/cubicasa5k"
OUT = _ROOT + "/eda/cubicasa5k/verify"
W = pd.read_csv(os.path.join(OUT, "wide.csv"), index_col=0)
recs = []
for f in sorted(os.listdir(DS)):
    if not f.endswith(".png"): continue
    im = Image.open(os.path.join(DS, f))
    recs.append(dict(file=f, w=im.width, h=im.height, mode=im.mode, dpi=im.info.get("dpi")))
P = pd.DataFrame(recs).set_index("file")
print("files", len(P), "modes", P["mode"].value_counts().to_dict(), "dpi present", P.dpi.notna().sum())
L = P[["w", "h"]].max(axis=1)
print("long side quantiles", L.quantile([0, .1, .5, .9, 1]).to_dict(), "<600", (L < 600).sum(), "<1000", (L < 1000).sum(), ">=2000", (L >= 2000).sum())
print("files not in questions", set(P.index) - set(W.index), "question files not on disk", set(W.index) - set(P.index))
W = W.join(P)
W["L"] = L
# which templates co-occur as a block
T = ["doors", "saunas", "kitchens", "bedrooms", "wc_rooms", "bathrooms", "balconies", "shower_bath"]
asked = W[T].notna().astype(int)
print("asked-pattern counts (top 12):")
print(asked.astype(str).agg("".join, axis=1).value_counts().head(12).to_string())
print("template order:", T)
# does omission of doors relate to window count, size, style?
for t in ["doors", "bedrooms", "kitchens", "saunas", "bathrooms", "balconies"]:
    a = W[t].notna()
    print(f"{t:10s} asked {a.sum():3d}; mean windows asked/not {W.windows[a].mean():.1f}/{W.windows[~a].mean():.1f}; mean toilets {W.toilets[a].mean():.2f}/{W.toilets[~a].mean():.2f}; median long side {W.L[a].median():.0f}/{W.L[~a].median():.0f}")
# wc_rooms and bathrooms asked together?
print("wc&bath both", (W.wc_rooms.notna() & W.bathrooms.notna()).sum(), "wc only", (W.wc_rooms.notna() & W.bathrooms.isna()).sum(), "bath only", (W.wc_rooms.isna() & W.bathrooms.notna()).sum())
W.to_csv(os.path.join(OUT, "wide_props.csv"))

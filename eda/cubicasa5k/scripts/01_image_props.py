"""Image properties for data/cubicasa5k: size, mode, colourfulness, prefix."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, re, sys
import numpy as np, pandas as pd
from PIL import Image

DS = _DATA + ""
OUT = _ROOT + "/eda/cubicasa5k"
d = os.path.join(DS, "data/cubicasa5k")
rows = []
for f in sorted(os.listdir(d)):
    if not f.endswith(".png"):
        continue
    p = os.path.join(d, f)
    im = Image.open(p)
    info = dict(im.info)
    m = re.match(r"(.+)-(\d+)\.png$", f)
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    # colourfulness: share of pixels whose channel spread > 30
    spread = a.max(axis=2) - a.min(axis=2)
    gray = a.mean(axis=2)
    rows.append(dict(
        file=f, prefix=m.group(1), cid=int(m.group(2)), w=im.width, h=im.height, mode=im.mode,
        bytes=os.path.getsize(p), dpi=str(info.get("dpi")),
        n_unique_colors=len(np.unique(a.reshape(-1, 3) @ np.array([65536, 256, 1]))) if a.size < 4e7 else -1,
        frac_colored=float((spread > 30).mean()),
        frac_white=float((gray > 245).mean()),
        frac_dark=float((gray < 80).mean()),
        mean_gray=float(gray.mean()),
    ))
df = pd.DataFrame(rows)
df["megapixels"] = df.w * df.h / 1e6
df["aspect"] = df.w / df.h
df.to_csv(os.path.join(OUT, "image_props.csv"), index=False)
pd.set_option("display.width", 200)
print(df.groupby("prefix")[["w", "h", "megapixels", "bytes", "frac_colored", "frac_white", "frac_dark", "n_unique_colors"]].describe().T.to_string())
print(df.groupby(["prefix", "mode"]).size())
print(df.dpi.value_counts().head())
print("overall w/h quantiles:\n", df[["w", "h", "megapixels"]].quantile([0, .1, .25, .5, .75, .9, 1]).to_string())

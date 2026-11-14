"""Seed-31 random sample of 12 images (any style, excluding my two blind samples) in a 4x3 grid,
to estimate how often a sheet shows more than one apartment (multi-unit)."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, random
import pandas as pd
from PIL import Image, ImageDraw
DS = _DATA + "/data/cubicasa5k"
OUT = _ROOT + "/eda/cubicasa5k/verify"
W = pd.read_csv(os.path.join(OUT, "wide.csv"), index_col=0)
mine = set(open(os.path.join(OUT, "blind_sample.txt")).read().split()) | set(open(os.path.join(OUT, "code_sample.txt")).read().split())
pick = random.Random(31).sample(sorted(set(W.index) - mine), 12)
cw, ch = 500, 520
sheet = Image.new("RGB", (4 * cw, 3 * ch), "white"); d = ImageDraw.Draw(sheet)
for i, f in enumerate(pick):
    im = Image.open(os.path.join(DS, f)).convert("RGB"); s = min((cw - 10) / im.width, (ch - 30) / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    x, y = (i % 4) * cw, (i // 4) * ch
    sheet.paste(im, (x + 5, y + 25)); d.text((x + 5, y + 5), f"{i}: {f}", fill="red")
sheet.save(os.path.join(OUT, "views", "unit_grid.png"))
for i, f in enumerate(pick): print(i, f)

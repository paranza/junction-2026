"""Seed-5 sample of 8 images with NO room-type questions (saunas, kitchens, bedrooms, wc, bath, balconies all absent)
in a 4x2 grid, to see whether these sheets lack room labels."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, random
import pandas as pd
from PIL import Image, ImageDraw
DS = _DATA + "/data/cubicasa5k"
OUT = _ROOT + "/eda/cubicasa5k/verify"
W = pd.read_csv(os.path.join(OUT, "wide.csv"), index_col=0)
room = ["saunas", "kitchens", "bedrooms", "wc_rooms", "bathrooms", "balconies"]
pool = sorted(W.index[W[room].isna().all(axis=1)])
print("images with no room-type question", len(pool))
pick = random.Random(5).sample(pool, 8)
cw, ch = 500, 640
sheet = Image.new("RGB", (4 * cw, 2 * ch), "white"); d = ImageDraw.Draw(sheet)
for i, f in enumerate(pick):
    im = Image.open(os.path.join(DS, f)).convert("RGB"); s = min((cw - 10) / im.width, (ch - 30) / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    x, y = (i % 4) * cw, (i // 4) * ch
    sheet.paste(im, (x + 5, y + 25)); d.text((x + 5, y + 5), f"{i}: {f}", fill="red")
sheet.save(os.path.join(OUT, "views", "noroom_grid.png"))
for i, f in enumerate(pick): print(i, f, "asked:", [c for c in W.columns if c != "style" and pd.notna(W.loc[f, c])])

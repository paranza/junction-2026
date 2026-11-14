"""Crop a region at full resolution and upscale: crop.py <file.png> x0 y0 x1 y1 [target_long_side=1400] [name]"""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, sys
from PIL import Image, ImageDraw
DS = _DATA + "/data/cubicasa5k"
OUT = _ROOT + "/eda/cubicasa5k/views"
f = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6])
T = int(sys.argv[6]) if len(sys.argv) > 6 else 1400
name = sys.argv[7] if len(sys.argv) > 7 else f"{f[:-4]}_crop_{x0}_{y0}_{x1}_{y1}.png"
im = Image.open(os.path.join(DS, f)).convert("RGB").crop((x0, y0, x1, y1))
s = T / max(im.size)
big = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
d = ImageDraw.Draw(big)
step = 10 if max(im.size) <= 150 else 25 if max(im.size) <= 400 else 50 if max(im.size) <= 900 else 100
for x in range((x0 // step + 1) * step, x1, step):
    X = (x - x0) * s; d.line([(X, 0), (X, 8)], fill="magenta"); d.text((X + 2, 0), str(x), fill="magenta")
for y in range((y0 // step + 1) * step, y1, step):
    Y = (y - y0) * s; d.line([(0, Y), (8, Y)], fill="magenta"); d.text((0, Y + 2), str(y), fill="magenta")
big.save(os.path.join(OUT, name)); print(os.path.join(OUT, name), "scale", round(s, 2))

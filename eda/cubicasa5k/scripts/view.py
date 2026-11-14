"""Render an image (or tiles of it) upscaled for visual inspection.
usage: view.py <file.png> <rows> <cols> [target_long_side=1500] [overlap_frac=0.08]
Writes views/<stem>_full.png and views/<stem>_r<i>c<j>.png with pixel-coordinate ticks."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, sys
from PIL import Image, ImageDraw
DS = _DATA + "/data/cubicasa5k"
OUT = _ROOT + "/eda/cubicasa5k/views"
os.makedirs(OUT, exist_ok=True)
f, R, C = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
T = int(sys.argv[4]) if len(sys.argv) > 4 else 1500
ov = float(sys.argv[5]) if len(sys.argv) > 5 else 0.08
im = Image.open(os.path.join(DS, f)).convert("RGB")
stem = f[:-4]
def save(crop, x0, y0, name):
    s = T / max(crop.size)
    big = crop.resize((max(1, round(crop.width * s)), max(1, round(crop.height * s))), Image.LANCZOS)
    d = ImageDraw.Draw(big)
    step = 50 if max(crop.size) < 800 else 100
    for x in range((x0 // step + 1) * step, x0 + crop.width, step):
        X = (x - x0) * s; d.line([(X, 0), (X, 8)], fill="magenta"); d.text((X + 2, 0), str(x), fill="magenta")
    for y in range((y0 // step + 1) * step, y0 + crop.height, step):
        Y = (y - y0) * s; d.line([(0, Y), (8, Y)], fill="magenta"); d.text((0, Y + 2), str(y), fill="magenta")
    big.save(os.path.join(OUT, name))
    print(os.path.join(OUT, name), crop.size, "scale", round(s, 2))
save(im, 0, 0, f"{stem}_full.png")
if R * C > 1:
    W, H = im.size; tw, th = W / C, H / R
    for i in range(R):
        for j in range(C):
            x0 = int(max(0, j * tw - ov * tw)); y0 = int(max(0, i * th - ov * th))
            x1 = int(min(W, (j + 1) * tw + ov * tw)); y1 = int(min(H, (i + 1) * th + ov * th))
            save(im.crop((x0, y0, x1, y1)), x0, y0, f"{stem}_r{i}c{j}.png")

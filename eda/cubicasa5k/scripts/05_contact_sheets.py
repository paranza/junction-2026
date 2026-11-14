"""Contact sheets per style (fixed seed 0) to compare visual styles."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, random
from PIL import Image, ImageDraw
DS = _DATA + "/data/cubicasa5k"
OUT = _ROOT + "/eda/cubicasa5k/contact"
os.makedirs(OUT, exist_ok=True)
files = sorted(f for f in os.listdir(DS) if f.endswith(".png"))
groups = {}
for f in files:
    groups.setdefault(f.rsplit("-", 1)[0], []).append(f)
rng = random.Random(0)
cell = 400
for pre, fs in groups.items():
    pick = fs if len(fs) <= 16 else rng.sample(fs, 16)
    cols = 4; rows = (len(pick) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 20)), "white")
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(pick):
        im = Image.open(os.path.join(DS, f)).convert("RGB")
        im.thumbnail((cell - 8, cell - 8))
        x, y = (i % cols) * cell, (i // cols) * (cell + 20)
        sheet.paste(im, (x + 4, y + 4))
        d.text((x + 4, y + cell), f"{f} {Image.open(os.path.join(DS, f)).size}", fill="red")
    sheet.save(os.path.join(OUT, f"sheet_{pre}.png"))
    print(pre, len(pick), [p for p in pick])

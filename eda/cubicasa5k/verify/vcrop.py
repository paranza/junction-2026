"""Usage: vcrop.py <file.png> x0 y0 x1 y1 scale [rot]  (native coords) -> verify/views/<stem>_c<x0>_<y0>.png"""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, sys
from PIL import Image
DS = _DATA + "/data/cubicasa5k"
OUT = _ROOT + "/eda/cubicasa5k/verify/views"
f, x0, y0, x1, y1, s = sys.argv[1], *map(int, sys.argv[2:6]), float(sys.argv[6])
rot = int(sys.argv[7]) if len(sys.argv) > 7 else 0
im = Image.open(os.path.join(DS, f)).convert("RGB").crop((x0, y0, x1, y1))
s = min(s, 2000 / max(im.size))
im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS).rotate(rot, expand=True)
p = os.path.join(OUT, f"{f[:-4]}_c{x0}_{y0}_{x1}_{y1}.png"); im.save(p); print(p, im.size)

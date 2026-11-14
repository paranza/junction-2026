"""Legibility at a VLM-like input size: fit the whole page to long side N (default 1568, LANCZOS), then crop the region
that corresponds to native box x,y,w,h, shown at 1x next to the native crop downscaled to the same size (for layout only).
Usage: 11_vlm_res.py <rel path> x y w h [N]. Output: view/<stem>_at<N>.png. Read-only on the dataset."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import sys, pathlib
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
DS = pathlib.Path(_DATA + "")
rel, x, y, w, h = sys.argv[1], *map(int, sys.argv[2:6]); N = int(sys.argv[6]) if len(sys.argv) > 6 else 1568
im = Image.open(DS / rel).convert("L"); s = N / max(im.size)
small = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
c = small.crop((round(x * s), round(y * s), round((x + w) * s), round((y + h) * s)))
nat = im.crop((x, y, x + w, y + h))
out = pathlib.Path(__file__).parent / "view" / f"{pathlib.Path(rel).stem}_at{N}.png"
canvas = Image.new("L", (nat.width, nat.height + c.height + 10), 128)
canvas.paste(nat, (0, 0)); canvas.paste(c, (0, nat.height + 10)); canvas.save(out)
print(out, "native crop", nat.size, "at", N, "->", c.size, "scale", round(s, 3))

"""Viewing helper (writes only to work dir/view).
  fit  <path> [max_side=1600]            downscaled overview
  crop <path> x y w h [scale=1]          native-resolution crop (x,y,w,h in native px), optional integer upscale
  pair <pathA> <pathB> [max_side=1600]   two images side by side, each fitted to half width
Paths may be dataset-relative (data/...) or absolute."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import sys, pathlib
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
DS = pathlib.Path(_DATA + "")
OUT = pathlib.Path(__file__).parent / "view"
OUT.mkdir(exist_ok=True)


CACHE = pathlib.Path(__file__).parent / "cache"  # local copies made by 00_cache.py (avoids iCloud re-downloads)


def load(p):
    p = pathlib.Path(p)
    if not p.is_absolute():
        p = CACHE / p if (CACHE / p).exists() else DS / p
    return Image.open(p).convert("RGB"), p.stem


def fit(im, n):
    s = n / max(im.size)
    return im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS) if s < 1 else im


cmd = sys.argv[1]
if cmd == "fit":
    im, stem = load(sys.argv[2]); n = int(sys.argv[3]) if len(sys.argv) > 3 else 1600
    out = OUT / f"{stem}_fit{n}.jpg"; fit(im, n).save(out, quality=90)
elif cmd == "crop":
    im, stem = load(sys.argv[2]); x, y, w, h = map(int, sys.argv[3:7]); sc = int(sys.argv[7]) if len(sys.argv) > 7 else 1
    c = im.crop((x, y, x + w, y + h))
    if sc > 1:
        c = c.resize((c.width * sc, c.height * sc), Image.NEAREST)
    out = OUT / f"{stem}_crop_{x}_{y}_{w}x{h}_s{sc}.png"; c.save(out)
elif cmd == "pair":
    a, sa = load(sys.argv[2]); b, sb = load(sys.argv[3]); n = int(sys.argv[4]) if len(sys.argv) > 4 else 1600
    a, b = fit(a, n // 2), fit(b, n // 2)
    canvas = Image.new("RGB", (a.width + b.width + 10, max(a.height, b.height)), (255, 0, 255))
    canvas.paste(a, (0, 0)); canvas.paste(b, (a.width + 10, 0))
    out = OUT / f"pair_{sa}__{sb}.jpg"; canvas.save(out, quality=90)
elif cmd == "sheet":  # sheet <name> <cell_px> <cols> <path>...  labelled grid of thumbnails
    from PIL import ImageDraw
    name, cell, cols, paths = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5:]
    rows = -(-len(paths) // cols)
    canvas = Image.new("RGB", (cols * (cell + 8), rows * (cell + 26)), (255, 0, 255))
    for i, p in enumerate(paths):
        im, stem = load(p); w0, h0 = im.size; im = fit(im, cell)
        x, y = (i % cols) * (cell + 8), (i // cols) * (cell + 26)
        canvas.paste(Image.new("RGB", (cell, 22), (255, 255, 255)), (x, y))
        ImageDraw.Draw(canvas).text((x + 3, y + 5), f"{i + 1}. {stem[:38]} ({w0}x{h0})", fill=(0, 0, 0))
        canvas.paste(im, (x, y + 22))
    out = OUT / f"sheet_{name}.jpg"; canvas.save(out, quality=88)
print(out, Image.open(out).size)

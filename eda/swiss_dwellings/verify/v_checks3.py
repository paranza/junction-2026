import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# F15 raster sensitivity (own formula run), F14 PNG vs PDF render on a different random sample (seed 1),
# and a census of iCloud 'dataless' placeholders in the whole preview dataset (stat only, no reads).
import sys, os, collections, random, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_pdf, v_parse, v_local, v_eval
import numpy as np, pymupdf
from PIL import Image

ROOT = _DATA + ""
# --- census
cnt = collections.Counter()
for p in glob.glob(ROOT + "/data/*/**/*", recursive=True):
    if os.path.isfile(p):
        src = p[len(ROOT) + 6:].split("/")[0]
        cnt[(src, os.path.splitext(p)[1].lower(), bool(os.stat(p).st_flags & v_local.SF_DATALESS))] += 1
by_src = collections.defaultdict(lambda: [0, 0])
for (src, ext, dl), n in cnt.items(): by_src[src][dl] += n
print("files local/dataless by source:", {k: tuple(v) for k, v in by_src.items()})
print("swiss by ext:", {k[1:]: v for k, v in cnt.items() if k[0] == "swiss_dwellings"})

# --- F15: 1-px boundary shift error = perimeter * pixel / area for asked rooms
qs = [q for q in v_parse.load() if q["lang"] == "en" and q["fam"] == "area_room"]
stems = sorted({q["stem"] for q in qs})
M = {s: v_pdf.load(s) for s in stems}
res = collections.Counter()
for q in qs:
    m = M[q["stem"]]; r = [r for r in m["rooms"] if r["num"] == q["param"][0]][0]
    g = r["poly"]["g"]
    per_m = g.length * m["mpp"]; area = r["net"]
    for dpi in (150, 300):
        px_m = 0.0254 / dpi * m["scale"]
        bad = per_m * px_m / area > 0.02
        res[(dpi, "all")] += bad; res[(dpi, m["scale"])] += bad
    res[("n", m["scale"])] += 1
print("1-px shift error > 2%:", dict(res))

# --- F14: PNG vs PDF render at PNG size, sample of local PNGs with seed 1
local_png = v_local.stems("png")
random.seed(1); sample = random.sample(local_png, min(8, len(local_png)))
for s in sample:
    im = Image.open(f"{v_pdf.D}/{s}.png")
    a = np.asarray(im.convert("L"), dtype=np.int16)
    pg = pymupdf.open(f"{v_pdf.D}/{s}.pdf")[0]
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(im.width / pg.rect.width, im.height / pg.rect.height), alpha=False, colorspace=pymupdf.csGRAY)
    b = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).astype(np.int16)
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    d = np.abs(a[:h, :w] - b[:h, :w])
    ink_a, ink_b = (a < 128).mean() * 100, (b < 128).mean() * 100
    print(s[:30], im.size, im.mode, im.info.get("dpi"), "diff>64: %.2f%%" % ((d > 64).mean() * 100), "ink png %.2f%% pdf %.2f%%" % (ink_a, ink_b))

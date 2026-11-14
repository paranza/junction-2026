"""Can A-701 fixture counts be derived from vector geometry alone?
Cluster the olive 'fixture' pen strokes of each enlarged plan into connected components and size them in feet.
Usage: python -I fixtures_a701.py <pdf> <out_png_prefix>"""
import sys
import pymupdf

pdf, out = sys.argv[1], sys.argv[2]
doc = pymupdf.open(pdf)
p = doc[0]
m = p.rotation_matrix
s = 3024 / 2000
PT_PER_FT = 36.0  # 1/2" = 1'-0" -> 0.5 in = 36 pt per foot
VIEWS = {"6A": pymupdf.Rect(75 * s, 970 * s, 470 * s, 1310 * s), "6B": pymupdf.Rect(140 * s, 700 * s, 470 * s, 925 * s)}
OLIVE = (0.55, 0.55, 0.4)
dr = p.get_drawings()


def olive(d):
    c = d.get("color")
    return c is not None and all(abs(a - b) < 0.03 for a, b in zip(c, OLIVE))


for name, clip in VIEWS.items():
    rects = []
    for d in dr:
        r = d["rect"] * m
        r.normalize()
        if olive(d) and clip.contains(r):
            rects.append(pymupdf.Rect(r))
    # union-find on padded bbox overlap
    par = list(range(len(rects)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    pad = [pymupdf.Rect(r.x0 - 0.8, r.y0 - 0.8, r.x1 + 0.8, r.y1 + 0.8) for r in rects]
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            if pad[i].intersects(pad[j]):
                par[f(i)] = f(j)
    comps = {}
    for i, r in enumerate(rects):
        k = f(i)
        comps[k] = comps.get(k, pymupdf.Rect(r)) | r
        comps.setdefault(("n", k), 0)
        comps[("n", k)] += 1
    print(f"view {name}: olive strokes={len(rects)} components={sum(1 for k in comps if not isinstance(k, tuple))}")
    big = [(k, v) for k, v in comps.items() if not isinstance(k, tuple)]
    big.sort(key=lambda kv: (kv[1].y0, kv[1].x0))
    for k, r in big:
        n = comps[("n", k)]
        if n >= 3:
            print(f"   {n:4d} strokes  {r.width / PT_PER_FT:5.2f} ft x {r.height / PT_PER_FT:5.2f} ft  at ({r.x0:.0f},{r.y0:.0f})")
    pix = p.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=clip)
    pix.save(f"{out}_{name}.png")

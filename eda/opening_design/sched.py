"""Lattice table extraction from a PDF page text layer + stroked grid lines, in display (rotated) space.
Every cell keeps its bbox so an answer can point back at the exact cell on the sheet."""
import pymupdf


def display_words(page, clip=None):
    """Words as (Rect, text) in display coordinates (pymupdf words are in unrotated space)."""
    m = page.rotation_matrix
    out = []
    for w in page.get_text("words"):
        r = pymupdf.Rect(w[:4]) * m
        r.normalize()
        if clip is None or clip.contains(pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)):
            out.append((r, w[4]))
    return out


def display_segments(page, clip, drawings=None):
    """Axis-parallel stroked line segments inside clip, in display coordinates.
    hs: (x0, x1, y), vs: (y0, y1, x)."""
    m = page.rotation_matrix
    hs, vs = [], []
    for d in drawings if drawings is not None else page.get_drawings():
        for it in d["items"]:
            if it[0] == "l":
                _add(it[1] * m, it[2] * m, clip, hs, vs)
            elif it[0] == "re":
                r = it[1] * m
                r.normalize()
                for a, b in ((r.tl, r.tr), (r.bl, r.br), (r.tl, r.bl), (r.tr, r.br)):
                    _add(a, b, clip, hs, vs)
    return hs, vs


def _add(a, b, clip, hs, vs):
    if not (clip.x0 - 1 <= min(a.x, b.x) and max(a.x, b.x) <= clip.x1 + 1 and
            clip.y0 - 1 <= min(a.y, b.y) and max(a.y, b.y) <= clip.y1 + 1):
        return
    if abs(a.y - b.y) < 0.5 and abs(a.x - b.x) > 2:
        hs.append((min(a.x, b.x), max(a.x, b.x), (a.y + b.y) / 2))
    elif abs(a.x - b.x) < 0.5 and abs(a.y - b.y) > 2:
        vs.append((min(a.y, b.y), max(a.y, b.y), (a.x + b.x) / 2))


def _cluster(vals, tol=1.5):
    vals = sorted(vals)
    out = []
    for v in vals:
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(c) / len(c) for c in out]


def lattice(page, clip, drawings=None, segs=None, words=None):
    """Return (rows, rects): rows = list of list of cell text; rects = matching cell Rects (display space).
    Columns come from vertical rules, rows from horizontal rules; a word goes to the cell holding its center.
    segs/words may be precomputed for the whole page (they are filtered to clip here)."""
    if segs is None:
        hs, vs = display_segments(page, clip, drawings)
    else:
        hs = [h for h in segs[0] if clip.x0 - 1 <= h[0] and h[1] <= clip.x1 + 1 and clip.y0 - 1 <= h[2] <= clip.y1 + 1]
        vs = [v for v in segs[1] if clip.y0 - 1 <= v[0] and v[1] <= clip.y1 + 1 and clip.x0 - 1 <= v[2] <= clip.x1 + 1]
    ys = _cluster([h[2] for h in hs])
    xs = _cluster([v[2] for v in vs])
    if words is None:
        words = display_words(page, clip)
    else:
        words = [(r, t) for r, t in words if clip.contains(pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))]
    rows, rects = [], []
    for y0, y1 in zip(ys, ys[1:]):
        if y1 - y0 < 3:
            continue
        band = [(r, t) for r, t in words if y0 <= (r.y0 + r.y1) / 2 < y1]
        cells, crs = [], []
        for x0, x1 in zip(xs, xs[1:]):
            if x1 - x0 < 3:
                continue
            ws = [(r, t) for r, t in band if x0 <= (r.x0 + r.x1) / 2 < x1]
            ws.sort(key=lambda w: (round(w[0].y0 / 3), w[0].x0))
            cells.append(" ".join(t for _, t in ws))
            crs.append(pymupdf.Rect(x0, y0, x1, y1))
        if any(cells):
            rows.append(cells)
            rects.append(crs)
    return rows, rects

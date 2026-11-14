import shapely, pymupdf
from shapely.geometry import Polygon, MultiLineString

def signed_rings(items):
    """get_drawings() items -> closed rings that keep their drawing direction (needed for the nonzero rule)."""
    rings, cur = [], []
    for it in items:
        if it[0] in ("re", "qu"):
            q = it[1].quad if it[0] == "re" else it[1]
            pts = [q.ul, q.ur, q.lr, q.ll]
            if it[0] == "re" and it[2] == 1: pts = pts[::-1]  # 're' orientation 1 = anticlockwise in PDF space
            rings.append([tuple(p) for p in pts]); continue  # shortcut: 'qu' direction is not reported, assumed ul-ur-lr-ll
        p0, p1 = it[1], it[-1]  # "l": (p1, p2); "c": (p1, c1, c2, p2). shortcut: Bezier curves become chords
        if cur and (abs(cur[-1][0] - p0.x) > 1e-3 or abs(cur[-1][1] - p0.y) > 1e-3):
            rings.append(cur); cur = []
        if not cur: cur = [tuple(p0)]
        cur.append(tuple(p1))
    if cur: rings.append(cur)
    return [r for r in rings if len(r) >= 3]

def winding(pt, ring):
    """Winding number of pt around a closed ring (crossing rule)."""
    x, y, w = pt[0], pt[1], 0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        side = (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0)
        if y0 <= y < y1 and side > 0: w += 1
        elif y1 <= y < y0 and side < 0: w -= 1
    return w

def path_fill(p):
    """Filled area of one get_drawings() path, honouring its own fill rule (p['even_odd'])."""
    rings = signed_rings(p["items"])
    if len(rings) <= 1: return shapely.make_valid(Polygon(rings[0])) if rings else Polygon()
    faces = shapely.polygonize(shapely.node(MultiLineString([r + r[:1] for r in rings])).geoms).geoms
    def filled(face):
        w = sum(winding(face.representative_point().coords[0], r) for r in rings)
        return w % 2 == 1 if p["even_odd"] else w != 0
    return shapely.union_all([f for f in faces if filled(f)])

def fill_polygons(page, rgb, tol=0.01):
    """Union of all filled paths whose fill colour matches rgb (0..1 floats). For COUNTS keep path_fill(p) per path."""
    polys = [path_fill(p) for p in page.get_drawings()
             if p.get("fill") and all(abs(a - b) <= tol for a, b in zip(p["fill"], rgb))]
    return shapely.union_all(polys) if polys else Polygon()

if __name__ == "__main__":
    import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import snips
    content = b"""
0.85 0.92 0.83 rg 100 100 m 300 100 l 300 300 l 100 300 l h 150 150 m 150 200 l 200 200 l 200 150 l h f
0.2 0.4 0.6 rg 350 100 m 450 100 l 450 200 l 350 200 l h 400 150 m 500 150 l 500 250 l 400 250 l h f
0.9 0.1 0.1 rg 100 400 200 200 re 150 450 50 50 re f
0.1 0.9 0.1 rg 350 400 200 200 re 400 450 50 50 re f*
0.3 0.3 0.9 rg 100 650 200 150 re 250 670 -100 100 re 175 700 25 30 re f
0.6 0.6 0.1 rg 350 650 m 550 650 l 550 800 l 350 800 l h 400 680 m 400 780 l 500 780 l 500 680 l h 430 700 m 470 700 l 470 740 l 430 740 l h f
"""
    doc = pymupdf.open(); page = doc.new_page(); page.insert_text((10, 20), "x")
    x = page.get_contents()[0]; doc.update_stream(x, doc.xref_stream(x) + b"\n" + content)
    cases = [((0.85, 0.92, 0.83), 37500, "nonzero, reversed hole"), ((0.2, 0.4, 0.6), 17500, "nonzero, same-dir overlap"),
             ((0.9, 0.1, 0.1), 40000, "nonzero, nested same-dir re"), ((0.1, 0.9, 0.1), 37500, "even-odd, nested re"),
             ((0.3, 0.3, 0.9), 30000 - 10000 + 750, "nonzero, re hole (neg width) + island re"),
             ((0.6, 0.6, 0.1), 30000 - 10000 + 1600, "nonzero, lines: outer, reversed hole, island")]
    for rgb, exp, label in cases:
        print(f"{label:45s} expected {exp:6d}  fixed {fill_polygons(page, rgb).area:8.1f}  original {snips.fill_polygons(page, rgb).area:8.1f}")
    print("items:", [[(it[0], it[2] if it[0] == 're' else '') for it in p["items"]] for p in page.get_drawings()][-2:])

# Verified snippets for vector PDFs (PyMuPDF 2.1 + shapely 2.2). Run: python -I snippets_pdf.py synthetic
import re, sys, functools
import pymupdf, shapely
from shapely.geometry import Polygon

# --- S1: words with bold flag (rawdict gives per-char bboxes; span flags bit 4 = bold) ---
def words_with_bold(page):
    out = []
    for b in page.get_text("rawdict")["blocks"]:
        for l in b.get("lines", []):  # image blocks have no "lines"
            for s in l["spans"]:
                bold = bool(s["flags"] & pymupdf.TEXT_FONT_BOLD) or "bold" in s["font"].lower()
                word, box = "", pymupdf.EMPTY_RECT()
                for ch in s["chars"] + [{"c": " "}]:  # sentinel flushes the last word
                    if ch["c"].isspace():
                        if word:
                            out.append(dict(text=word, bbox=tuple(box), bold=bold, size=s["size"], font=s["font"], dir=l["dir"]))
                        word, box = "", pymupdf.EMPTY_RECT()
                    else:
                        word += ch["c"]; box |= ch["bbox"]
    return out

# --- S2: filled paths of one colour -> shapely polygons with holes ---
def subpaths(items):
    """Split a get_drawings() items list into closed point rings; a gap between items starts a new subpath."""
    rings, cur = [], []
    for it in items:
        if it[0] == "re":
            rings.append([tuple(p) for p in (it[1].tl, it[1].tr, it[1].br, it[1].bl)]); continue
        if it[0] == "qu":
            q = it[1]; rings.append([tuple(p) for p in (q.ul, q.ur, q.lr, q.ll)]); continue
        p0, p1 = it[1], it[-1]  # "l": (p1, p2); "c": (p1, c1, c2, p2). shortcut: Bezier curves become chords, flatten them if rooms have arcs
        if cur and (abs(cur[-1][0] - p0.x) > 1e-3 or abs(cur[-1][1] - p0.y) > 1e-3):
            rings.append(cur); cur = []
        if not cur: cur = [tuple(p0)]
        cur.append(tuple(p1))
    if cur: rings.append(cur)
    return [r for r in rings if len(r) >= 3]

def fill_polygons(page, rgb, tol=0.01):
    """Union of all filled paths whose fill colour matches rgb (0..1 floats). Holes: XOR of subpath rings."""
    polys = []
    for p in page.get_drawings():
        f = p.get("fill")
        if f and all(abs(a - b) <= tol for a, b in zip(f, rgb)):
            rings = [shapely.make_valid(Polygon(r)) for r in subpaths(p["items"])]
            if rings: polys.append(functools.reduce(lambda a, b: a.symmetric_difference(b), rings))
    return shapely.union_all(polys) if polys else Polygon()

# --- S3: "1:100" -> metres per PDF point ---
def m_per_pt(page):
    m = re.search(r"\b1\s*:\s*(\d+)\b", page.get_text())
    if not m: return None
    return int(m.group(1)) * 0.0254 / 72  # 1 pt = 1/72 inch on paper, times scale denominator

if __name__ == "__main__":
    d = sys.argv[1]
    doc = pymupdf.open(f"{d}/plan.pdf"); page = doc[0]
    print("page.rect", page.rect, "rotation", page.rotation)
    ws = words_with_bold(page)
    for w in ws: print(w["text"], [round(v, 1) for v in w["bbox"]], "bold" if w["bold"] else "", w["dir"])
    assert any(w["text"] == "Living" and w["bold"] for w in ws) and any(w["text"] == "Bath" and not w["bold"] for w in ws)
    k = m_per_pt(page); print("m per pt", k)
    green = fill_polygons(page, (0xd9 / 255, 0xea / 255, 0xd3 / 255))
    print("green geom", green.geom_type, "holes", len(green.interiors) if green.geom_type == "Polygon" else "?", "area m2", green.area * k * k)
    assert abs(green.area * k * k - (60 - 1)) < 0.6, green.area * k * k  # 10x6 m minus 1x1 m column, within 1%
    peach = fill_polygons(page, (0xfc / 255, 0xe5 / 255, 0xcd / 255))
    print("peach area m2", peach.area * k * k); assert abs(peach.area * k * k - 12) < 0.12
    # exact-text search: search_for is ASCII case-insensitive, so re-check exact text with words
    hits = page.search_for("living"); print("search_for('living') ->", hits)
    exact = [w for w in ws if w["text"] == "Living"]; print("exact words", len(exact))
    # point-in-room: which label lies inside which polygon
    lab = pymupdf.Rect(exact[0]["bbox"]); print("label inside green room:", green.contains(shapely.Point(lab.x0, lab.y1)))
    # raw drawing dict keys, for reference
    p0 = [p for p in page.get_drawings() if p.get("fill")][0]
    print("path keys", sorted(p0.keys())); print("item kinds", [it[0] for it in p0["items"]], "even_odd", p0["even_odd"], "closePath", p0["closePath"])
    print("ALL PDF CHECKS PASSED")

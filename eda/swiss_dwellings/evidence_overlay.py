"""Demo: evidence overlay for two answers, drawn on an in-memory copy of the PDF (the dataset file is never saved)."""
import os, sys, collections
import pymupdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_solver as S

WD = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1] if len(sys.argv) > 1 else "site1102_bldg2242_floor10281"
apt = sys.argv[2] if len(sys.argv) > 2 else "A"
m = S.load(name)
doc = pymupdf.open(f"{S.DS}/{name}.pdf"); page = doc[0]
shape = page.new_shape()
total = 0.0
for r in m["rooms"]:
    if not (r["unit"] and S.RES_TAG.match(r["unit"]) and r["unit"].split()[-1] == apt): continue
    keep = r["cat"] != "outdoor"
    g = r["poly"]; polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    for pg in polys:
        shape.draw_polyline([pymupdf.Point(x, y) for x, y in pg.exterior.coords])
        shape.finish(color=(0, 0.6, 0) if keep else (0.85, 0, 0), fill=(0, 0.8, 0) if keep else (1, 0.3, 0.3), fill_opacity=0.25, width=1.2)
    if keep: total += r["net"]
    x0, y0, x1, y1 = r["bbox"]
    shape.insert_text(pymupdf.Point(x0, y1 + 22), f"{'+' if keep else 'excl.'} {r['net']:.2f}", fontsize=6, color=(0, 0.4, 0) if keep else (0.8, 0, 0))
shape.commit()
page.insert_text(pymupdf.Point(60, 60), f"Apartment {apt} net area = {total:.2f} m2 (green rooms summed, red = outdoor, excluded)", fontsize=11, color=(0, 0.4, 0))
z = 2000 / max(page.rect.width, page.rect.height)
page.get_pixmap(matrix=pymupdf.Matrix(z, z)).save(f"{WD}/img/evidence_{name}_apt{apt}.png")

# door evidence: draw each door frame; duplicates (same geometry) get a count badge
doc2 = pymupdf.open(f"{S.DS}/{name}.pdf"); p2 = doc2[0]
frames = collections.Counter()
for d in p2.get_drawings():
    if d["type"] == "s" and S.RGB(d.get("color")) == (0.267, 0.267, 0.267) and any(it[0] == "qu" for it in d["items"]):
        r = d["rect"]; frames[(round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1))] += 1
sh = p2.new_shape()
for (x0, y0, x1, y1), c in frames.items():
    sh.draw_rect(pymupdf.Rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2)); sh.finish(color=(0, 0, 1) if c == 1 else (0.9, 0.4, 0), width=1.5)
    if c > 1: sh.insert_text(pymupdf.Point(x1 + 3, y0), f"x{c}", fontsize=8, color=(0.9, 0.4, 0))
sh.commit()
p2.insert_text(pymupdf.Point(60, 60), f"Doors = {sum(frames.values())} door records ({len(frames)} distinct symbols; orange = drawn more than once)", fontsize=11, color=(0, 0, 0.6))
p2.get_pixmap(matrix=pymupdf.Matrix(z, z)).save(f"{WD}/img/evidence_{name}_doors.png")
print("apartment", apt, round(total, 2), "| doors", sum(frames.values()), "distinct", len(frames))

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf, shapely
from shapely.geometry import LinearRing
from snips import schedule_tables, subpaths
FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fx")
# B2) clip rule precisely
doc = pymupdf.open(); page = doc.new_page(); page.insert_text((100, 100), "ABCDEFGH", fontsize=20)
ch = [c for b in page.get_text("rawdict")["blocks"] for l in b["lines"] for s in l["spans"] for c in s["chars"]][3]["bbox"]
mid = (ch[0] + ch[2]) / 2
for dx in (-0.6, -0.2, 0.2, 0.6):
    print(f"B2 clip x1 = D mid {dx:+}: ->", repr(page.get_text("text", clip=(0, 0, mid + dx, 200)).strip()))
midy = (ch[1] + ch[3]) / 2
for dy in (-0.6, 0.6):
    print(f"B2 clip y1 = D vertical mid {dy:+}: ->", repr(page.get_text("text", clip=(0, 0, 400, midy + dy)).strip()))
# 're' orientation vs ring orientation
content = b"0.85 0.92 0.83 rg\n100 100 m 300 100 l 300 300 l 100 300 l h\n150 150 m 150 200 l 200 200 l 200 150 l h\nf\n0.5 0.5 0.5 rg 100 400 200 200 re f\n"
doc = pymupdf.open(); page = doc.new_page(); page.insert_text((10, 20), "x"); x = page.get_contents()[0]; doc.update_stream(x, doc.xref_stream(x) + b"\n" + content)
for p in page.get_drawings():
    print("R items", [(it[0], it[2] if it[0] == "re" else None) for it in p["items"]], "ring ccw (shapely, y-down coords):", [LinearRing(r).is_ccw for r in subpaths(p["items"])])
# E2) realistic rotated sheet: content drawn rotated so the sheet reads horizontally only with /Rotate applied
src = pymupdf.open(); sp = src.new_page(width=842, height=595)
rows = [["MARK", "WIDTH", "TYPE"], ["D1", "3'-0\"", "A"], ["D2", "2'-8\"", "B"]]
for i, rr in enumerate(rows):
    for j, t in enumerate(rr):
        rect = pymupdf.Rect(100 + j * 90, 100 + i * 22, 190 + j * 90, 122 + i * 22)
        sp.draw_rect(rect, color=(0, 0, 0), width=0.7); sp.insert_text(rect.bl + (4, -6), t, fontsize=10)
sp.insert_text((100, 90), "DOOR SCHEDULE", fontsize=12)
for rot in (90, 270):
    d = pymupdf.open(); tp = d.new_page(width=595, height=842)
    tp.show_pdf_page(tp.rect, src, 0, rotate=rot); tp.set_rotation(rot)
    d = pymupdf.open("pdf", d.tobytes()); tp = d[0]
    dirs = {tuple(round(v, 2) for v in l["dir"]) for b in tp.get_text("dict")["blocks"] for l in b.get("lines", [])}
    pm = tp.get_pixmap(dpi=40); pm.save(f"{FX}/sheet_rot{rot}.png")
    print(f"E2 rot={rot} page.rect={tp.rect} dirs before={dirs}")
    t0 = time.time(); res = schedule_tables(tp); dt = time.time() - t0
    dirs2 = {tuple(round(v, 2) for v in l["dir"]) for b in tp.get_text("dict")["blocks"] for l in b.get("lines", [])}
    print(f"E2 rot={rot} after: rotation={tp.rotation} dirs={dirs2} time={dt:.2f}s tables={len(res)}")
    for bb, df, cells in res: print(df.to_string()); print("cells", cells)
    d2 = pymupdf.open("pdf", d.tobytes()); p2 = d2[0]
    t0 = time.time(); tf = p2.find_tables(); print(f"E2 rot={rot} default find_tables without remove_rotation: {time.time()-t0:.2f}s", [t.extract() for t in tf.tables])

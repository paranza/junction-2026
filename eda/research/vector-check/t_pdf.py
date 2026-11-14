import sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf, shapely
from snips import *
FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fx")

def raw_page(content: bytes, w=595, h=842):
    doc = pymupdf.open(); page = doc.new_page(width=w, height=h)
    page.insert_text((10, 20), "Scale 1:100", fontsize=8)  # creates a contents stream we then extend
    xref = page.get_contents()[0]
    doc.update_stream(xref, doc.xref_stream(xref) + b"\n" + content)
    return doc

# A) compound paths
content = b"""
0.85 0.92 0.83 rg
100 100 m 300 100 l 300 300 l 100 300 l h
150 150 m 150 200 l 200 200 l 200 150 l h
f
0.2 0.4 0.6 rg
350 100 m 450 100 l 450 200 l 350 200 l h
400 150 m 500 150 l 500 250 l 400 250 l h
f
0.9 0.1 0.1 rg
100 400 200 200 re 150 450 50 50 re f
0.1 0.9 0.1 rg
350 400 200 200 re 400 450 50 50 re f*
"""
doc = raw_page(content); page = doc[0]
for p in page.get_drawings():
    print("A path:", p["type"], "even_odd=", p.get("even_odd"), "fill=", tuple(round(c, 2) for c in p["fill"]) if p.get("fill") else None,
          "items:", [it[0] for it in p["items"]], "keys:", sorted(p.keys()))
g = fill_polygons(page, (0.85, 0.92, 0.83)); print("A1 nonzero reversed hole: area", g.area, "expected 37500")
b = fill_polygons(page, (0.2, 0.4, 0.6)); print("A2 nonzero same-dir overlap: area", b.area, "expected 17500 (nonzero union)")
r = fill_polygons(page, (0.9, 0.1, 0.1)); print("A3 nonzero two 're' (same dir): area", r.area, "expected 40000 (no hole under nonzero)")
q = fill_polygons(page, (0.1, 0.9, 0.1)); print("A4 even-odd two 're': area", q.area, "expected 37500")
print("A m_per_pt:", m_per_pt(page))

# B) get_text clip containment rule
doc = pymupdf.open(); page = doc.new_page()
page.insert_text((100, 100), "ABCDEFGH", fontsize=20)
chars = [c for b in page.get_text("rawdict")["blocks"] for l in b["lines"] for s in l["spans"] for c in s["chars"]]
d = chars[3]["bbox"]; print("B char D bbox", [round(v, 1) for v in d])
mid = (d[0] + d[2]) / 2
for label, x1 in [("clip ends 1pt before D right edge", d[2] - 1), ("clip ends at D middle", mid), ("clip ends 1pt after D left", d[0] + 1)]:
    print("B", label, "->", repr(page.get_text("text", clip=(0, 0, x1, 200)).strip()))
print("B words clip mid ->", [w[4] for w in page.get_text("words", clip=(0, 0, mid, 200))])

# C) search_for semantics
doc = pymupdf.open(); page = doc.new_page()
page.insert_text((50, 100), "mh MH Mh MHMH ÄÖ äö", fontsize=14)
print("C search MH ->", len(page.search_for("MH")), "hits;", "search ÄÖ ->", len(page.search_for("ÄÖ")), "search äö ->", len(page.search_for("äö")))

# D) words_with_bold: base-14 bold, rotated text, matplotlib Type 3 bold
doc = pymupdf.open(); page = doc.new_page()
page.insert_text((50, 100), "Kitchen MH", fontsize=12, fontname="hebo")
page.insert_text((50, 130), "plain words", fontsize=12, fontname="helv")
page.insert_text((300, 400), "rotated label", fontsize=12, rotate=90)
for w in words_with_bold(page): print("D", w["text"], "bold=", w["bold"], "dir=", tuple(round(v, 2) for v in w["dir"]), "bbox=", tuple(round(v, 1) for v in w["bbox"]))
print("D get_text words for comparison:", [(w[4], tuple(round(v, 1) for v in w[:4])) for w in page.get_text("words")])
import matplotlib; matplotlib.use("pdf"); import matplotlib.pyplot as plt
fig = plt.figure(figsize=(4, 3)); fig.text(0.2, 0.5, "Living room", fontweight="bold"); fig.text(0.2, 0.3, "Bath"); fig.savefig(f"{FX}/mpl.pdf"); plt.close(fig)
mp = pymupdf.open(f"{FX}/mpl.pdf")[0]
for b in mp.get_text("dict")["blocks"]:
    for l in b.get("lines", []):
        for s in l["spans"]: print("D mpl span", repr(s["text"]), "font=", s["font"], "flags=", s["flags"])
print("D mpl words_with_bold", [(w["text"], w["bold"]) for w in words_with_bold(mp)])

# E) schedule_tables on a rotated ruled table
doc = pymupdf.open(); page = doc.new_page(width=842, height=595)
rows = [["MARK", "WIDTH", "TYPE"], ["D1", "3'-0\"", "A"], ["D2", "2'-8\"", "B"]]
for i, rr in enumerate(rows):
    for j, t in enumerate(rr):
        rect = pymupdf.Rect(100 + j * 90, 100 + i * 22, 190 + j * 90, 122 + i * 22)
        page.draw_rect(rect, color=(0, 0, 0), width=0.7); page.insert_text(rect.bl + (4, -6), t, fontsize=10)
page.insert_text((100, 90), "DOOR SCHEDULE", fontsize=12)
page.set_rotation(90); doc.save(f"{FX}/sched_rot.pdf")
page = pymupdf.open(f"{FX}/sched_rot.pdf")[0]
t0 = time.time(); res = schedule_tables(page); print("E schedule_tables", round(time.time() - t0, 2), "s; tables:", len(res))
for bb, df, cells in res: print("E df:\n", df.to_string()); print("E cells:", cells)
page2 = pymupdf.open(f"{FX}/sched_rot.pdf")[0]
t0 = time.time(); tf = page2.find_tables(); print("E default find_tables on ROTATED page (no remove_rotation):", round(time.time() - t0, 2), "s;", len(tf.tables), "tables", [t.extract() for t in tf.tables])
page3 = pymupdf.open(f"{FX}/sched_rot.pdf")[0]; page3.remove_rotation()
t0 = time.time(); tf = page3.find_tables(); print("E default find_tables after remove_rotation:", round(time.time() - t0, 2), "s;", [t.extract() for t in tf.tables])
print("E header external/names:", [(t.header.external, t.header.names) for t in tf.tables])

# F) evidence_png on rotations 0/90/270: are red pixels on the word?
for rot in (0, 90, 270):
    doc = pymupdf.open(); page = doc.new_page(width=600, height=400)
    page.insert_text((400, 300), "Bath", fontsize=14); page.set_rotation(rot)
    doc = pymupdf.open("pdf", doc.tobytes()); page = doc[0]
    boxes = page.search_for("Bath"); n_drw = len(page.get_drawings())
    pix = evidence_png(page, boxes, f"{FX}/ev_{rot}.png", pad=24, dpi=144)
    # expected word position inside the crop, in pixels
    clip = ((pymupdf.Rect(boxes[0]) + (-24, -24, 24, 24)) * page.rotation_matrix) & page.rect
    wr = (pymupdf.Rect(boxes[0]) * page.rotation_matrix); sc = 144 / 72
    exp = pymupdf.Rect((wr.x0 - clip.x0) * sc, (wr.y0 - clip.y0) * sc, (wr.x1 - clip.x0) * sc, (wr.y1 - clip.y0) * sc)
    import numpy as np
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    ys, xs = np.where((a[:, :, 0] > 200) & (a[:, :, 1] < 80) & (a[:, :, 2] < 80))
    red = pymupdf.Rect(xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None
    print(f"F rot={rot} pix={pix.w}x{pix.h} red_bbox={red} expected_word_px={exp.round()} annots_left={len(list(page.annots()))} drawings_same={len(page.get_drawings()) == n_drw}")

"""Evidence overlay demo: highlight the exact schedule cells behind one answer (doors of type A1 on A-801).
Draws on a rendered PNG with PIL; the PDF is only read.
Usage: python -I evidence_demo.py <dataset_dir> <work_dir>"""
import sys, os
import pymupdf
from PIL import Image, ImageDraw

D, W = sys.argv[1], sys.argv[2]
sys.path.insert(0, W)
import tables_auto  # noqa: E402

page = pymupdf.open(os.path.join(D, "data", "opening_design", "Sports_Complex", "Sheets - Current Set",
                                 "A-801 - Door and Finish Schedules & Wall Types.pdf"))[0]
t = [t for t in tables_auto.find_tables(page) if t["title"] == "Door Schedule"][0]
hits = [(rr[0], rr[5]) for r, rr in zip(t["rows"], t["rects"]) if len(r) > 5 and r[5] == "A1"]
assert len(hits) == 14, len(hits)  # ground truth for 'type A1' is 14
clip = t["bbox"] + (-10, -10, 10, 10)
z = 2.0
pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=clip)
img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
dr = ImageDraw.Draw(img)
for a, b in hits:
    for r in (a, b):
        dr.rectangle([(r.x0 - clip.x0) * z, (r.y0 - clip.y0) * z, (r.x1 - clip.x0) * z, (r.y1 - clip.y0) * z],
                     outline=(220, 0, 0), width=3)
img.save(os.path.join(W, "img", "evidence_A801_typeA1.png"))
print("highlighted rows:", len(hits), "| clip (display pt):", tuple(round(v) for v in clip))

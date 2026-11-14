import pymupdf
doc = pymupdf.open(); page = doc.new_page(); page.insert_text((100, 100), "ABCDEFGH", fontsize=20)
ch = [c for b in page.get_text("rawdict")["blocks"] for l in b["lines"] for s in l["spans"] for c in s["chars"]][3]["bbox"]
print("D bbox", ch)
for x1 in (142.3, 142.6, 142.9, 143.3, 144.0, 145.0):
    print("x1", x1, repr(page.get_text("text", clip=(0, 0, x1, 200)).strip()), [w[4] for w in page.get_text("words", clip=(0, 0, x1, 200))])
for y1 in (84.5, 85.5, 86.5, 88):
    print("y1", y1, repr(page.get_text("text", clip=(0, 0, 400, y1)).strip()))
# accurate bboxes flag variant
print("TEXT_ACCURATE_BBOXES" , getattr(pymupdf, "TEXT_ACCURATE_BBOXES", None))

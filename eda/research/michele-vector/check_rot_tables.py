import sys, pymupdf
d = sys.argv[1]
# rotated page: annotation in unrotated coords, clip in rotated coords
doc = pymupdf.open(); pg = doc.new_page(width=595, height=842)
pg.insert_text((100, 100), "MARKER", fontsize=20); pg.set_rotation(90)
r = pg.search_for("MARKER")[0]
print("unrotated page rect", pg.rect * pg.derotation_matrix, "| cropbox", pg.cropbox)
a = pg.add_rect_annot(r); a.set_colors(stroke=(1, 0, 0)); a.set_border(width=2); a.update()
print("annot rect", a.rect, "(input", r, ")")
pix = pg.get_pixmap(clip=(r + (-10, -10, 10, 10)) * pg.rotation_matrix, dpi=72)
reds = sum(1 for y in range(pix.height) for x in range(pix.width) if pix.pixel(x, y)[:3] == (255, 0, 0))
print("rotated clip pix", pix.width, "x", pix.height, "red pixels", reds)
txt = pg.get_text("text", clip=r + (-1, -1, 1, 1)); print("clip text (unrotated coords):", repr(txt))
# table cell text gotcha: hyphen in 3'-0"
page = pymupdf.open(f"{d}/schedule.pdf")[0]
t = page.find_tables()[0]
print("extract():", t.extract()[1])
print("per-cell get_text:", [page.get_text("text", clip=c).strip() for c in t.rows[1].cells])
for tol in (5,):
    print("text_y_tolerance", tol, page.find_tables(text_y_tolerance=tol)[0].extract()[1])
print("use_layout=False", page.find_tables(use_layout=False)[0].extract()[1])
print([k for k in dir(pymupdf) if k.startswith("TEXT_") and ("CHAR" in k or "FILL" in k or "STROK" in k or "BOLD" in k)])
print("TEXT_FONT_BOLD", pymupdf.TEXT_FONT_BOLD)

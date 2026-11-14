# Verified: find_tables -> DataFrame, evidence crop with highlight, rotated-page coordinates.
import sys, pymupdf
d = sys.argv[1]

# --- S4: schedule table -> pandas DataFrame ---
page = pymupdf.open(f"{d}/schedule.pdf")[0]
hit = page.search_for("DOOR SCHEDULE")[0]                  # anchor the table under its title
clip = pymupdf.Rect(page.rect.x0, hit.y0, page.rect.x1, page.rect.y1)
tabs = page.find_tables(clip=clip)                          # default strategy "lines" uses ruled cell borders
print("tables found:", len(tabs.tables))
df = tabs[0].to_pandas()
print(df); print("header external:", tabs[0].header.external, "names:", tabs[0].header.names)
assert list(df.columns) == ["MARK", "WIDTH", "HEIGHT", "TYPE"] and len(df) == 3 and (df["TYPE"] == "A").sum() == 2
# fallback for schedules without ruling lines
tabs_txt = page.find_tables(clip=clip, strategy="text"); print("text strategy tables:", len(tabs_txt.tables))

# --- S5: evidence crop with highlight boxes -> PNG (does not touch page content; annots removed after) ---
def evidence_png(page, boxes, path, pad=24, dpi=200):
    boxes = [pymupdf.Rect(b) for b in boxes]
    clip = functools_reduce_or(boxes) + (-pad, -pad, pad, pad)
    annots = []
    for b in boxes:
        a = page.add_rect_annot(b); a.set_colors(stroke=(1, 0, 0)); a.set_border(width=1.5); a.update(); annots.append(a)
    pix = page.get_pixmap(clip=clip & page.rect, dpi=dpi)   # annots=True by default, so the boxes are drawn
    for a in annots: page.delete_annot(a)
    pix.save(path); return pix.width, pix.height

def functools_reduce_or(rects):
    r = pymupdf.Rect(rects[0])
    for x in rects[1:]: r |= x
    return r

plan = pymupdf.open(f"{d}/plan.pdf"); pp = plan[0]
n_before = len(pp.get_drawings())
wh = evidence_png(pp, pp.search_for("Bath") + pp.search_for("Living"), f"{d}/evidence.png")
print("evidence png size", wh, "drawings unchanged:", len(pp.get_drawings()) == n_before, "annots left:", len(list(pp.annots())))
assert len(pp.get_drawings()) == n_before and not list(pp.annots())

# --- S6: rotated pages: which coordinate space do get_text / search_for / get_drawings / clip use? ---
doc = pymupdf.open(); pg = doc.new_page(width=595, height=842)
pg.insert_text((100, 100), "MARKER", fontsize=20)
pg.draw_rect(pymupdf.Rect(300, 600, 400, 700), color=(0, 0, 0), fill=(1, 0, 0))
pg.set_rotation(90)
print("rotation", pg.rotation, "page.rect", pg.rect, "mediabox", pg.mediabox)
r_search = pg.search_for("MARKER")[0]
r_words = pymupdf.Rect(pg.get_text("words")[0][:4])
r_draw = [p["rect"] for p in pg.get_drawings() if p.get("fill")][0]
print("search_for", r_search, "| words", r_words, "| drawing rect", r_draw)
print("search rect * rotation_matrix ->", r_search * pg.rotation_matrix)
print("drawing rect * rotation_matrix ->", r_draw * pg.rotation_matrix)
pix = pg.get_pixmap(clip=r_draw, dpi=72); print("clip with unrotated drawing rect -> pix", pix.width, "x", pix.height)

# S5 final: evidence crop with red highlight boxes; boxes in extraction (unrotated) coords; works on rotated pages.
import sys, pymupdf
def evidence_png(page, boxes, path, pad=24, dpi=200):
    boxes = [pymupdf.Rect(b) for b in boxes]
    area = pymupdf.Rect(boxes[0])
    for b in boxes[1:]: area |= b
    annots = []
    for b in boxes:  # annotations take unrotated coords, like get_text/search_for/get_drawings return
        a = page.add_rect_annot(b); a.set_colors(stroke=(1, 0, 0)); a.set_border(width=1.5); a.update(); annots.append(a)
    clip = ((area + (-pad, -pad, pad, pad)) * page.rotation_matrix) & page.rect  # get_pixmap clip is in rotated coords
    pix = page.get_pixmap(clip=clip, dpi=dpi)
    for a in annots: page.delete_annot(a)  # leave the page as found
    pix.save(path)
    return pix

if __name__ == "__main__":
    out = sys.argv[1]
    for rot in (0, 90, 270):
        doc = pymupdf.open(); pg = doc.new_page(width=595, height=842)
        pg.insert_text((100, 100), "MARKER", fontsize=20); pg.set_rotation(rot)
        pix = evidence_png(pg, pg.search_for("MARKER"), f"{out}/evidence_rot{rot}.png", dpi=72)
        reds = sum(1 for y in range(pix.height) for x in range(pix.width) if pix.pixel(x, y)[:3] == (255, 0, 0))
        print("rotation", rot, "png", pix.width, "x", pix.height, "red px", reds, "annots left", len(list(pg.annots())))
        assert reds > 100 and not list(pg.annots())
    print("EVIDENCE CHECKS PASSED")

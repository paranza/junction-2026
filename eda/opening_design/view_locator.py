"""Locate a named view on a sheet from its title text (e.g. '6A' + 'RESTROOMS') and crop it for a vision check.
Region: from the view title up to the next view title above that overlaps in x (or the sheet top), and from the
title underline's left/right ends widened by a margin. No hand-given coordinates.
Usage: python -I view_locator.py <pdf> <out_prefix> <view_id> [<view_id> ...]"""
import sys, re, os
import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir; stdlib also has a "sched"
import sched  # noqa: E402

pdf, out, ids = sys.argv[1], sys.argv[2], sys.argv[3:]
page = pymupdf.open(pdf)[0]
words = sched.display_words(page)
hs, _ = sched.display_segments(page, page.rect)
# view ids look like 6A, 12B; a title = upper-case words right of the id bubble, on the line just above its centre
titles = []
for r, t in words:
    if re.fullmatch(r"\d{1,2}[A-Z]", t):
        line = [(r2, t2) for r2, t2 in words if 0 < r.y0 - r2.y0 < 12 and 0 < r2.x0 - r.x1 < 200]
        line.sort(key=lambda w: w[0].x0)
        name = " ".join(t2 for _, t2 in line[:6])
        if line and re.match(r"[A-Z]{3,}", name):
            titles.append((t, name, r))
print("view titles found:", [(t, n[:30]) for t, n, _ in titles])
for vid in ids:
    t, name, r = next(x for x in titles if x[0] == vid)
    # the underline: longest horizontal rule just below/at the title text that starts near the id
    ul = [h for h in hs if abs(h[0] - r.x0) < 40 and 0 <= h[2] - r.y0 < 25 and h[1] - h[0] > 50]
    x0, x1 = (min(h[0] for h in ul), max(h[1] for h in ul)) if ul else (r.x0, r.x0 + 300)
    above = [r2.y1 for t2, _, r2 in titles if r2.y1 < r.y0 - 20 and r2.x0 < x1 and r2.x0 + 300 > x0]
    top = max(above) + 5 if above else page.rect.y0 + 20
    clip = pymupdf.Rect(x0 - 80, top, x1 + 60, r.y1 + 8) & page.rect
    page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), clip=clip).save(f"{out}_{vid}.png")
    print(vid, name[:40], "| underline", (round(x0), round(x1)), "| clip", tuple(round(v) for v in clip))

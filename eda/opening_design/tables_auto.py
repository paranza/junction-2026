"""Find ruled tables on a sheet without hand-given regions: connected components of the stroked
horizontal/vertical rules, header boxes merged with the body box below, then lattice() per region.
A region counts as a table when it has >= min_rows text rows and >= 2 columns with text.
Usage as script: python -I tables_auto.py <pdf> [page_no]  -> prints every table found."""
import sys, os
import numpy as np
import cv2
import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sched  # noqa: E402


def find_tables(page, drawings=None, min_rows=3):
    drawings = drawings if drawings is not None else page.get_drawings()
    R = page.rect
    hs, vs = sched.display_segments(page, R, drawings)
    words = sched.display_words(page)
    mask = np.zeros((int(R.height) + 2, int(R.width) + 2), np.uint8)
    for x0, x1, y in hs:
        cv2.line(mask, (int(x0), int(y)), (int(x1), int(y)), 255, 1)
    for y0, y1, x in vs:
        cv2.line(mask, (int(x), int(y0)), (int(x), int(y1)), 255, 1)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    H = np.array([((a + b) / 2, y) for a, b, y in hs]) if hs else np.zeros((0, 2))
    V = np.array([(x, (a + b) / 2) for a, b, x in vs]) if vs else np.zeros((0, 2))
    WC = np.array([((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2) for r, _ in words]) if words else np.zeros((0, 2))

    def cnt(P, b):
        return int(((P[:, 0] >= b.x0) & (P[:, 0] <= b.x1) & (P[:, 1] >= b.y0) & (P[:, 1] <= b.y1)).sum())

    boxes = []
    for i in range(1, n):
        x, y, w, h, _ = stats[i]
        if w < 40 or h < 15:
            continue
        b = pymupdf.Rect(x, y, x + w, y + h)
        if cnt(H, b) >= 2 and cnt(V, b) >= 2 and cnt(WC, b) >= 2:
            boxes.append(b)
    # merge a header box with the body box right below it (same left/right edges, small gap)
    boxes.sort(key=lambda r: (r.y0, r.x0))
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(len(boxes)):
                a, b = boxes[i], boxes[j]
                if i != j and abs(a.x0 - b.x0) < 4 and abs(a.x1 - b.x1) < 4 and 0 <= b.y0 - a.y1 < 40:
                    boxes[i] = a | b
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    out = []
    for b in boxes:
        clip = pymupdf.Rect(b.x0 - 2, b.y0 - 2, b.x1 + 2, b.y1 + 2)
        rows, rects = sched.lattice(page, clip, segs=(hs, vs), words=words)
        ncols_text = sum(1 for j in range(len(rows[0]) if rows else 0) if sum(1 for r in rows if r[j]) >= 2)
        if len(rows) < min_rows or ncols_text < 2:
            continue
        title = " ".join(c for c in rows[0] if c).strip()
        out.append(dict(title=title, bbox=b, rows=rows, rects=rects))
    return out


if __name__ == "__main__":
    doc = pymupdf.open(sys.argv[1])
    pno = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    for t in find_tables(doc[pno]):
        print(f"== {t['title'][:60]!r} bbox={tuple(round(v) for v in t['bbox'])} rows={len(t['rows'])} cols={len(t['rows'][0])}")
        for r in t["rows"][:60]:
            print("   ", r)

import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Independent scale-bar calibration on habs/al1276_sheet_00001.jpg: vertical edges of the feet and metre bars,
# and the extension lines of the overall 39'-0 5/8" dimension.
import cv2, numpy as np
D = _DATA + '/data'
g = cv2.imread(D + '/habs/al1276_sheet_00001.jpg', 0)
def edges(y0, y1, x0, x1, frac=0.6):
    band = g[y0:y1, x0:x1] < 128
    col = band.sum(0); hit = np.where(col >= frac * (y1 - y0))[0]
    groups = np.split(hit, np.where(np.diff(hit) > 2)[0] + 1)
    return [round(x0 + gr.mean(), 1) for gr in groups if len(gr)]
# find bar rows: rows inside 2190..2265 with long horizontal runs
for y in range(2190, 2266):
    r = (g[y, 1560:2140] < 128).sum()
    if r > 120: print('row', y, r)
fe = edges(2200, 2214, 1600, 2140); me = edges(2243, 2257, 1560, 2140)
print('feet bar vertical edges', fe); print('metre bar vertical edges', me)
de = edges(560, 600, 440, 1160, frac=0.9); print('dimension-zone full-height verticals', de)
# dimension line: the long horizontal row near y~585, then the vertical extension lines crossing it
rows = [(y, int((g[y, 440:1160] < 140).sum())) for y in range(560, 610)]
yd = max(rows, key=lambda t: t[1]); print('dimension row', yd)
y = yd[0]; xs = np.where(g[y, 400:1200] < 140)[0] + 400; print('dim line ink extent', xs.min(), xs.max())
for x0 in (xs.min(), xs.max()):
    seg = g[y - 25:y + 25, x0 - 6:x0 + 7] < 140
    col = seg.sum(0); print('around', x0, 'vertical ink per column', dict(zip(range(x0 - 6, x0 + 7), col.tolist())))
pxft = (2124 - 1787) / 20; pxft_m = (2124 - 1627) / 9 * 0.3048
written = 39 + 0.625 / 12
for name, k in (('feet bar', pxft), ('metre bar', pxft_m)):
    for a, b in ((xs.min(), xs.max()),):
        L = (b - a) / k; print(name, 'px/ft', round(k, 3), 'span px', b - a, 'ft', round(L, 3), 'err %', round(100 * (L - written) / written, 2))

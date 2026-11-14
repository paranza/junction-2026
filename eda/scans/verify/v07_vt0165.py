import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Second sheet (seeded pick, seed 7): habs/vt0165_sheet_00003.jpg, scale bars vs written 182'-1 3/4" and 54'-5".
import cv2, numpy as np
g = cv2.imread(_DATA + '/data/habs/vt0165_sheet_00003.jpg', 0)
def vstrokes(y0, y1, x0, x1, thr=150, frac=0.5):
    col = (g[y0:y1, x0:x1] < thr).sum(0); hit = np.where(col >= frac * (y1 - y0))[0]
    if len(hit) == 0: return []
    gr = np.split(hit, np.where(np.diff(hit) > 1)[0] + 1); return [round(x0 + a.mean(), 1) for a in gr]
for y in range(1830, 1875):
    n = int((g[y, 2440:2630] < 150).sum())
    if n > 40: print('bar row', y, n)
print('feet-bar verticals', vstrokes(1836, 1850, 2440, 2630, frac=0.6))
print('metre-bar verticals', vstrokes(1858, 1872, 2440, 2630, frac=0.6))
# dimension row: longest dark row between y 1600 and 1640
yb = max(range(1600, 1645), key=lambda y: int((g[y, 380:2900] < 150).sum())); print('dim row', yb, int((g[yb, 380:2900] < 150).sum()))
print('dim ticks (verticals crossing dim row)', vstrokes(yb - 18, yb - 2, 370, 2920, frac=0.7))

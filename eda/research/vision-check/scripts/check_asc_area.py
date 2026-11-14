"""Re-run the original synthetic test with smallest-box-first scoring, plus the band-box case."""
import sys
sys.path.insert(0, sys.argv[1])
import numpy as np
from tile_merge_count import nms, tiles, to_pixels

rng = np.random.default_rng(0)
W, H, N = 2400, 1700, 40
cells = rng.choice(np.arange((W // 60) * (H // 60)), N, replace=False)
gt = np.array([[c % (W // 60) * 60 + 10, c // (W // 60) * 60 + 10] for c in cells], float)
gt = np.hstack([gt, gt + 30])
raw = []
for (x0, y0, x1, y1) in tiles(W, H, size=768, overlap=0.25):
    tw, th = x1 - x0, y1 - y0
    for g in gt:
        cx0, cy0, cx1, cy1 = max(g[0], x0), max(g[1], y0), min(g[2], x1), min(g[3], y1)
        if cx1 <= cx0 or cy1 <= cy0 or (cx1 - cx0) * (cy1 - cy0) < 0.3 * 900:
            continue
        box_2d = [round((cy0 - y0) / th * 1000), round((cx0 - x0) / tw * 1000),
                  round((cy1 - y0) / th * 1000), round((cx1 - x0) / tw * 1000)]
        raw.append(to_pixels(box_2d, tw, th, x0, y0))
raw = np.array(raw)
area = (raw[:, 2] - raw[:, 0]) * (raw[:, 3] - raw[:, 1])
print("synthetic: raw", len(raw), "area-desc", len(nms(raw, area, 0.5, "ios")), "area-asc", len(nms(raw, -area, 0.5, "ios")), "truth", N)
assert len(nms(raw, -area, 0.5, "ios")) == N

small = [(100, 100, 130, 110), (135, 100, 165, 110), (170, 100, 200, 110)]
b = np.array(small + small + [(98, 98, 202, 112)], float)
a = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
assert len(nms(b, -a, 0.5, "ios")) == 3 and len(nms(b, a, 0.5, "ios")) == 1
print("band-box case: area-asc 3 (truth 3), area-desc 1")
print("all checks passed")

"""Edge cases for the IOS merge with box area as score."""
import sys
sys.path.insert(0, sys.argv[1])
import numpy as np
from tile_merge_count import nms, tiles

# Case A: three adjacent windows (true count 3) found as 3 boxes in one tile,
# but one other tile (or a full-image pass) returns a single box around the whole band.
small = [(100, 100, 130, 110), (135, 100, 165, 110), (170, 100, 200, 110)]
group = [(98, 98, 202, 112)]
boxes = np.array(small + small + group, float)  # same 3 windows seen in two tiles + one group box
area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
print("A  area-desc IOS:", len(nms(boxes, area, 0.5, "ios")), " area-asc IOS:", len(nms(boxes, -area, 0.5, "ios")), " IoU:", len(nms(boxes, area, 0.5, "iou")), " truth 3")

# Case B: a symbol cut in half at a tile edge (half box inside full box): any order must give 1.
full, half = (300, 300, 330, 330), (300, 300, 315, 330)
b = np.array([full, half], float); a = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
print("B  area-desc IOS:", len(nms(b, a, 0.5, "ios")), " area-asc IOS:", len(nms(b, -a, 0.5, "ios")), " truth 1")

# Case C: two different doors whose boxes include the swing arcs and overlap at a corner (L-shaped hallway)
d1, d2 = (0, 0, 90, 90), (60, 60, 150, 150)
b = np.array([d1, d2], float); a = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
print("C  IOS:", len(nms(b, a, 0.5, "ios")), " truth 2  (inter/min =", 900 / 8100, ")")

# Case D: tiles() on degenerate sizes
print("D ", tiles(500, 300), tiles(768, 768), len(tiles(4500, 3200)))

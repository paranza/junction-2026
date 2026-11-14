"""Find connected components of the purple window fill in high_quality-11377 (colour probe)."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import numpy as np, cv2
from PIL import Image
p = _DATA + "/data/cubicasa5k/high_quality-11377.png"
a = np.asarray(Image.open(p).convert("RGB")).astype(int)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
m = ((b - g) > 25) & ((r - g) > 5) & (b > 150)
n, lab, st, cen = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
for i in range(1, n):
    x, y, w, h, area = st[i]
    if area >= 4:
        print(f"comp x={x} y={y} w={w} h={h} area={area}")

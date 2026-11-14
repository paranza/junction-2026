"""Measure a HABS graphic scale bar: x positions of vertical edges of the square-wave bars (native px).
Usage: 08_scalebar.py <rel path> x0 y0 w h   (band containing one bar). Prints edge x positions."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import sys, pathlib
import numpy as np
from PIL import Image
DS = pathlib.Path(_DATA + "")
rel, x0, y0, w, h = sys.argv[1], *map(int, sys.argv[2:6])
g = np.asarray(Image.open(DS / rel).convert("L"))[y0:y0 + h, x0:x0 + w] < 128
col = g.mean(0)                      # share of band height that is ink, per column
edges = np.nonzero(col > 0.6)[0]     # vertical strokes span most of the band
groups = np.split(edges, np.nonzero(np.diff(edges) > 2)[0] + 1) if len(edges) else []
xs = [round(x0 + grp.mean(), 1) for grp in groups if len(grp)]
print("vertical edges at x =", xs)
print("gaps =", np.round(np.diff(xs), 1).tolist())

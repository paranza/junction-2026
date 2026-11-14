"""Parse a swiss_dwellings PDF (vector + text layer only) into rooms, units, doors, windows, fixtures."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, re, collections
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
DS = _DATA + "/data/swiss_dwellings"
NUM = re.compile(r"[A-Z]?\d*\.\d+")
AREA = re.compile(r"(\d+\.\d+) m²")
TAG = re.compile(r"^(App\.|Whg\.|Appart\.|Gewerbe|Commerce|Commercio|Commercial|Unità|Unité)\s+\S{1,3}$")
RGB = lambda c: tuple(round(v, 3) for v in c) if c else None

def path_points(d):
    pts = []
    for it in d["items"]:
        if it[0] == "l": pts += [it[1], it[2]]
        elif it[0] == "c": pts += [it[1], it[4]]
        elif it[0] == "re": r = it[1]; pts += [r.tl, r.tr, r.br, r.bl]
        elif it[0] == "qu": q = it[1]; pts += [q.ul, q.ur, q.lr, q.ll]
    out = []
    for p in pts:
        if not out or (abs(out[-1][0] - p.x) > 1e-6 or abs(out[-1][1] - p.y) > 1e-6): out.append((p.x, p.y))
    return out

def load(name):
    page = pymupdf.open(f"{DS}/{name}.pdf")[0]
    H = page.rect.height
    spans = [sp for b in page.get_text("dict")["blocks"] for l in b.get("lines", []) for sp in l["spans"]]
    # title block / legend occupy the bottom band; drawing area is above the first horizontal frame line of the title block
    dr = page.get_drawings()
    return page, spans, dr

def scale_m_per_pt(spans):
    for s in spans:
        m = re.fullmatch(r"1:(\d+) \(A\d\)", s["text"])
        if m: return int(m.group(1)) * 0.0254 / 72.0  # 1 pt = 1/72 inch on paper
    return None

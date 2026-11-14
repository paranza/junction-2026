import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, sys, collections, re
from shapely.geometry import Polygon, Point, LineString
DS = _DATA + "/data/swiss_dwellings"
doc = ezdxf.readfile(f"{DS}/{sys.argv[1]}.dxf"); msp = doc.modelspace()
texts = [(e.dxf.text, e.dxf.insert[0], e.dxf.insert[1], e.dxf.height, e.dxf.get("halign"), e.dxf.get("valign"), e.dxf.get("align_point")) for e in msp.query("TEXT[layer=='ROOM_TEXT']")]
print("text align sample", texts[:3])
nums = [(t, x, y) for t, x, y, *_ in texts if re.fullmatch(r"[A-Z]?\d*\.\d+", t)]
for e in msp.query("LWPOLYLINE[layer=='ROOM_OUTLINE']"):
    pts = [tuple(p[:2]) for p in e.get_points()]
    first_eq_last = len(pts) > 2 and abs(pts[0][0]-pts[-1][0]) < 1e-9 and abs(pts[0][1]-pts[-1][1]) < 1e-9
    poly = Polygon(pts) if len(pts) >= 3 else None
    inside = [n for n, x, y in nums if poly is not None and poly.is_valid and poly.contains(Point(x, y))]
    bulge = any(abs(p[4]) > 1e-9 for p in e.get_points())
    print(f"closed={e.closed} n={len(pts)} f=l={first_eq_last} bulge={bulge} area={poly.area if poly else 0:.3f} valid={poly.is_valid if poly else None} lw={e.dxf.get('const_width')} color={e.dxf.get('color')} ltype={e.dxf.get('linetype')} bbox=({min(p[0] for p in pts):.2f},{min(p[1] for p in pts):.2f})-({max(p[0] for p in pts):.2f},{max(p[1] for p in pts):.2f}) nums_inside={inside}")

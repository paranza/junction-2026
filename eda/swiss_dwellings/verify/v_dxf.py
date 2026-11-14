import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Independent DXF floor model for swiss_dwellings (written from scratch for verification).
import ezdxf, re, collections, math
from ezdxf import path as ezpath
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

D = _DATA + "/data/swiss_dwellings"
NUM = re.compile(r"^U?\d+\.\d+$")
AREA = re.compile(r"^(\d+(?:\.\d+)?) m²$")

def verts(e):
    """Flattened vertex list of an LWPOLYLINE (handles bulges), closed flag."""
    p = ezpath.make_path(e)
    pts = [(v.x, v.y) for v in p.flattening(0.001)]
    return pts, bool(e.closed) or (len(pts) > 2 and math.dist(pts[0], pts[-1]) < 1e-9)

def load(stem):
    doc = ezdxf.readfile(f"{D}/{stem}.dxf")
    msp = doc.modelspace()
    by = collections.defaultdict(list)
    for e in msp: by[e.dxf.layer].append(e)
    texts = [dict(t=e.dxf.text, x=e.dxf.insert[0], y=e.dxf.insert[1], h=e.dxf.height, bold="Bold" in (e.dxf.style or ""))
             for e in by["ROOM_TEXT"] if e.dxftype() == "TEXT"]
    ann = [e.dxf.text for e in by["ANNOTATION"] if e.dxftype() == "TEXT"]
    # room outline polygons
    outl = []
    open_room_lines = 0
    bulge_any = False
    for e in by["ROOM_OUTLINE"]:
        if e.dxftype() != "LWPOLYLINE": continue
        if any(b != 0 for b in e.get_points("b")): bulge_any = True
        pts, closed = verts(e)
        if closed and len(pts) >= 3:
            g = Polygon(pts)
            if not g.is_valid: g = g.buffer(0)
            outl.append(g)
        else:
            open_room_lines += 1
    # rooms = bold numbers; label = non-bold text directly above (same x), printed area = text directly below
    rooms = []
    for t in texts:
        if not (t["bold"] and NUM.match(t["t"])): continue
        col = [u for u in texts if u is not t and abs(u["x"] - t["x"]) < 1e-6]
        above = [u for u in col if 0 < u["y"] - t["y"] < 2.0 * t["h"]]
        below = [u for u in col if 0 < t["y"] - u["y"] < 2.0 * t["h"]]
        lab = [u for u in above if not u["bold"]]
        ar = [u for u in below if AREA.match(u["t"])]
        rooms.append(dict(num=t["t"], label=lab[0]["t"] if lab else None,
                          printed=float(AREA.match(ar[0]["t"]).group(1)) if ar else None, x=t["x"], y=t["y"], h=t["h"]))
    for r in rooms:
        pt = Point(r["x"], r["y"])
        cont = [g for g in outl if g.contains(pt)]
        g = min(cont, key=lambda g: g.area) if cont else None
        r["poly"] = g
        r["raw"] = g.area if g is not None else None
        if g is not None:
            inner = [o for o in outl if o is not g and o.area < g.area and g.buffer(1e-6).contains(o)]
            r["n_inner"] = len(inner)
            r["net"] = g.difference(unary_union(inner)).area if inner else g.area
        else:
            r["n_inner"] = 0; r["net"] = None
    # units: outlines + bold tags (bold, not a number)
    units = []
    for e in by["UNIT_OUTLINE"]:
        if e.dxftype() != "LWPOLYLINE": continue
        pts, closed = verts(e)
        g = Polygon(pts)
        if not g.is_valid: g = g.buffer(0)
        units.append(dict(poly=g, tags=[]))
    tags = [t for t in texts if t["bold"] and not NUM.match(t["t"])]
    for t in tags:
        pt = Point(t["x"], t["y"])
        cont = [u for u in units if u["poly"].contains(pt)]
        t["unit"] = min(cont, key=lambda u: u["poly"].area) if cont else None
        if t["unit"] is not None: t["unit"]["tags"].append(t["t"])
    # doors
    dl = by["DOOR"]
    door_frames = [verts(e)[0] for e in dl if e.dxftype() == "LWPOLYLINE" and len(e) == 5]
    door_lines = [e for e in dl if e.dxftype() == "LWPOLYLINE" and len(e) == 2]
    door_arcs = [e for e in dl if e.dxftype() == "ARC"]
    door_other = collections.Counter((e.dxftype(), len(e) if e.dxftype() == "LWPOLYLINE" else None) for e in dl
                                     if not (e.dxftype() == "ARC" or (e.dxftype() == "LWPOLYLINE" and len(e) in (2, 5))))
    # windows
    wl = by["WINDOW"]
    win_rects = [verts(e)[0] for e in wl if e.dxftype() == "LWPOLYLINE" and e.closed]
    win_lines = [verts(e)[0] for e in wl if e.dxftype() == "LWPOLYLINE" and not e.closed]
    win_other = collections.Counter(e.dxftype() for e in wl if e.dxftype() != "LWPOLYLINE")
    # fixtures raw
    fx = []
    for e in by["FIXTURE"]:
        if e.dxftype() == "LWPOLYLINE":
            pts, closed = verts(e)
            fx.append(dict(kind="pl", n=len(e), closed=bool(e.closed), pts=pts))
        elif e.dxftype() == "CIRCLE":
            fx.append(dict(kind="circle", r=e.dxf.radius, c=(e.dxf.center[0], e.dxf.center[1])))
        else:
            fx.append(dict(kind=e.dxftype()))
    return dict(stem=stem, rooms=rooms, outl=outl, units=units, tags=tags, ann=ann, texts=texts,
                door_frames=door_frames, door_lines=door_lines, door_arcs=door_arcs, door_other=door_other,
                win_rects=win_rects, win_lines=win_lines, win_other=win_other, fx=fx,
                open_room_lines=open_room_lines, bulge_any=bulge_any, layers=[l.dxf.name for l in doc.layers],
                insunits=doc.header.get("$INSUNITS"))

def key(pts, nd=3):
    """Order-independent geometry key for duplicate detection."""
    return tuple(sorted((round(x, nd), round(y, nd)) for x, y in pts))

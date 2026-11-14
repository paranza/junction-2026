"""Parse a swiss_dwellings DXF into rooms, units and raw layer entities (reference solver)."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, re, math
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
DS = _DATA + "/data/swiss_dwellings"
NUM = re.compile(r"[A-Z]?\d*\.\d+")
AREA = re.compile(r"(\d+\.\d+) m²")
TAG = re.compile(r"^(App\.|Whg\.|Appart\.|Gewerbe|Commerce|Commercio|Commercial|Unità|Unité)\s+\S{1,3}$")

def load(name):
    doc = ezdxf.readfile(f"{DS}/{name}.dxf"); msp = doc.modelspace()
    texts = [dict(t=e.dxf.text, x=e.dxf.insert[0], y=e.dxf.insert[1], h=e.dxf.height) for e in msp.query("TEXT[layer=='ROOM_TEXT']")]
    outlines = []
    for e in msp.query("LWPOLYLINE[layer=='ROOM_OUTLINE']"):
        pts = [tuple(p[:2]) for p in e.get_points()]
        if e.closed and len(pts) >= 3:
            outlines.append(Polygon(pts).buffer(0))
    opens = [[tuple(p[:2]) for p in e.get_points()] for e in msp.query("LWPOLYLINE[layer=='ROOM_OUTLINE']") if not e.closed]
    units = []
    for e in msp.query("LWPOLYLINE[layer=='UNIT_OUTLINE']"):
        pts = [tuple(p[:2]) for p in e.get_points()]
        units.append(dict(poly=Polygon(pts).buffer(0), closed=e.closed, tag=None))
    # group text stacks: same x (centred), label above number, area below
    used = set(); rooms = []
    for i, t in enumerate(texts):
        if not NUM.fullmatch(t["t"]): continue
        col = [(j, u) for j, u in enumerate(texts) if j != i and abs(u["x"] - t["x"]) < 1e-6 and abs(u["y"] - t["y"]) < 2.2 * t["h"]]
        above = sorted([c for c in col if c[1]["y"] > t["y"]], key=lambda c: c[1]["y"])
        below = [c for c in col if c[1]["y"] < t["y"]]
        label = None; area_txt = None
        if above and not TAG.fullmatch(above[0][1]["t"]): label = above[0][1]["t"]
        for j, u in below:
            m = AREA.fullmatch(u["t"])
            if m: area_txt = float(m.group(1))
        pt = Point(t["x"], t["y"])
        cont = [p for p in outlines if p.contains(pt)]
        poly = min(cont, key=lambda p: p.area) if cont else None
        net = None
        if poly is not None:
            # net area: outline minus outlines nested inside it (columns, shafts, lift, stair void)
            inner = [o for o in outlines if o is not poly and o.area < poly.area and poly.intersection(o).area > 0.5 * o.area]
            net = poly.difference(unary_union(inner)).area if inner else poly.area
        rooms.append(dict(num=t["t"], label=label, printed=area_txt, poly=poly, area=poly.area if poly else None, net=net, x=t["x"], y=t["y"], h=t["h"]))
    # unit tags
    for t in texts:
        m = TAG.fullmatch(t["t"])
        if m:
            pt = Point(t["x"], t["y"])
            cont = [u for u in units if u["poly"].contains(pt)]
            if cont:
                u = min(cont, key=lambda u: u["poly"].area)
                u["tag"] = t["t"]
    for r in rooms:
        r["unit"] = None
        if r["poly"] is not None:
            # most specific (smallest) unit outline that holds most of the room; untagged outlines are common areas
            cands = [u for u in units if u["poly"].intersection(r["poly"]).area > 0.5 * r["poly"].area]
            if cands:
                r["unit"] = min(cands, key=lambda u: u["poly"].area)["tag"]
    return dict(msp=msp, texts=texts, outlines=outlines, opens=opens, units=units, rooms=rooms)

if __name__ == "__main__":
    import sys
    m = load(sys.argv[1])
    for r in m["rooms"]: print(r["num"], r["label"], r["printed"], round(r["area"], 3) if r["area"] else None, r["unit"])
    for u in m["units"]: print("unit", u["tag"], round(u["poly"].area, 2), u["closed"])

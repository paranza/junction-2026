import math, re, xml.etree.ElementTree as ET
import shapely
from shapely.geometry import Polygon, LineString

SVG, IFC = "{http://www.w3.org/2000/svg}", "{http://www.ifcopenshell.org/ns}"

def svg_elements(svg_path, page_rect=None):
    """IfcConvert SVG -> {GlobalId: (ifc_class, name, geometry)}; with page_rect, geometry is in the twin PDF's points."""
    root = ET.parse(svg_path).getroot()
    vx, vy, vw, vh = map(float, re.split(r"[\s,]+", root.get("viewBox").strip()))
    sx, sy = (page_rect.width / vw, page_rect.height / vh) if page_rect is not None else (1.0, 1.0)
    out = {}
    for g in root.iter(SVG + "g"):
        guid = g.get("data-guid") or g.get(IFC + "guid")  # IfcConvert default: data-guid; --svg-xmlns / ifcopenshell.draw: ifc:guid
        if not guid or g.get("class") == "IfcBuildingStorey": continue  # storey groups wrap every element
        geoms = []
        for p in g.iter(SVG + "path"):
            for sub in re.split(r"(?=M)", p.get("d", "")):  # IfcConvert writes "M x,y L x,y ... Z"
                pts = [((float(x) - vx) * sx, (float(y) - vy) * sy) for x, y in re.findall(r"(-?[\d.eE+-]+),(-?[\d.eE+-]+)", sub)]
                closed = sub.rstrip().endswith(("Z", "z")) or (len(pts) >= 4 and math.dist(pts[0], pts[-1]) < 1e-6 * max(vw, vh))
                if closed and len(pts) >= 3: geoms.append(shapely.make_valid(Polygon(pts)))
                elif len(pts) >= 2: geoms.append(LineString(pts))
        out[guid] = (g.get("class"), g.get("data-name") or g.get(IFC + "name"), shapely.union_all(geoms) if geoms else None)
    return out

from collections import Counter
import ezdxf
from ezdxf import units
from ezdxf.addons import geo
from shapely.geometry import shape

def dxf_summary(path):
    doc = ezdxf.readfile(path)                      # damaged files: doc, auditor = ezdxf.recover.readfile(path)
    msp = doc.modelspace()
    k = units.conversion_factor(doc.units, units.M) if doc.units else None   # $INSUNITS 0 = unitless: decide scale yourself
    per_layer = Counter((e.dxftype(), e.dxf.layer) for e in msp)
    rooms = []
    for e in msp.query('LWPOLYLINE[layer=="ROOM_OUTLINE"]'):
        pts = e.get_points("xy")                    # shortcut: bulges ignored; use ezdxf.path.make_path(e).flattening(0.001) if any bulge != 0
        if len(pts) >= 3 and (e.closed or math.dist(pts[0], pts[-1]) < 1e-6):  # many exporters close by repeating the first point
            rooms.append(Polygon(pts))
    hatches = [shapely.make_valid(shape(geo.proxy(h))) for h in msp.query("HATCH")]  # holes kept; geo does no full validity check
    texts = [(e.dxf.text, tuple(e.dxf.insert)[:2]) for e in msp.query("TEXT")] + \
            [(e.plain_text(), tuple(e.dxf.insert)[:2]) for e in msp.query("MTEXT")]

    def count_inserts(layout, c, mult=1):
        for ins in layout.query("INSERT"):          # MINSERT grids: mcount > 1
            n = mult * ins.mcount
            c[ins.dxf.name] += n
            count_inserts(doc.blocks[ins.dxf.name], c, n)   # nested blocks
        return c
    return dict(to_m=k, per_layer=per_layer, room_areas_m2=[p.area * k * k for p in rooms] if k else None,
                hatches=hatches, texts=texts, blocks=count_inserts(msp, Counter()))

if __name__ == "__main__":
    import os; FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fx")
    for f in ("syn.svg", "syn_data.svg"):
        els = svg_elements(os.path.join(FX, f)); print(f, {c: round(g.area, 1) for c, n, g in els.values()} | {"n": len(els)})
    r = dxf_summary(os.path.join(FX, "h.dxf"))
    print("rooms", r["room_areas_m2"], "blocks", dict(r["blocks"]), "hatch", [h.area for h in r["hatches"]])
    assert sorted(r["room_areas_m2"]) == [6.0, 12.0] and r["blocks"]["DOOR"] == 9 and r["hatches"][0].area == 59.0
    print("asserts ok")

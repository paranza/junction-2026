# S8: DXF essentials with ezdxf 1.4 (+ shapely 2): units, layers, polylines, hatches with holes, text, block counts.
import sys
from collections import Counter
import ezdxf, shapely
from ezdxf import units, bbox
from ezdxf.addons import geo
from shapely.geometry import shape, Polygon

doc = ezdxf.readfile(sys.argv[1])                     # untrusted/broken files: ezdxf.recover.readfile(path) -> (doc, auditor)
msp = doc.modelspace()
to_m = units.conversion_factor(doc.units, units.M) if doc.units else None   # $INSUNITS: 0 = unitless, 4 = mm, 6 = m
print("$INSUNITS", doc.header.get("$INSUNITS"), units.unit_name(doc.units), "-> m factor", to_m)
print("layers", [l.dxf.name for l in doc.layers])
print("entity types per layer", Counter((e.dxftype(), e.dxf.layer) for e in msp))

walls = [Polygon(e.get_points("xy")) for e in msp.query('LWPOLYLINE[layer=="A-WALL"]') if e.closed]  # bulges ignored: shortcut
print("closed wall polylines", len(walls), "area m2", sum(p.area for p in walls) * to_m**2)

hatch_geoms = [shape(geo.proxy(h)) for h in msp.query("HATCH")]  # __geo_interface__ keeps holes
print("hatch", hatch_geoms[0].geom_type, "holes", len(hatch_geoms[0].interiors), "area m2", hatch_geoms[0].area * to_m**2)
assert abs(hatch_geoms[0].area * to_m**2 - 59) < 1e-9

texts = [(e.dxf.text, tuple(e.dxf.insert)[:2]) for e in msp.query("TEXT")] + \
        [(e.plain_text(), tuple(e.dxf.insert)[:2]) for e in msp.query("MTEXT")]
print("texts", texts)

def count_inserts(layout, counter=None, mult=1):
    """Count block references, including blocks nested inside blocks."""
    counter = Counter() if counter is None else counter
    for ins in layout.query("INSERT"):
        counter[ins.dxf.name] += mult
        count_inserts(doc.blocks[ins.dxf.name], counter, mult)   # MINSERT grids: multiply by ins.mcount
    return counter
c = count_inserts(msp); print("block counts incl. nested", dict(c)); assert c["DOOR_900"] == 3 and c["DOOR_PAIR"] == 1
print("top-level only", Counter(e.dxf.name for e in msp.query("INSERT")))
print("extents", bbox.extents(msp).extmin, bbox.extents(msp).extmax)
print("ALL DXF CHECKS PASSED")

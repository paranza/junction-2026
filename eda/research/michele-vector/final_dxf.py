from collections import Counter
import ezdxf
from ezdxf import units
from ezdxf.addons import geo
from shapely.geometry import shape, Polygon

def dxf_summary(path):
    doc = ezdxf.readfile(path)                      # damaged files: doc, auditor = ezdxf.recover.readfile(path)
    msp = doc.modelspace()
    k = units.conversion_factor(doc.units, units.M) if doc.units else None   # $INSUNITS 0 = unitless: decide scale yourself
    per_layer = Counter((e.dxftype(), e.dxf.layer) for e in msp)
    rooms = [Polygon(e.get_points("xy")) for e in msp.query('LWPOLYLINE[layer=="ROOM_OUTLINE"]') if e.closed]  # shortcut: bulges ignored; use ezdxf.path.make_path(e).flattening(0.001) if any bulge != 0
    hatches = [shape(geo.proxy(h)) for h in msp.query("HATCH")]          # holes kept via __geo_interface__
    texts = [(e.dxf.text, tuple(e.dxf.insert)[:2]) for e in msp.query("TEXT")] + \
            [(e.plain_text(), tuple(e.dxf.insert)[:2]) for e in msp.query("MTEXT")]

    def count_inserts(layout, c):
        for ins in layout.query("INSERT"):          # MINSERT grids: multiply by ins.mcount
            c[ins.dxf.name] += 1
            count_inserts(doc.blocks[ins.dxf.name], c)   # nested blocks
        return c
    return dict(to_m=k, per_layer=per_layer, room_areas_m2=[p.area * k * k for p in rooms] if k else None,
                hatches=hatches, texts=texts, blocks=count_inserts(msp, Counter()))

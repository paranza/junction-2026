"""DXF probe: version, units, layers, entity types, text content, extents.
Usage: python -I dxf_probe.py <dxf>"""
import sys, collections
import ezdxf
from ezdxf import bbox

doc = ezdxf.readfile(sys.argv[1])
msp = doc.modelspace()
print("dxf version", doc.dxfversion, "| $INSUNITS", doc.header.get("$INSUNITS"), "| layers", [l.dxf.name for l in doc.layers])
print("entity types", dict(collections.Counter(e.dxftype() for e in msp)))
print("texts", [e.dxf.text if e.dxftype() == "TEXT" else e.text for e in msp if e.dxftype() in ("TEXT", "MTEXT")][:30])
ext = bbox.extents(msp)
print("extents", ext.extmin, ext.extmax, "size", ext.size)
print("paperspace layouts", doc.layout_names())

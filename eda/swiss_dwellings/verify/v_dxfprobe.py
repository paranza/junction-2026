import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, glob, os, collections, sys
D = _DATA + "/data/swiss_dwellings"
f = sys.argv[1] if len(sys.argv) > 1 else "site1102_bldg2242_floor10281"
doc = ezdxf.readfile(f"{D}/{f}.dxf")
msp = doc.modelspace()
print("dxfversion", doc.dxfversion, "units $INSUNITS", doc.header.get("$INSUNITS"), "$MEASUREMENT", doc.header.get("$MEASUREMENT"))
print("layers", [l.dxf.name for l in doc.layers])
c = collections.Counter((e.dxf.layer, e.dxftype()) for e in msp)
for k, v in sorted(c.items()): print(v, k)
print("blocks", [b.name for b in doc.blocks if not b.name.startswith("*")][:30])
# text samples per layer
for lay in sorted(set(e.dxf.layer for e in msp if e.dxftype() in ("TEXT","MTEXT"))):
    ts = [e.dxf.text if e.dxftype()=="TEXT" else e.text for e in msp if e.dxf.layer==lay and e.dxftype() in ("TEXT","MTEXT")]
    print(lay, len(ts), ts[:12])
# xdata / extra attributes
e0 = [e for e in msp if e.dxftype()=="LWPOLYLINE"][:3]
for e in e0:
    print(e.dxf.layer, e.dxf.all_existing_dxf_attribs(), e.closed, len(e), e.has_xdata if hasattr(e,'has_xdata') else None)

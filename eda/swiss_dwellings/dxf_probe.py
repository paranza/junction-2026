import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, glob, os, collections, sys
DS = _DATA + "/data/swiss_dwellings"
f = f"{DS}/{sys.argv[1]}.dxf"
doc = ezdxf.readfile(f)
msp = doc.modelspace()
print("version", doc.dxfversion, "insunits", doc.header.get("$INSUNITS"), "measurement", doc.header.get("$MEASUREMENT"), "extmin", doc.header.get("$EXTMIN"), "extmax", doc.header.get("$EXTMAX"))
print("layers:", [(l.dxf.name, l.dxf.color) for l in doc.layers])
print("blocks:", [b.name for b in doc.blocks if not b.name.startswith("*")][:50])
c = collections.Counter((e.dxftype(), e.dxf.layer) for e in msp)
for k, v in sorted(c.items(), key=lambda kv: (kv[0][1], kv[0][0])): print(k, v)
print("paperspace layouts:", doc.layouts.names())
for name in doc.layouts.names():
    if name != "Model":
        ps = doc.layouts.get(name)
        print(name, collections.Counter(e.dxftype() for e in ps))
# Sample text entities
for e in list(msp.query("TEXT MTEXT"))[:40]:
    t = e.dxf.text if e.dxftype()=="TEXT" else e.text
    print(e.dxftype(), e.dxf.layer, repr(t), tuple(round(x,2) for x in e.dxf.insert)[:2], round(e.dxf.get("height", 0) if e.dxftype()=="TEXT" else e.dxf.get("char_height", 0),3), e.dxf.get("color"))
# INSERTs
ins = collections.Counter((e.dxf.name, e.dxf.layer) for e in msp.query("INSERT"))
print("inserts", ins)
# polylines closed
for e in list(msp.query("LWPOLYLINE"))[:5]:
    print(e.dxf.layer, e.closed, len(e), [tuple(round(v,2) for v in p[:2]) for p in e.get_points()][:6])
# XDATA / extension dicts?
n_x = sum(1 for e in msp if e.has_xdata)
print("entities with xdata", n_x)
for e in msp:
    if e.has_xdata:
        print(e.dxftype(), e.dxf.layer, [ (a, list(e.get_xdata(a))) for a in e.xdata.data.keys()][:3]); break

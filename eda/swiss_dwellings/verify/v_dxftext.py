import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, sys
D = _DATA + "/data/swiss_dwellings"
f = sys.argv[1]
doc = ezdxf.readfile(f"{D}/{f}.dxf")
msp = doc.modelspace()
for e in msp:
    if e.dxftype() == "TEXT":
        a = e.dxf
        print(a.layer, repr(a.text), "ins", tuple(round(v,3) for v in a.insert)[:2], "h", round(a.height,3), "style", a.style, "halign", a.get("halign"), "valign", a.get("valign"), "color", a.get("color"), "rot", a.get("rotation"))
for e in msp:
    if e.dxf.layer in ("UNIT_OUTLINE",):
        print(e.dxf.layer, e.dxftype(), e.dxf.all_existing_dxf_attribs(), len(e))
for lay in ["DOOR","WINDOW","FIXTURE","WALL","ROOM_OUTLINE"]:
    es = [e for e in msp if e.dxf.layer == lay]
    import collections
    print(lay, collections.Counter((e.dxftype(), len(e) if e.dxftype()=="LWPOLYLINE" else None, e.closed if e.dxftype()=="LWPOLYLINE" else None, e.dxf.get("color"), e.dxf.get("linetype"), e.dxf.get("lineweight")) for e in es))

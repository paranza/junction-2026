import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, sys, collections
DS = _DATA + "/data/swiss_dwellings"
doc = ezdxf.readfile(f"{DS}/{sys.argv[1]}.dxf"); msp = doc.modelspace()
for lay in ["FIXTURE", "DOOR", "WINDOW"]:
    print("=====", lay)
    for e in msp.query(f"*[layer=='{lay}']"):
        if e.dxftype() == "CIRCLE":
            print("CIRCLE", tuple(round(v, 2) for v in e.dxf.center)[:2], "r", round(e.dxf.radius, 3))
        elif e.dxftype() == "ARC":
            print("ARC", tuple(round(v, 2) for v in e.dxf.center)[:2], "r", round(e.dxf.radius, 3), round(e.dxf.start_angle), round(e.dxf.end_angle))
        else:
            pts = [tuple(round(v, 2) for v in p[:2]) for p in e.get_points()]
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            print("PL", "closed" if e.closed else "open", len(pts), f"w={max(xs)-min(xs):.2f} h={max(ys)-min(ys):.2f}", pts[:4])

import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, sys, collections, math
DS = _DATA + "/data/swiss_dwellings"
msp = ezdxf.readfile(f"{DS}/{sys.argv[1]}.dxf").modelspace()
ents = list(msp.query("*[layer=='DOOR']"))
# entity order: print sequence to see grouping
for i, e in enumerate(ents):
    if e.dxftype() == "ARC":
        print(i, "ARC", round(e.dxf.center[0],2), round(e.dxf.center[1],2), "r", round(e.dxf.radius,3), round(e.dxf.start_angle), round(e.dxf.end_angle))
    else:
        pts = [(round(p[0],2), round(p[1],2)) for p in e.get_points()]
        print(i, "PL", len(pts), "closed" if e.closed else "open", pts)

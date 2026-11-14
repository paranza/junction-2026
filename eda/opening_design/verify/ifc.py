import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ifcopenshell, glob, os
import ifcopenshell.util.unit as U
R=_DATA + "/data/opening_design/"
for p in sorted(glob.glob(R+"**/*.ifc",recursive=True)):
    try:
        f=ifcopenshell.open(p)
        c={t:len(f.by_type(t)) for t in ("IfcWall","IfcWallStandardCase","IfcDoor","IfcWindow","IfcSpace","IfcBuildingStorey","IfcSlab","IfcStair")}
        try: s=U.calculate_unit_scale(f)
        except Exception as e: s=repr(e)[:40]
        app=[a.ApplicationFullName for a in f.by_type("IfcApplication")][:1]
        print(os.path.relpath(p,R)[:90], f.schema, round(os.path.getsize(p)/1e6,1),"MB", "scale",s, app, c, flush=True)
    except Exception as e: print("FAIL",os.path.relpath(p,R),repr(e)[:100],flush=True)

import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, glob, os, collections
import pandas as pd
DS = _DATA + "/data/swiss_dwellings"
WD = _ROOT + "/eda/swiss_dwellings"
en = pd.read_csv(f"{WD}/questions_en_families.csv")
ans = en.pivot_table(index="path", columns="family", values="answer", aggfunc="first")
rows = []
for f in sorted(glob.glob(f"{DS}/*.dxf")):
    msp = ezdxf.readfile(f).modelspace()
    arcs = [(round(e.dxf.center[0], 4), round(e.dxf.center[1], 4), round(e.dxf.radius, 4), round(e.dxf.start_angle, 2), round(e.dxf.end_angle, 2)) for e in msp.query("ARC[layer=='DOOR']")]
    door_pl = [e for e in msp.query("LWPOLYLINE[layer=='DOOR']")]
    win_closed = [e for e in msp.query("LWPOLYLINE[layer=='WINDOW']") if e.closed]
    win_closed_u = {tuple(round(v, 4) for p in e.get_points() for v in p[:2]) for e in win_closed}
    key = "data/swiss_dwellings/" + os.path.basename(f)[:-4] + ".pdf"
    rows.append(dict(file=os.path.basename(f)[:-4], arcs=len(arcs), arcs_unique=len(set(arcs)), door_pl=len(door_pl),
                     ans_doors=ans.loc[key, "count_doors"], win_closed=len(win_closed), win_unique=len(win_closed_u), ans_windows=ans.loc[key, "count_windows"]))
s = pd.DataFrame(rows)
print(s.to_string())
print("doors == arcs:", (s.arcs == s.ans_doors).sum(), "/", len(s), " doors == unique arcs:", (s.arcs_unique == s.ans_doors).sum())
print("windows == closed:", (s.win_closed == s.ans_windows).sum(), " windows == unique closed:", (s.win_unique == s.ans_windows).sum())
print("files with duplicate arcs:", (s.arcs != s.arcs_unique).sum(), " total dup arcs:", (s.arcs - s.arcs_unique).sum())
s.to_csv(f"{WD}/doors_windows.csv", index=False)

import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, glob, os
import pandas as pd
DS = _DATA + "/data/swiss_dwellings"
WD = _ROOT + "/eda/swiss_dwellings"
s = pd.read_csv(f"{WD}/doors_windows.csv")
fr, fru, arcs_no_frame = [], [], []
for f in s.file:
    msp = ezdxf.readfile(f"{DS}/{f}.dxf").modelspace()
    frames = [tuple(round(v, 4) for p in e.get_points() for v in p[:2]) for e in msp.query("LWPOLYLINE[layer=='DOOR']") if len(e) == 5]
    fr.append(len(frames)); fru.append(len(set(frames)))
s["frames"] = fr; s["frames_unique"] = fru
print("doors == frames:", (s.frames == s.ans_doors).sum(), "/", len(s), "; doors == unique frames:", (s.frames_unique == s.ans_doors).sum())
print(s[s.frames != s.ans_doors][["file", "arcs", "arcs_unique", "frames", "frames_unique", "ans_doors"]])
s.to_csv(f"{WD}/doors_windows.csv", index=False)

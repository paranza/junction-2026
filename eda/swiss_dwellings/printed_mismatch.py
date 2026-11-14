import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
import pandas as pd
WD = _ROOT + "/eda/swiss_dwellings"
R = pd.read_csv(f"{WD}/dxf_rooms.csv")
P = R.dropna(subset=["printed"]).copy()
P["diff"] = P.printed - P.area.round(2)
print(P[P["diff"].abs() >= 0.005][["file", "num", "label", "printed", "area", "diff"]].to_string())

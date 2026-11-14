import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
import sys, glob, os, collections
sys.path.insert(0, _ROOT + "/eda/swiss_dwellings")
import dxf_model as M
import pandas as pd
WD = _ROOT + "/eda/swiss_dwellings"
rows = []
for f in sorted(glob.glob(f"{M.DS}/*.dxf")):
    name = os.path.basename(f)[:-4]
    m = M.load(name)
    for r in m["rooms"]:
        rows.append(dict(file=name, num=r["num"], label=r["label"], printed=r["printed"], area=r["area"], unit=r["unit"], h=r["h"], nopoly=r["poly"] is None))
    tags = [u["tag"] for u in m["units"]]
    if any(t is None for t in tags): print("untagged unit in", name, tags)
R = pd.DataFrame(rows)
R.to_csv(f"{WD}/dxf_rooms.csv", index=False)
print("rooms", len(R), "no polygon", R.nopoly.sum(), "unlabelled", R.label.isna().sum())
print(R.label.value_counts(dropna=False).to_string())
print("unit tags:", R.unit.str.split().str[0].value_counts(dropna=False).to_dict())
print("unlabelled rooms area describe:", R[R.label.isna()].area.describe().to_dict())
# printed vs polygon area
P = R.dropna(subset=["printed"])
d = (P.printed - P.area.round(2)).abs()
print("printed rooms", len(P), "printed==round(area,2):", (d < 0.005).sum(), "max diff", d.max())

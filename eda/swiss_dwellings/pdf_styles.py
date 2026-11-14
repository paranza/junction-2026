import pymupdf, glob, os, collections, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_model as P
WD = os.path.dirname(os.path.abspath(__file__))
dx = pd.read_csv(f"{WD}/dxf_survey.csv").set_index("file")
rows = []
for f in sorted(glob.glob(f"{P.DS}/*.pdf")):
    name = os.path.basename(f)[:-4]
    page = pymupdf.open(f)[0]
    c = collections.Counter()
    for d in page.get_drawings():
        k = "".join(sorted(set(it[0] for it in d["items"])))
        c[(d["type"], P.RGB(d.get("color")), P.RGB(d.get("fill")), round(d["width"], 3) if d.get("width") else None, k)] += 1
    r = {"file": name}; r.update({str(k): v for k, v in c.items()}); rows.append(r)
S = pd.DataFrame(rows).set_index("file").fillna(0)
# drop legend-constant styles: report mean, std and correlation with each DXF layer count
cols = ["ROOM_OUTLINE:LWPOLYLINE", "WALL:HATCH", "WALL:LWPOLYLINE", "WINDOW:LWPOLYLINE", "FIXTURE:LWPOLYLINE", "UNIT_OUTLINE:LWPOLYLINE", "DOOR:LWPOLYLINE", "DOOR:ARC", "FIXTURE:CIRCLE"]
out = []
for c in S.columns:
    best = max(cols, key=lambda L: abs(S[c].corr(dx.loc[S.index, L])) if S[c].std() > 0 else 0)
    ratio = (S[c] / dx.loc[S.index, best].replace(0, float("nan"))).median()
    out.append((int(S[c].sum()), S[c].min(), S[c].max(), c, best, round(S[c].corr(dx.loc[S.index, best]), 3) if S[c].std() > 0 else None, round(ratio, 3)))
for o in sorted(out, reverse=True): print(o)
S.to_csv(f"{WD}/pdf_styles.csv")

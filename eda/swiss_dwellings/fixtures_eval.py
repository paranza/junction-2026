import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
import sys, glob, os, collections
sys.path.insert(0, _ROOT + "/eda/swiss_dwellings")
import fixtures as FX, ezdxf
import pandas as pd
WD = _ROOT + "/eda/swiss_dwellings"
en = pd.read_csv(f"{WD}/questions_en_families.csv")
ans = en.pivot_table(index="path", columns="family", values="answer", aggfunc="first")
def kind(g):
    k = collections.Counter(q["kind"] for q in g["parts"])
    circ = [q["r"] for q in g["parts"] if q["kind"] == "circle"]
    if k.get("open69"): return "bathtub"
    if k.get("open48") and k.get("open2"): return "wc"
    if k.get("open48") and circ: return "washbasin"
    if k.get("open5") and circ: return "shower"
    if len(circ) >= 4: return "kitchen"
    if len(circ) == 1 and not k.get("open2"): return "washer"
    if k.get("open2") == 2 and not circ: return "x_box"
    if k.get("open2", 0) >= 3: return "stairs"
    if not g["parts"]: return "empty"
    return "other"
rows = []
for f in sorted(glob.glob(f"{FX.DS}/*.dxf")):
    name = os.path.basename(f)[:-4]
    gs = FX.groups(ezdxf.readfile(f).modelspace())
    c = collections.Counter(kind(g) for g in gs)
    cu = collections.Counter(kind(g) for g in {g["frame"]["key"]: g for g in gs}.values())
    key = f"data/swiss_dwellings/{name}.pdf"
    r = dict(file=name)
    for k, fam in [("wc", "count_wc"), ("washbasin", "count_washbasins"), ("bathtub", "count_bathtubs"), ("shower", "count_showers")]:
        r[k] = c.get(k, 0); r[k + "_u"] = cu.get(k, 0); r[k + "_ans"] = ans.loc[key, fam] if fam in ans.columns else None
    r["empty"] = c.get("empty", 0); r["washer"] = c.get("washer", 0); r["other"] = c.get("other", 0)
    rows.append(r)
s = pd.DataFrame(rows)
for k in ["wc", "washbasin", "bathtub", "shower"]:
    m = s[k + "_ans"].notna()
    print(k, "asked", m.sum(), "== raw:", (s[m][k] == s[m][k + "_ans"]).sum(), " == unique:", (s[m][k + "_u"] == s[m][k + "_ans"]).sum())
pd.set_option("display.width", 250)
print(s[(s.wc != s.wc_ans) | (s.washbasin != s.washbasin_ans) | ((s.bathtub != s.bathtub_ans) & s.bathtub_ans.notna()) | ((s.shower != s.shower_ans) & s.shower_ans.notna())].to_string())
print("empty frames total", s["empty"].sum(), "washer", s["washer"].sum(), "other", s["other"].sum())
s.to_csv(f"{WD}/fixtures_eval.csv", index=False)

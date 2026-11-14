"""Mode-prediction baselines per template and cross-template consistency checks on the ground truth."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import os
import pandas as pd
OUT = _ROOT + "/eda/cubicasa5k"
W = pd.read_csv(os.path.join(OUT, "answers_wide.csv"), index_col=0)
T = ["windows", "floors", "toilets", "sinks", "shower_bath", "doors", "saunas", "kitchens", "bedrooms", "wc_rooms", "bathrooms", "balconies"]
rows = []
for t in T:
    s = W[t].dropna()
    mode = s.mode().iloc[0]
    rows.append(dict(template=t, n=len(s), mode=int(mode), mode_acc=round((s == mode).mean(), 3),
                     within1=round(((s - mode).abs() <= 1).mean(), 3), mean=round(s.mean(), 2), sd=round(s.std(), 2)))
B = pd.DataFrame(rows)
print(B.to_string(index=False))
B.to_csv(os.path.join(OUT, "mode_baseline.csv"), index=False)
n_q = sum(W[t].notna().sum() for t in T)
print("question-weighted mode baseline accuracy:", round(sum(r["mode_acc"] * r["n"] for r in rows) / n_q, 3), "over", n_q, "image-template pairs (each asked twice, EN+FI)")

def chk(name, mask):
    m = mask.fillna(False)
    print(f"{name}: {int(m.sum())} images", list(W.index[m])[:8])
chk("wc_rooms > toilets", W.wc_rooms > W.toilets)
chk("toilets == 0 and (wc_rooms>=1 or bathrooms>=1)", (W.toilets == 0) & ((W.wc_rooms >= 1) | (W.bathrooms >= 1)))
chk("toilets > wc_rooms + bathrooms (both asked)", W.wc_rooms.notna() & W.bathrooms.notna() & (W.toilets > W.wc_rooms + W.bathrooms))
chk("sinks < toilets", W.sinks < W.toilets)
chk("kitchens == 0", W.kitchens == 0)
chk("shower_bath == 0 and bathrooms >= 1", (W.shower_bath == 0) & (W.bathrooms >= 1))
chk("doors < bedrooms + 1", W.doors < W.bedrooms + 1)
print("\nfloors vs toilets mean:", W.groupby("floors").toilets.mean().round(2).to_dict(), W.floors.value_counts().to_dict())
print("windows by floors (median):", W.groupby("floors").windows.median().to_dict())
print("corr windows~megapixels:", round(W.windows.corr(W.megapixels), 3), " windows~doors:", round(W.windows.corr(W.doors), 3))

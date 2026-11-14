"""Score manual counts (manual_counts.csv) against ground truth; verify gt column equals questions.jsonl."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import os
import pandas as pd
OUT = _ROOT + "/eda/cubicasa5k"
m = pd.read_csv(os.path.join(OUT, "manual_counts.csv"))
q = pd.read_csv(os.path.join(OUT, "answers_wide.csv"), index_col=0)
for r in m.itertuples():
    assert q.loc[r.file, r.template] == r.gt, (r.file, r.template)
print("gt verified:", len(m), "rows,", m.file.nunique(), "images")
v = m[m.status != "unverified"].copy()
v["ok"] = (v["mine"].astype(float) == v["gt"].astype(float)).astype(int)
best = v["alt"].where(v["alt"].notna(), v["mine"])
v["alt_ok"] = (best.astype(float) == v["gt"].astype(float)).astype(int)
t = v.groupby("template").agg(n=("ok", "size"), k_natural=("ok", "sum"), k_best_convention=("alt_ok", "sum"))
print(t.to_string())
print("total natural", v.ok.sum(), "/", len(v), "| best convention", v.alt_ok.sum(), "/", len(v))
print("unverified rows:", (m.status == "unverified").sum())
print(v[v.ok == 0][["file", "template", "gt", "mine", "alt", "note"]].to_string())
t.to_csv(os.path.join(OUT, "manual_counts_summary.csv"))

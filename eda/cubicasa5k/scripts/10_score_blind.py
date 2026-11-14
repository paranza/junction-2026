"""Score blind counts (written before looking at answers) against ground truth."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import os
import pandas as pd
OUT = _ROOT + "/eda/cubicasa5k"
b = pd.read_csv(os.path.join(OUT, "blind_counts.csv"))
W = pd.read_csv(os.path.join(OUT, "answers_wide.csv"), index_col=0)
b["gt"] = [W.loc[f, t] for f, t in zip(b.file, b.template)]
b = b[b["gt"].notna()].copy()
b["ok"] = (b["mine"] == b["gt"]).astype(int)
b["ok_any"] = ((b["mine"] == b["gt"]) | (b["alt"] == b["gt"])).astype(int)
t = b.groupby("template").agg(n=("ok", "size"), k_first_guess=("ok", "sum"), k_first_or_alt=("ok_any", "sum"))
print(t.to_string())
print("total first guess", b.ok.sum(), "/", len(b), "| first or alternative", b.ok_any.sum(), "/", len(b))
print(b[b.ok == 0][["file", "template", "gt", "mine", "alt", "note"]].to_string())
b.to_csv(os.path.join(OUT, "blind_counts_scored.csv"), index=False)

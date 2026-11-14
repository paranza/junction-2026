"""Score my blind counts against ground truth (exact match) per template."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import os
import pandas as pd
OUT = _ROOT + "/eda/cubicasa5k/verify"
B = pd.read_csv(os.path.join(OUT, "blind_counts.csv"))
W = pd.read_csv(os.path.join(OUT, "wide.csv"), index_col=0)
B["gt"] = [W.loc[f, t] for f, t in zip(B["file"], B["template"])]
assert B["gt"].notna().all()
B["ok"] = (B["mine"] == B["gt"]).astype(int)
B["ok_any"] = ((B["mine"] == B["gt"]) | (B["alt"] == B["gt"])).astype(int)
B.to_csv(os.path.join(OUT, "blind_counts_scored.csv"), index=False)
print(B[["file", "template", "mine", "alt", "gt", "ok", "ok_any"]].to_string())
print("overall", B["ok"].sum(), "/", len(B), " with alt", B["ok_any"].sum())
print(B.groupby("template")[["ok", "ok_any"]].agg(["sum", "count"]).to_string())

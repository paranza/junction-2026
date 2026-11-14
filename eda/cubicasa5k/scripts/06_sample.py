"""Fixed-seed stratified sample for manual ground-truth counting (seed 7, 3/3/4 per style)."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import os, random
import pandas as pd
OUT = _ROOT + "/eda/cubicasa5k"
W = pd.read_csv(os.path.join(OUT, "answers_wide.csv"), index_col=0)
rng = random.Random(7)
pick = []
for pre, k in [("colorful", 3), ("high_quality", 3), ("high_quality_architectural", 4)]:
    pick += rng.sample(sorted(W[W.prefix == pre].index), k)
S = W.loc[pick]
S.to_csv(os.path.join(OUT, "manual_sample_answers.csv"))
pd.set_option("display.width", 250)
print(S.to_string())

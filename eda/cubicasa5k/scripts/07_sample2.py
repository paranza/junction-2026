"""Second fixed-seed sample (seed 11) for window/door convention checks, excluding sample 1."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import os, random
import pandas as pd
OUT = _ROOT + "/eda/cubicasa5k"
W = pd.read_csv(os.path.join(OUT, "answers_wide.csv"), index_col=0)
s1 = set(pd.read_csv(os.path.join(OUT, "manual_sample_answers.csv")).file)
rng = random.Random(11)
pick = []
for pre, k in [("colorful", 3), ("high_quality", 4), ("high_quality_architectural", 5)]:
    pool = sorted(f for f in W[W.prefix == pre].index if f not in s1)
    pick += rng.sample(pool, k)
S = W.loc[pick]
S.to_csv(os.path.join(OUT, "manual_sample2_answers.csv"))
pd.set_option("display.width", 250)
print(S[["windows", "doors", "toilets", "sinks", "shower_bath", "floors", "w", "h"]].to_string())

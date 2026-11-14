"""Blind window-count sample: seed 21, 3 high_quality_architectural images never viewed before.
Prints only file names and sizes (no ground truth) so counts can be made blind."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import os, random
import pandas as pd
OUT = _ROOT + "/eda/cubicasa5k"
seen = {v.split("_full")[0] + ".png" for v in os.listdir(os.path.join(OUT, "views")) if v.endswith("_full.png")}
for f in ["text_sample_answers.csv", "text_sample2_answers.csv"]:
    seen |= set(pd.read_csv(os.path.join(OUT, f)).file)
W = pd.read_csv(os.path.join(OUT, "answers_wide.csv"), index_col=0)
pool = sorted(f for f in W.index if f not in seen and W.loc[f, "prefix"] == "high_quality_architectural")
pick = random.Random(21).sample(pool, 3)
for f in pick:
    print(f, int(W.loc[f, "w"]), int(W.loc[f, "h"]))
open(os.path.join(OUT, "window_blind_sample.txt"), "w").write("\n".join(pick) + "\n")

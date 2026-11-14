"""Blind sample (seed 2026) of images the analyst never viewed: 3 architectural, 1 high_quality, 1 colorful.
Prints only names, sizes and which templates are asked (no answers). Renders each at long side <= 2000 px."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, random, re
import pandas as pd
from PIL import Image
DS = _DATA + "/data/cubicasa5k"
AN = _ROOT + "/eda/cubicasa5k"
OUT = os.path.join(AN, "verify")
W = pd.read_csv(os.path.join(OUT, "wide.csv"), index_col=0)
seen = set()
for v in os.listdir(os.path.join(AN, "views")) + os.listdir(os.path.join(AN, "contact")):
    m = re.match(r"((?:colorful|high_quality_architectural|high_quality)-\d+)", v)
    if m: seen.add(m.group(1) + ".png")
for f in ["manual_counts.csv", "text_observations.csv", "blind_counts.csv", "window_blind_counts.csv", "text_sample_answers.csv", "text_sample2_answers.csv", "manual_sample_answers.csv", "manual_sample2_answers.csv"]:
    d = pd.read_csv(os.path.join(AN, f))
    seen |= set(d.iloc[:, 0].astype(str))
seen |= set(open(os.path.join(AN, "blind_sample.txt")).read().split()) | set(open(os.path.join(AN, "window_blind_sample.txt")).read().split())
seen &= set(W.index)
print("analyst-touched images:", len(seen))
rng = random.Random(2026)
pick = []
for st, k in [("high_quality_architectural", 3), ("high_quality", 1), ("colorful", 1)]:
    pool = sorted(f for f in W.index if f not in seen and W.loc[f, "style"] == st)
    print(st, "unseen pool", len(pool))
    pick += rng.sample(pool, k)
T = [c for c in W.columns if c != "style"]
for f in pick:
    im = Image.open(os.path.join(DS, f)).convert("RGB")
    s = min(2000 / max(im.size), 2.0)
    r = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    r.save(os.path.join(OUT, "views", f.replace(".png", "_full.png")))
    print(f, im.size, "scale", round(s, 2), "asked:", [t for t in T if pd.notna(W.loc[f, t])])
open(os.path.join(OUT, "blind_sample.txt"), "w").write("\n".join(pick) + "\n")

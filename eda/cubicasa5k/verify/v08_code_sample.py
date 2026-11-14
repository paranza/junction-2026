"""Second blind sample (seed 2027): 5 architectural images unseen by analyst and by v04. For window-code rule,
apartment-code rule, label orientation and multi-unit status. Prints names/sizes/asked templates only."""
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
seen = set(open(os.path.join(OUT, "blind_sample.txt")).read().split())
for v in os.listdir(os.path.join(AN, "views")):
    m = re.match(r"((?:colorful|high_quality_architectural|high_quality)-\d+)", v)
    if m: seen.add(m.group(1) + ".png")
for f in ["manual_counts.csv", "text_observations.csv", "blind_counts.csv", "window_blind_counts.csv", "text_sample_answers.csv", "text_sample2_answers.csv", "manual_sample_answers.csv", "manual_sample2_answers.csv"]:
    seen |= set(pd.read_csv(os.path.join(AN, f)).iloc[:, 0].astype(str))
seen |= set(open(os.path.join(AN, "blind_sample.txt")).read().split()) | set(open(os.path.join(AN, "window_blind_sample.txt")).read().split())
pool = sorted(f for f in W.index if f not in seen and W.loc[f, "style"] == "high_quality_architectural")
pick = random.Random(2027).sample(pool, 5)
T = [c for c in W.columns if c != "style"]
for f in pick:
    im = Image.open(os.path.join(DS, f)).convert("RGB")
    s = min(2000 / max(im.size), 2.0)
    im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS).save(os.path.join(OUT, "views", f.replace(".png", "_full.png")))
    print(f, im.size, "scale", round(s, 2), "asked:", [t for t in T if pd.notna(W.loc[f, t])])
open(os.path.join(OUT, "code_sample.txt"), "w").write("\n".join(pick) + "\n")

"""Question templates and answer distributions for cubicasa5k."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, os, re, collections
import pandas as pd

DS = _DATA + ""
OUT = _ROOT + "/eda/cubicasa5k"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
q = pd.DataFrame([r for r in rows if r["path"].startswith("data/cubicasa5k/")])
print("n questions", len(q), "n images", q.path.nunique())
print(q.type.value_counts(), q.unit.value_counts())
print("answer python types", collections.Counter(type(a).__name__ for a in q.answer))
# distinct question strings
vc = q.question.value_counts()
print("distinct question strings", len(vc))
for s, n in vc.items():
    print(n, "|", s)
q.to_csv(os.path.join(OUT, "questions_cubicasa5k.csv"), index=False)

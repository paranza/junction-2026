import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, re, collections, sys
import pandas as pd
DS = _DATA + ""
rows = [json.loads(l) for l in open(f"{DS}/questions.jsonl", encoding="utf-8")]
df = pd.DataFrame(rows)
df = df[df.path.str.startswith("data/ifc_models/")].reset_index(drop=True)
df["file"] = df.path.str.replace("data/ifc_models/", "", regex=False)
df["ext"] = df.file.str.rsplit(".", n=1).str[-1]
# template: replace quoted strings and numbers
def tmpl(q):
    t = re.sub(r"[„\"'‘’“«»]([^„\"'‘’“”«»]*)[“”\"'’»]", "<X>", q)
    t = re.sub(r"\d+(?:[.,]\d+)?", "<N>", t)
    return t
df["template"] = df.question.map(tmpl)
df.to_pickle("ifc_q.pkl")
print(df.groupby(["file","type","unit"]).size().to_string())
print()
print(df.type.value_counts().to_string())
print()
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 200)
vc = df.groupby(["template","type","unit"]).size().sort_values(ascending=False)
print(len(vc), "templates")
print(vc.to_string())

import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Independent look at swiss_dwellings questions: types, extensions, language pairs, templates.
import json, re, collections, sys
D = _DATA + ""
rows = [json.loads(l) for l in open(D + "/questions.jsonl", encoding="utf-8")]
print("total lines", len(rows))
sw = [r for r in rows if r["path"].startswith("data/swiss_dwellings/")]
print("swiss rows", len(sw))
print("types", collections.Counter(r["type"] for r in sw))
print("units", collections.Counter(r["unit"] for r in sw))
print("ext", collections.Counter(r["path"].rsplit(".",1)[1] for r in sw))
print("files", len(set(r["path"] for r in sw)))
print("answer python types", collections.Counter(type(r["answer"]).__name__ for r in sw))
# template skeleton: replace quoted strings and numbers
def skel(q):
    q = re.sub(r"«[^»]*»", "«X»", q)
    q = re.sub(r"'[^?]*?'(?=[ )?])", "'X'", q)
    q = re.sub(r"\(\s*'X'\s*\)", "('X')", q)
    q = re.sub(r"\b[U]?\d+\.\d+\b", "N", q)
    q = re.sub(r"\b(apartment|appartement|appartamento|Wohnung|l'appartement|dell'appartamento)\s+[A-Z]\b", r"\1 L", q)
    return q
c = collections.Counter(skel(r["question"]) for r in sw)
print("n skeletons", len(c))
for k, v in c.most_common():
    print(v, "|", k)

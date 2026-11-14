"""Independent re-load of cubicasa5k questions: templates, EN/FI twins, answer types, mode baseline."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, collections, os
DS = _DATA + ""
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
print("total rows", len(rows))
cc = [r for r in rows if r["path"].startswith("data/cubicasa5k/")]
print("cubicasa rows", len(cc), "paths", len({r["path"] for r in cc}))
print("types", collections.Counter((r["type"], r["unit"]) for r in cc))
print("answer py types", collections.Counter(type(r["answer"]).__name__ for r in cc))
qs = collections.Counter(r["question"] for r in cc)
print("distinct questions", len(qs))
for q, n in sorted(qs.items(), key=lambda x: -x[1]):
    print(n, q)
# duplicates
print("dup (path,question)", sum(v - 1 for v in collections.Counter((r["path"], r["question"]) for r in cc).values() if v > 1))
# is the same question string used in other sources?
other = collections.Counter(r["path"].split("/")[1] for r in rows if r["question"] in qs and not r["path"].startswith("data/cubicasa5k/"))
print("same strings in other sources", other)

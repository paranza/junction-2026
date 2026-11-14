import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, collections, pandas as pd
DS=_DATA + ""
rows=[json.loads(l) for l in open(DS+"/questions.jsonl",encoding="utf-8")]
print("total lines",len(rows))
q=pd.DataFrame(rows)
q=q[q.path.str.startswith("data/ifc_models/")].reset_index(drop=True)
print("ifc_models q",len(q))
print(q.path.value_counts())
print(q.type.value_counts())
print(q.unit.value_counts())
q["ext"]=q.path.str.rsplit(".",n=1).str[-1]
print(q.ext.value_counts())
print(pd.crosstab(q.path,q.type))
q.to_pickle("q.pkl")
# answer dtypes
print(collections.Counter(type(a).__name__ for a in q.answer))

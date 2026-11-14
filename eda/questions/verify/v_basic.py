import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, collections, os, sys
DS = _DATA + ""
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
print("lines", len(rows))
print("keys", collections.Counter(tuple(sorted(r.keys())) for r in rows))
src = collections.Counter(r["path"].split("/")[1] for r in rows)
print("by source", src)
ext = collections.Counter(os.path.splitext(r["path"])[1].lower() for r in rows)
print("by ext", ext)
print("by type", collections.Counter(r["type"] for r in rows))
print("by unit", collections.Counter(r["unit"] for r in rows))
print("type x unit", collections.Counter((r["type"], r["unit"]) for r in rows))
paths = set(r["path"] for r in rows)
print("distinct files", len(paths))
print("distinct question strings", len(set(r["question"] for r in rows)))
missing = [p for p in paths if not os.path.exists(os.path.join(DS, p))]
print("paths missing on disk", len(missing), missing[:5])
# files per source
fs = collections.Counter(p.split("/")[1] for p in paths)
print("files w/ q by source", fs)
# questions per file
qpf = collections.Counter(r["path"] for r in rows)
import statistics
v = sorted(qpf.values())
print("qpf min/median/mean/max", v[0], statistics.median(v), sum(v)/len(v), v[-1])
for s in sorted(fs):
    vs = sorted(c for p, c in qpf.items() if p.split("/")[1] == s)
    print(" ", s, len(vs), vs[0], statistics.median(vs), vs[-1])
# answer python types
print("answer py types by type", collections.Counter((r["type"], type(r["answer"]).__name__) for r in rows))
# dup (path,question)
pq = collections.Counter((r["path"], r["question"]) for r in rows)
print("dup path+question", sum(1 for k, c in pq.items() if c > 1))

import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, collections, os, re
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
def norm(q):
    q = re.sub(r"'[^']*'|«\s?[^»]*»|„[^“”]*[“”]|\"[^\"]*\"|“[^”]*”", "<Q>", q)
    q = re.sub(r"\bapartment [A-Z]\b", "apartment <L>", q)
    q = re.sub(r"\b(?:room|Raum|pièce|locale|ruumi)\s+\S*\d\S*", "room <ID>", q)
    q = re.sub(r"\d+(?:[.,]\d+)*", "<N>", q)
    return q
src = [r["path"].split("/")[1] for r in rows]
T = collections.Counter()
for r, L, s in zip(rows, langs, src):
    if L == "en": T[(s, norm(r["question"]))] += 1
bysrc = collections.defaultdict(list)
for (s, t), c in T.items(): bysrc[s].append((c, t))
for s in sorted(bysrc):
    v = sorted(bysrc[s], reverse=True)
    print(f"== {s}: {len(v)} English templates, {sum(c for c,_ in v)} lines")
    for c, t in v[:40]:
        print(f"  {c:5d}  {t[:160]}")

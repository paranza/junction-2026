import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Does each (English template, language) map to exactly one translated template? Are quoted slots identical across twins?
import json, os, re, collections
DS = _DATA + ""
OUT = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
QT = r"'(?:[^']|'(?=\w))*'|«\s?[^»]*?\s?»|„[^“”]*[“”]|\"[^\"]*\"|“[^”]*”"
def slots(q): return [re.sub(r"^['«„\"“]\s?|\s?['»“”\"]$", "", s) for s in re.findall(QT, q)]
def norm(q):
    q = re.sub(QT, "<Q>", q)
    q = re.sub(r"\b[A-H]\b", "<L>", q)
    return re.sub(r"\d+(?:[.,]\d+)*", "<N>", q)
M = collections.defaultdict(set); same = diff = 0; ex = []
for i in range(1, len(rows)):
    if langs[i] == "en": continue
    e, t = rows[i - 1], rows[i]
    M[(norm(e["question"]), langs[i])].add(norm(t["question"]))
    if slots(e["question"]) == slots(t["question"]): same += 1
    else:
        diff += 1
        if len(ex) < 6: ex.append((e["question"][:90], t["question"][:90]))
print("(English template, language) combos", len(M), "mapping to >1 local template", sum(1 for v in M.values() if len(v) > 1))
for k, v in M.items():
    if len(v) > 1: print("  MULTI", k[1], k[0][:70], "->", [x[:60] for x in v][:3])
print("quoted slots identical", same, "different", diff)
for x in ex: print("  ", x)

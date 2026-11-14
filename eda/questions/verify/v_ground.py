import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, os, re, collections
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
EN = [i for i, L in enumerate(langs) if L == "en"]
def scope(r):
    s = r["path"].split("/")[1]; q = r["question"]
    if s == "ifc_bench": return "ifc_bench report"
    if s == "opening_design":
        if re.search(r"\b(door|room) \d{3}|door \d{3}\.[A-Z]|room \d{3}|type [A-Z]\d|U\d\d|types? [A-Z]{2}|named|floor finish|base \(B2\)|W1|F\d", q): return "named row/type in schedule"
        return "whole schedule"
    if s == "cubicasa5k": return "whole drawing"
    if s == "swiss_dwellings":
        if "room " in q and re.search(r"room \S*\d", q): return "one room by id"
        if "labelled" in q: return "label set"
        if "apartment " in q and re.search(r"apartment [A-Z]\b", q): return "one apartment"
        return "whole drawing"
    if s == "ifc_models":
        if "of the room" in q: return "one room by name+storey"
        if "in the model" in q: return "whole model"
        return "one storey"
    return "?"
c = collections.Counter(scope(rows[i]) for i in EN)
n = len(EN)
for k, v in c.most_common(): print(f"{v:5d} {100*v/n:5.1f}%  {k}")
named = sum(v for k, v in c.items() if k not in ("whole drawing", "whole model", "ifc_bench report", "whole schedule"))
print("needs a named entity located:", named, round(100*named/n, 1), "%")
# rule clauses: parenthetical definitions or explicit counting rules in English
rule = re.compile(r"\(|;|\bcount(s|ed)?\b as|do(es)? not count|not counting|excluding|except|including|summing|combined|in total|together", re.I)
k = sum(1 for i in EN if rule.search(rows[i]["question"]))
print("English questions with an inline definition/rule clause (my regex):", k, round(100*k/n, 1), "%")
# breakdown by source
for s in ["cubicasa5k", "swiss_dwellings", "ifc_models", "ifc_bench", "opening_design"]:
    e = [i for i in EN if rows[i]["path"].split("/")[1] == s]
    print("  ", s, sum(1 for i in e if rule.search(rows[i]["question"])), "/", len(e))

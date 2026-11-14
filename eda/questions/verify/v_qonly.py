import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, collections, os, re, statistics, csv
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
INV = _ROOT + "/eda/inventory.csv"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
src = [r["path"].split("/")[1] for r in rows]
EN = [i for i, L in enumerate(langs) if L == "en"]
# --- F18 coverage: drawings = (dir, stem) groups, excluding LICENSE.md
inv = list(csv.DictReader(open(INV)))
print("inventory rows", len(inv), collections.Counter(r["ext"] for r in inv).most_common())
draw = collections.defaultdict(list)
for r in inv:
    p = r["path"]
    if p.endswith("LICENSE.md"): continue
    draw[os.path.splitext(p)[0]].append(r)
asked = set(os.path.splitext(r["path"])[0] for r in rows)
print("drawings", len(draw), "with questions", len(asked & set(draw)), round(100*len(asked & set(draw))/len(draw), 1))
bys = collections.Counter(k.split("/")[1] for k in draw); bya = collections.Counter(k.split("/")[1] for k in asked & set(draw))
for s in sorted(bys): print("  ", s, bys[s], bya.get(s, 0))
# ifc_models: plan PDFs rendered from model IFC should arguably be one drawing family; check alternative grouping
# --- F6 storey attachment: which file carries questions for each (model, storey)
st = collections.defaultdict(collections.Counter)
for i in EN:
    r = rows[i]
    if src[i] != "ifc_models": continue
    m = re.findall(r"on (?:the floor plan of )?'([^']*)'", r["question"])
    key = m[-1] if m else ("MODEL" if "in the model" in r["question"] else "?")
    st[(r["path"].split("/")[-1].split("_")[0], key)][r["path"].split("/")[-1][-30:]] += 1
for k, v in sorted(st.items()): print("  storey-attach", k, dict(v))
# --- F15 ifc_bench text answers
tb = [rows[i] for i in EN if src[i] == "ifc_bench"]
L = sorted(len(str(r["answer"])) for r in tb)
print("ifc_bench", len(tb), "types", collections.Counter(r["type"] for r in tb), "median chars", statistics.median(L), "max", L[-1], ">1000", sum(x > 1000 for x in L), "multi-line", sum("\n" in str(r["answer"]) for r in tb), round(100*sum("\n" in str(r["answer"]) for r in tb)/len(tb), 1))
neg = re.compile(r"\b(no |not |none|n/a|unavailable|absent|cannot|could not|does not|doesn't|isn't|aren't|missing)", re.I)
short_neg = [r for r in tb if len(str(r["answer"])) < 200 and neg.search(str(r["answer"]))]
print("short (<200 chars) answers with a negation", len(short_neg))
for r in short_neg[:60]: print("   NEG:", repr(str(r["answer"])[:150]))
hm = [r for r in tb if r["question"].lower().startswith("how many")]
print("ifc_bench how-many questions", len(hm), "types", collections.Counter(r["type"] for r in hm))
# --- F17 apartment sums vs floor total (swiss), from answers only
fl = {}; ap = collections.defaultdict(list); napt = {}
for i in EN:
    r = rows[i]
    if src[i] != "swiss_dwellings": continue
    if r["question"].startswith("What is the total net floor area in m² of all numbered"): fl[r["path"]] = r["answer"]
    if r["question"].startswith("What is the net floor area of apartment"): ap[r["path"]].append(r["answer"])
    if r["question"].startswith("How many apartments"): napt[r["path"]] = r["answer"]
full = [p for p in ap if len(ap[p]) == napt[p]]
ratios = sorted(sum(ap[p]) / fl[p] for p in full)
print("swiss files where every apartment is asked", len(full), "ratio min/median/max", round(ratios[0], 3), round(statistics.median(ratios), 3), round(ratios[-1], 3), "exceed", sum(x > 1.0001 for x in ratios))
print("apartments asked per file vs count", collections.Counter((napt[p], len(ap.get(p, []))) for p in napt).most_common())
# --- quoted labels with internal apostrophes (parser hazard)
apos = [rows[i]["question"] for i in range(len(rows)) if re.search(r"'[^']*\w'\w[^']*'", rows[i]["question"])]
print("questions whose quoted label contains an apostrophe", len(apos), apos[:3])

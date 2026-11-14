import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, collections, os, re, statistics
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
def norm(q):
    q = re.sub(r"'(?:[^']|'(?=\w))*'|«\s?[^»]*»|„[^“”]*[“”]|\"[^\"]*\"|“[^”]*”", "<Q>", q)
    q = re.sub(r"\bapartment [A-Z]\b", "apartment <L>", q)
    q = re.sub(r"\broom\s+\S*\d\S*", "room <ID>", q)
    q = re.sub(r"\d+(?:[.,]\d+)*", "<N>", q)
    return q
src = [r["path"].split("/")[1] for r in rows]
EN = [i for i, L in enumerate(langs) if L == "en"]
fam = {i: (src[i], norm(rows[i]["question"])) for i in EN}
# template counts after apostrophe fix
T = collections.Counter(fam.values())
print("English templates per source", collections.Counter(s for s, _ in T))
top20 = sum(c for _, c in T.most_common(20))
print("top20 English templates cover", top20, "/", len(EN), round(100*top20/len(EN), 1), "% of English;", round(100*top20/len(rows),1), "% of all lines (en only)")
gen = sum(1 for i in EN if src[i] in ("cubicasa5k", "swiss_dwellings", "ifc_models"))
print("generated-source English", gen, len(EN), round(100*gen/len(EN), 2))
# zeros among English counts
cnt = [i for i in EN if rows[i]["type"] == "count"]
z = [i for i in cnt if rows[i]["answer"] == 0]
print("English count answers", len(cnt), "zeros", len(z), round(100*len(z)/len(cnt), 1))
fz = collections.defaultdict(lambda: [0, 0])
for i in cnt:
    fz[fam[i]][0] += 1; fz[fam[i]][1] += rows[i]["answer"] == 0
for k, (n, nz) in sorted(fz.items(), key=lambda kv: -kv[1][1]/kv[1][0]):
    if nz: print(f"  zero {nz}/{n} = {100*nz/n:.0f}%  {k[0]} | {k[1][:90]}")
# min answer per count family
print("count families never zero and min answer:")
for k, (n, nz) in fz.items():
    if not nz and n >= 5:
        mn = min(rows[i]["answer"] for i in cnt if fam[i] == k)
        print(f"  n={n} min={mn} {k[0]} | {k[1][:90]}")
# any numeric zero in non-count?
print("non-count numeric zero", sum(1 for r in rows if r["type"] in ("area","length","volume") and r["answer"] == 0))
# mode baseline on English counts (in-sample) and leave-one-file-out
hit = 0
for k in fz:
    vals = [rows[i]["answer"] for i in cnt if fam[i] == k]
    m = collections.Counter(vals).most_common(1)[0][1]
    hit += m
print("in-sample mode baseline", hit, len(cnt), round(100*hit/len(cnt), 1))
# leave-one-file-out mode baseline (honest)
hit2 = 0
for i in cnt:
    vals = [rows[j]["answer"] for j in cnt if fam[j] == fam[i] and rows[j]["path"] != rows[i]["path"]]
    if vals:
        m = collections.Counter(vals).most_common()
        top = max(c for _, c in m); cands = sorted(v for v, c in m if c == top)
        hit2 += cands[0] == rows[i]["answer"]
print("leave-one-file-out mode baseline", hit2, len(cnt), round(100*hit2/len(cnt), 1))
# all-lines (incl translations) mode baseline per line
# area small pressure
m2 = [rows[i]["answer"] for i in EN if rows[i]["unit"] == "m2"]
print("English m2 answers", len(m2), "under5", sum(a < 5 for a in m2), round(100*sum(a < 5 for a in m2)/len(m2), 1), "under10", round(100*sum(a < 10 for a in m2)/len(m2), 1), "min", min(m2))
# decimals
def dec(a):
    s = repr(a)
    return len(s.split(".")[1]) if "." in s else 0
print("decimals by (src,type)", collections.Counter((src[i], rows[i]["type"], dec(rows[i]["answer"])) for i in EN if rows[i]["type"] in ("area","length","volume")))
# ft2 questions
for i, r in enumerate(rows):
    if r["unit"] == "ft2": print("FT2", r["answer"], "| unit word in q:", bool(re.search(r"sq|ft|feet|SF|square", r["question"])), "|", r["question"][-110:])
# does every metric quantity question state the unit?
nostate = [r for r in rows if r["unit"] in ("m2","m3","m") and not re.search(r"m²|m2|m³|m3|metres|meters|\bm\b|mètres|metri|meter|Metern|Quadratmeter|neliömetr", r["question"])]
print("metric quantity questions w/o obvious unit token", len(nostate))
for r in nostate[:10]: print("  ", r["unit"], r["question"][:150])

import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, collections, os, re, random
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
SW = {
 "en": "how many what the is are of on in this drawn shown plan floor total which there and does with for".split(),
 "fi": "kuinka monta mikä on pohjapiirustuksessa pohjapiirustukseen yhteensä piirretty huonetta kerroksessa ja".split(),
 "de": "wie viele ist sind der die das auf dem diesem grundriss gesamt welche und im des mit wird".split(),
 "fr": "combien de est sont le la les sur ce plan quelle et du des au dans cet cette".split(),
 "it": "quanti quante quale è sono il la le su questa questo pianta del della e nel di".split(),
 "et": "mitu kui palju on see ruumi korrusel korruse plaanil kokku ja mis millised".split(),
 "da": "hvor mange er der på denne plan hvad og etage samlet rum af i".split(),
}
def strip_quotes(q):
    # remove quoted slot content so labels in other languages do not bias detection
    return re.sub(r"'[^']*'|«[^»]*»|„[^“”]*[“”]|\"[^\"]*\"|“[^”]*”", " ", q)
def lang(q):
    t = re.findall(r"[^\W\d_]+", strip_quotes(q).lower())
    sc = {L: sum(1 for w in t if w in set(ws)) for L, ws in SW.items()}
    best = max(sc, key=sc.get)
    return best, sc
langs = [lang(r["question"])[0] for r in rows]
print(collections.Counter(langs))
# per source
src = [r["path"].split("/")[1] for r in rows]
print(collections.Counter(zip(src, langs)))
# twin check: non-English line i; line i-1 English, same path and answer
non = [i for i, L in enumerate(langs) if L != "en"]
ok = sum(1 for i in non if i > 0 and langs[i-1] == "en" and rows[i-1]["path"] == rows[i]["path"] and rows[i-1]["answer"] == rows[i]["answer"])
print("non-en", len(non), "preceded by en twin same path+answer", ok)
bad = [i for i in non if not (i > 0 and langs[i-1] == "en" and rows[i-1]["path"] == rows[i]["path"] and rows[i-1]["answer"] == rows[i]["answer"])]
for i in bad[:20]:
    print("BAD", i, langs[i-1], rows[i-1]["question"][:90], "||", langs[i], rows[i]["question"][:90])
# en lines with twin
en = [i for i, L in enumerate(langs) if L == "en"]
tw = set(i-1 for i in non)
print("en", len(en), "with twin", sum(1 for i in en if i in tw))
for s in sorted(set(src)):
    e = [i for i in en if src[i] == s]
    print(" ", s, len(e), sum(1 for i in e if i in tw))
# same type/unit across twins
print("twin type+unit agree", sum(1 for i in non if rows[i-1]["type"] == rows[i]["type"] and rows[i-1]["unit"] == rows[i]["unit"]))
# languages per file (non-English)
pf = collections.defaultdict(set)
for i in non: pf[rows[i]["path"]].add(langs[i])
print("files with >1 non-en lang", sum(1 for v in pf.values() if len(v) > 1), "of", len(pf))
print("non-en lang by source", collections.Counter((src[i], langs[i]) for i in non))
# sample 40 lines at random (seed 7) to eyeball
random.seed(7)
with open(os.path.join(OUT, "lang_sample.txt"), "w") as f:
    for i in random.sample(range(len(rows)), 60):
        f.write(f"{langs[i]}\t{rows[i]['question'][:140]}\n")
json.dump(langs, open(os.path.join(OUT, "langs.json"), "w"))

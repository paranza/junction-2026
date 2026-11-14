import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, os, collections, re
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
rooms = json.load(open(os.path.join(OUT, "swiss_rooms.json")))
LEX = {"de": {"Zimmer", "Küche", "Korridor", "Bad", "Wohnen", "Reduit", "Treppenhaus", "Balkon", "Schlafzimmer", "Wohnen/Essen"},
       "fr": {"Pièce", "Cuisine", "Couloir", "Bain", "Séjour", "Réduit", "Balcon", "Chambre à coucher", "Séjour/repas", "Cage d'escalier"},
       "it": {"Stanza", "Cucina", "Corridoio", "Bagno", "Soggiorno", "Ripostiglio", "Balcone", "Camera da letto", "Soggiorno/pranzo", "Vano scala"}}
twin = {}
for i, r in enumerate(rows):
    if r["path"] in rooms and langs[i] != "en": twin[r["path"]] = langs[i]
agree = 0; tally = collections.Counter(); unl = collections.Counter(); asked_unl = []
for p, d in rooms.items():
    labs = [v["label"] for v in d["room"].values() if v["label"]]
    vote = collections.Counter(L for lab in labs for L, s in LEX.items() if lab in s)
    lang = vote.most_common(1)[0][0] if vote else None
    agree += lang == twin.get(p); tally[(lang, twin.get(p))] += 1
    n_unl = sum(1 for v in d["room"].values() if v["label"] is None)
    unl[n_unl > 0] += 1
print("label-language == twin language:", agree, "/", len(rooms), dict(tally))
print("files with numbered rooms lacking a printed label above:", dict(unl))
# what labels exist overall (top 40) to see if 'Bad' etc. printed
allL = collections.Counter(v["label"] for d in rooms.values() for v in d["room"].values())
print(allL.most_common(45))

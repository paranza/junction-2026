"""Map 24 strings to 12 intents by keyword, check EN/FI twin agreement, answer distributions, mode baseline,
and which templates are absent per image (selection pattern). Writes wide table to verify/wide.csv."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, collections, os
import pandas as pd
DS = _DATA + ""
OUT = _ROOT + "/eda/cubicasa5k/verify"
KEYS = [("windows", ["windows", "ikkunaa"]), ("floors", ["storeys", "kerrosta"]), ("toilets", ["toilet bowls", "WC-istuinta"]),
        ("sinks", ["sinks and", "tiskiallasta"]), ("shower_bath", ["showers and", "suihkua"]), ("doors", ["doors are", "ovea"]),
        ("saunas", ["saunas", "saunaa"]), ("kitchens", ["kitchens", "keittiötä"]), ("bedrooms", ["bedrooms", "makuuhuonetta"]),
        ("wc_rooms", ["How many separate WC rooms", "Kuinka monta erillistä WC-tilaa"]), ("bathrooms", ["bathrooms or", "kylpy- tai"]), ("balconies", ["balconies", "parveketta"])]
def intent(q):
    hits = [k for k, ws in KEYS if any(w in q for w in ws)]
    assert len(hits) == 1, (q, hits)
    return hits[0]
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
df = pd.DataFrame([r for r in rows if r["path"].startswith("data/cubicasa5k/")])
df["intent"] = df.question.map(intent)
df["lang"] = df.question.map(lambda q: "en" if q.startswith("How") else "fi")
p = df.pivot_table(index=["path", "intent"], columns="lang", values="answer", aggfunc="first")
print("pairs", len(p), "both langs", p.notna().all(axis=1).sum(), "disagree", (p.en != p.fi).sum())
W = p.en.unstack()
W.index = [x.split("/")[-1] for x in W.index]
W["style"] = [x.rsplit("-", 1)[0] for x in W.index]
W.to_csv(os.path.join(OUT, "wide.csv"))
print(W["style"].value_counts())
tot_q = 0; tot_ok = 0
for k, _ in KEYS:
    s = W[k].dropna().astype(int)
    m = s.mode()[0]; ok = (s == m).sum()
    tot_q += len(s) * 2; tot_ok += ok * 2
    print(f"{k:12s} imgs {len(s):3d} min {s.min()} med {s.median()} max {s.max()} mode {m} acc {ok/len(s):.3f}  dist {dict(sorted(collections.Counter(s).items()))}")
print("question-weighted mode baseline", tot_ok / tot_q, tot_q)
# per-style asked rate per template
print((W.groupby("style")[[k for k, _ in KEYS]].count().T / W.style.value_counts()).round(2))

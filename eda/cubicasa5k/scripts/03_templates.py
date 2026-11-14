"""Map question strings to templates, check EN/FI twin agreement, answer distributions."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import os
import pandas as pd

OUT = _ROOT + "/eda/cubicasa5k"
q = pd.read_csv(os.path.join(OUT, "questions_cubicasa5k.csv"))
T = {
 "windows": ("How many windows", "Kuinka monta ikkunaa"),
 "floors": ("How many floors", "Kuinka monta kerrosta"),
 "toilets": ("How many toilet bowls", "Kuinka monta WC-istuinta"),
 "sinks": ("How many sinks", "Kuinka monta pesu- ja tiskiallasta"),
 "shower_bath": ("How many showers", "Kuinka monta suihkua"),
 "doors": ("How many doors", "Kuinka monta ovea"),
 "saunas": ("How many saunas", "Kuinka monta saunaa"),
 "kitchens": ("How many kitchens", "Kuinka monta keittiötä"),
 "bedrooms": ("How many bedrooms", "Kuinka monta makuuhuonetta"),
 "wc_rooms": ("How many separate WC", "Kuinka monta erillistä WC"),
 "bathrooms": ("How many bathrooms", "Kuinka monta kylpy"),
 "balconies": ("How many balconies", "Kuinka monta parveketta"),
}
def tmpl(s):
    for k, (en, fi) in T.items():
        if s.startswith(en): return k, "en"
        if s.startswith(fi): return k, "fi"
    return None, None
q[["template", "lang"]] = q.question.apply(lambda s: pd.Series(tmpl(s)))
assert q.template.notna().all()
q["file"] = q.path.str.split("/").str[-1]
q["prefix"] = q.file.str.replace(r"-\d+\.png$", "", regex=True)
q.to_csv(os.path.join(OUT, "questions_cubicasa5k.csv"), index=False)
# duplicates of (path, question)?
print("duplicate (path,question) rows:", q.duplicated(["path", "question"]).sum())
# twin agreement
p = q.pivot_table(index=["path", "template"], columns="lang", values="answer", aggfunc="first")
print("pairs with both langs:", p.dropna().shape[0], "mismatching:", (p.dropna().en != p.dropna().fi).sum())
print("EN-only:", p.fi.isna().sum(), "FI-only:", p.en.isna().sum())
en = q[q.lang == "en"]
print("\nAnswer distribution per template (EN rows):")
tab = en.groupby("template").answer.agg(["count", "min", "median", "mean", "max"])
tab["zeros"] = en.groupby("template").answer.apply(lambda s: (s == 0).sum())
print(tab.sort_values("count", ascending=False).to_string())
print()
for t in tab.sort_values("count", ascending=False).index:
    print(t, dict(sorted(en[en.template == t].answer.value_counts().items())))
# coverage per image
cov = en.groupby("path").template.apply(lambda s: tuple(sorted(s)))
print("\ntemplates per image:", en.groupby("path").size().value_counts().sort_index().to_dict())
# answer by prefix
print(en.pivot_table(index="template", columns="prefix", values="answer", aggfunc="mean").round(2).to_string())

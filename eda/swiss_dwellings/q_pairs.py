import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
import pandas as pd, re
WD = _ROOT + "/eda/swiss_dwellings"
df = pd.read_csv(f"{WD}/questions_swiss.csv")
# questions in file order: check en followed by local twin with same answer
ok = 0; bad = []
for i in range(0, len(df), 2):
    a, b = df.iloc[i], df.iloc[i+1]
    if a.path == b.path and a.answer == b.answer and a.lang == "en" and b.lang != "en": ok += 1
    else: bad.append((i, a.question[:60], b.question[:60]))
print("pairs ok", ok, "of", len(df)//2, "bad", len(bad), bad[:5])
# per-file local language
df["local"] = None
loc = df[df.lang != "en"].groupby("path").lang.agg(lambda s: ",".join(sorted(set(s))))
print(loc.value_counts())
# families
def fam(q):
    ql = q.lower()
    if "apartment" in ql and "area" in ql: return "area_apartment"
    if "numbered indoor rooms" in ql: return "area_total_indoor"
    if "total net area" in ql and "labelled" in ql: return "area_label_total"
    if "net floor area of room" in ql: return "area_room"
    if "rooms labelled" in ql: return "count_label"
    if "apartments" in ql: return "count_apartments"
    if "doors" in ql: return "count_doors"
    if "windows" in ql: return "count_windows"
    if "toilets" in ql: return "count_wc"
    if "washbasins" in ql: return "count_washbasins"
    if "bathtubs" in ql: return "count_bathtubs"
    if "showers" in ql: return "count_showers"
    return "?"
en = df[df.lang == "en"].copy()
en["family"] = en.question.map(fam)
print(en.family.value_counts())
print(en.groupby("family").answer.describe().to_string())
# labels in count_label and area questions
en["label"] = en.question.str.extract(r"labelled '(.*)' (?:are|on)")[0]
en.loc[en.family=="area_room","label"] = en.question.str.extract(r"\('(.*)'\)")[0]
en["room"] = en.question.str.extract(r"room ([A-Z]?\w*\.\d+)")[0]
en["apt"] = en.question.str.extract(r"apartment ([A-Z]+) in")[0]
print(en[en.family.isin(["count_label"])].label.value_counts().to_string())
print("area_room labels:", en[en.family=="area_room"].label.value_counts().to_string())
print("area_label_total labels:", en[en.family=="area_label_total"].label.value_counts().to_string())
print("apts:", en[en.family=="area_apartment"].apt.value_counts().to_string())
# per file counts of families
print(en.groupby("path").family.value_counts().unstack(fill_value=0).describe().T.to_string())
# answer decimals for area
ar = en[en.family.str.startswith("area")]
dec = ar.answer.astype(str).str.split(".").str[-1].str.len()
print("area decimals:", dec.value_counts().to_dict())
en.to_csv(f"{WD}/questions_en_families.csv", index=False)
# count_label answer dist
print(en[en.family=="count_label"].answer.value_counts().sort_index().to_dict())
print(en[en.family=="count_apartments"].answer.value_counts().sort_index().to_dict())

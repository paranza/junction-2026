import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, re, collections, sys
import pandas as pd
DS = _DATA + ""
WD = _ROOT + "/eda/swiss_dwellings"
rows = [json.loads(l) for l in open(f"{DS}/questions.jsonl")]
df = pd.DataFrame([r for r in rows if r["path"].startswith("data/swiss_dwellings/")])
print("n", len(df), "files", df.path.nunique())
print(df.type.value_counts(), df.unit.value_counts())
print("ext of paths:", df.path.str.rsplit(".", n=1).str[-1].value_counts().to_dict())

# Template normalisation: replace quoted labels, room numbers, apartment letters, numbers
def templ(q):
    t = q
    t = re.sub(r"'[^']*'", "'<L>'", t)
    t = re.sub(r"«[^»]*»", "«<L>»", t)
    t = re.sub(r"\b\d+\.\d+\b", "<R>", t)
    t = re.sub(r"(apartment|appartamento|appartement|Wohnung|l'appartamento|dell'appartamento|de l'appartement) ([A-Z]{1,2})\b", r"\1 <A>", t)
    t = re.sub(r"\b\d+\b", "<N>", t)
    return t
df["templ"] = df.question.map(templ)
# language detection crude
def lang(q):
    if re.search(r"\b(How|What|Which|Is|Are)\b", q): return "en"
    if re.search(r"\b(Wie|Welche|Wieviele|Gibt|Raum|Räume|Geschoss|Grundriss)\b", q): return "de"
    if re.search(r"\b(Combien|Quelle|Quel|pièces|plan|étage)\b", q): return "fr"
    if re.search(r"\b(Quant|Qual|locali|pianta|piano)\b", q): return "it"
    return "?"
df["lang"] = df.question.map(lang)
print(df.lang.value_counts())
pd.set_option("display.width", 250, "display.max_colwidth", 200, "display.max_rows", 200)
tc = df.groupby(["templ", "type", "lang"]).size().reset_index(name="n").sort_values("n", ascending=False)
print(tc.to_string())
df.to_csv(f"{WD}/questions_swiss.csv", index=False)

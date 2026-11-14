"""Questions EDA: counts, templates, families, languages, answers, duplicates, grounding.
Run: python -I analyze.py  (writes CSVs into the work dir, prints summaries)."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
import sys, re, json
sys.path.insert(0, _ROOT + "/eda/questions")
import numpy as np
import pandas as pd
from qlib import load, normalize, WORK
from families import assign

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 120)

df = load()
n = df.question.map(normalize)
df["template"] = n.str[0]
df["slots"] = n.str[1]
df = assign(df)
assert (df.family != "UNMATCHED").all()

# translation twin bookkeeping (verified: every non-English line follows its English twin)
df["is_translation"] = df.lang != "en"
df["twin_line"] = np.where(df.is_translation, df.line - 1, np.nan)
nxt = df.shift(-1)
df["has_translated_twin"] = (df.lang == "en") & (nxt.lang.ne("en")) & (nxt.path == df.path)
df["stem"] = df.path.str.rsplit(".", n=1).str[0]


def numeric(a):
    return isinstance(a, (int, float)) and not isinstance(a, bool)


def decimals(a):
    if isinstance(a, int):
        return 0
    s = repr(float(a))
    if "e" in s:
        return np.nan
    frac = s.split(".")[1]
    return 0 if frac == "0" else len(frac)


df["is_num"] = df.answer.map(numeric)
df["ans_float"] = df.answer.map(lambda a: float(a) if numeric(a) else np.nan)
df["ans_decimals"] = df.answer.map(lambda a: decimals(a) if numeric(a) else np.nan)
df["ans_is_int_type"] = df.answer.map(lambda a: isinstance(a, int))
df["ans_len"] = df.answer.map(lambda a: len(a) if isinstance(a, str) else np.nan)
df["ans_lines"] = df.answer.map(lambda a: a.count("\n") + 1 if isinstance(a, str) else np.nan)

print("=" * 30, "1. BASIC COUNTS")
print("rows", len(df), "distinct files", df.path.nunique(), "distinct question strings", df.question.nunique())
print(pd.crosstab(df.source, df.type, margins=True))
print(pd.crosstab(df.source, df.ext, margins=True))
print(pd.crosstab(df.type, df.unit.fillna("none"), margins=True))
print(pd.crosstab(df.source, df.lang, margins=True))

qpf = df.groupby(["source", "path"]).size().rename("n").reset_index()
qpf_en = df[df.lang == "en"].groupby(["source", "path"]).size().rename("n_en").reset_index()
qpf = qpf.merge(qpf_en, on=["source", "path"], how="left")
qpf.to_csv(WORK + "questions_per_file.csv", index=False)
print("\nquestions per file (all languages, and English only):")
print(qpf.groupby("source").agg(files=("n", "size"), min=("n", "min"), p25=("n", lambda s: s.quantile(.25)), median=("n", "median"),
                                p75=("n", lambda s: s.quantile(.75)), max=("n", "max"), mean=("n", "mean"),
                                en_median=("n_en", "median"), en_max=("n_en", "max")).round(1))
print("overall:", qpf.n.describe().round(1).to_dict())

print("=" * 30, "2. TEMPLATES")
tmpl = (df.groupby(["source", "lang", "template"])
        .agg(n=("line", "size"), n_files=("path", "nunique"), family=("family", "first"), grounding=("grounding", "first"),
             types=("type", lambda s: ",".join(sorted(s.unique()))), units=("unit", lambda s: ",".join(sorted(s.dropna().unique()))),
             example_question=("question", "first"), example_answer=("answer", lambda s: str(s.iloc[0])[:120]),
             ans_min=("ans_float", "min"), ans_median=("ans_float", "median"), ans_max=("ans_float", "max"),
             share_zero=("ans_float", lambda s: (s == 0).mean() if s.notna().any() else np.nan),
             max_decimals=("ans_decimals", "max"))
        .reset_index().sort_values("n", ascending=False))
tmpl.to_csv(WORK + "templates.csv", index=False)
print("distinct templates overall:", len(tmpl), " English-only templates:", (tmpl.lang == "en").sum())
print(tmpl.groupby("source").agg(templates=("n", "size"), en_templates=("lang", lambda s: (s == "en").sum()), questions=("n", "sum")))
top20 = tmpl.head(20)
print("top-20 templates cover", top20.n.sum(), "of", len(df), f"= {top20.n.sum()/len(df):.1%}")
print(top20[["source", "lang", "n", "n_files", "family", "template"]].to_string(index=False))
# coverage by top-k at the family level (language-independent intent)
fam = (df.groupby(["source", "family"])
       .agg(n=("line", "size"), n_en=("lang", lambda s: (s == "en").sum()), n_files=("path", "nunique"),
            langs=("lang", lambda s: ",".join(sorted(s.unique()))), grounding=("grounding", "first"),
            types=("type", lambda s: ",".join(sorted(s.unique()))), units=("unit", lambda s: ",".join(sorted(s.dropna().unique()))),
            n_num=("is_num", "sum"), ans_min=("ans_float", "min"), ans_p50=("ans_float", "median"), ans_p90=("ans_float", lambda s: s.quantile(.9)),
            ans_max=("ans_float", "max"),
            share_zero=("ans_float", lambda s: (s == 0).mean() if s.notna().any() else np.nan),
            share_int_valued=("ans_float", lambda s: (s.dropna() == s.dropna().round()).mean() if s.notna().any() else np.nan),
            share_int_type=("ans_is_int_type", "mean"),
            decimals_dist=("ans_decimals", lambda s: json.dumps({int(k): int(v) for k, v in s.dropna().value_counts().sort_index().items()})),
            text_len_median=("ans_len", "median"), text_lines_median=("ans_lines", "median"))
       .reset_index().sort_values("n", ascending=False))
fam.to_csv(WORK + "families.csv", index=False)
print("\ndistinct families (cross-language intents):", len(fam))
print(fam.groupby("source").agg(families=("n", "size"), questions=("n", "sum")))
cov = fam.n.cumsum() / len(df)
print("top-20 families cover", f"{cov.iloc[19]:.1%}", "; top-10:", f"{cov.iloc[9]:.1%}")
en = df[df.lang == "en"]
en_t = en.groupby(["source", "template"]).size().sort_values(ascending=False)
print("English-only view: distinct EN templates", len(en_t), "top-20 cover", f"{en_t.head(20).sum()/len(en):.1%}", "of", len(en), "English questions")

print("=" * 30, "3. LANGUAGES AND TRANSLATION PAIRS")
print(pd.crosstab(df.source, df.lang, margins=True))
twins = df[df.lang == "en"].groupby("source").has_translated_twin.agg(["sum", "size", "mean"]).round(3)
print("English questions with a translated twin:\n", twins)
print("overall:", df[df.lang == "en"].has_translated_twin.sum(), "/", (df.lang == "en").sum())
# language of twin per file: one local language per file?
loc = df[df.lang != "en"].groupby("path").lang.nunique()
print("files with >1 non-English language:", (loc > 1).sum(), "of", len(loc))
print(df[df.lang != "en"].groupby(["source", "lang"]).path.nunique().rename("files"))

print("=" * 30, "4. ANSWERS")
print("answer python types by question type:\n", pd.crosstab(df.type, df.answer.map(lambda a: type(a).__name__)))
for t in ["count", "area", "length", "volume"]:
    s = df[df.type == t]
    print(f"{t}: n={len(s)} min={s.ans_float.min()} median={s.ans_float.median()} max={s.ans_float.max()} zero={(s.ans_float==0).mean():.3f}",
          "decimals:", s.ans_decimals.value_counts().sort_index().to_dict(), "int-type:", s.ans_is_int_type.mean().round(3))
cnt = df[df.type == "count"]
print("count answers non-integer:", (cnt.ans_float != cnt.ans_float.round()).sum())
# per family numeric stats (English only to avoid double-counting translations)
num_fam = (df[(df.lang == "en") & df.is_num].groupby(["source", "family"])
           .agg(n=("line", "size"), mn=("ans_float", "min"), p50=("ans_float", "median"), mx=("ans_float", "max"),
                zero=("ans_float", lambda s: round((s == 0).mean(), 3)),
                dec=("ans_decimals", lambda s: s.value_counts().sort_index().to_dict()))
           .reset_index())
print(num_fam.to_string(index=False))
num_fam.to_csv(WORK + "numeric_answers_by_family_en.csv", index=False)
# text answers
txt = df[df.type == "text"]
print("\ntext answers: n", len(txt), "chars median", txt.ans_len.median(), "p90", txt.ans_len.quantile(.9), "max", txt.ans_len.max(),
      "multi-line share", (txt.ans_lines > 1).mean().round(3))
print(txt.groupby("source").agg(n=("line", "size"), chars_min=("ans_len", "min"), chars_med=("ans_len", "median"), chars_max=("ans_len", "max"),
                                lines_med=("ans_lines", "median"), multiline=("ans_lines", lambda s: (s > 1).mean())))
NEG = re.compile(r"\b(no |not (available|found|present|provided|specified|included|defined)|none|cannot|can't|unavailable|does not|doesn't|n/a|unknown|missing|no data|not possible|lacks|absent)", re.I)
txt_neg = txt[txt.answer.map(lambda a: bool(NEG.search(a)))]
print("text answers containing a negative/not-available phrase:", len(txt_neg), "of", len(txt))
LEAD_NEG = re.compile(r"^\s*(no\b|none\b|not\b|this (model|information)|the (model|ifc).*(does not|doesn't|no )|[^\n]{0,80}(not available|no \w+ (were |was )?found|not found|not (provided|specified|included|defined|present)))", re.I)
txt_mainly_neg = txt[txt.answer.map(lambda a: bool(LEAD_NEG.search(a)) and len(a) < 400)]
print("short text answers that state the information is absent:", len(txt_mainly_neg))
for a, q in zip(txt_mainly_neg.answer, txt_mainly_neg.question):
    print("   Q:", q[:90], "\n      A:", a[:160].replace("\n", " | "))
df.loc[txt_mainly_neg.index, "answer_absent"] = True
df["answer_absent"] = df.get("answer_absent", False)
df["answer_absent"] = df["answer_absent"].fillna(False).astype(bool)

# units vs question wording
print("\nunit vs explicit unit word in question:")
def unit_in_q(q):
    if re.search(r"m²|m2\b", q): return "m2"
    if re.search(r"m³|m3\b", q): return "m3"
    if re.search(r"\bmetres\b|\bmeter\b|\bMetern\b|\bmeters\b", q): return "m"
    if re.search(r"\bsq ?ft|square feet|\bSF\b|ft²", q): return "ft2"
    return "none"
df["unit_in_question"] = df.question.map(unit_in_q)
print(pd.crosstab(df.unit.fillna("none"), df.unit_in_question))

print("=" * 30, "5. DUPLICATES AND CONTRADICTIONS")
key = df.groupby(["path", "question"])
dup = key.filter(lambda g: len(g) > 1)
print("rows sharing (path, question) with another row:", len(dup))
contra = key.answer.agg(lambda s: s.astype(str).nunique()).rename("n_answers")
print("(path,question) groups with >1 distinct answer:", (contra > 1).sum())
# same question text across different files (ifc_bench paraphrase reuse)
same_q_multi_files = df.groupby("question").path.nunique()
print("question strings used on >1 file:", (same_q_multi_files > 1).sum(), "of", len(same_q_multi_files))
# translation twins: answer agreement is by construction of the pairing; check type/unit agreement
prev = df.shift(1)
tw = df.lang != "en"
print("twins with same type and unit:", ((prev.type[tw] == df.type[tw]) & (prev.unit[tw].fillna("") == df.unit[tw].fillna(""))).sum(), "/", tw.sum())

# cross-format: same question template + slots on files of the same model / drawing
def model_key(p):
    name = p.split("/")[-1].rsplit(".", 1)[0]
    if "/ifc_models/" in p:
        return re.sub(r"_plan-\d+-.*$", "", name)
    return name
df["model_key"] = df.path.map(model_key)
x = df[df.source == "ifc_models"].copy()
x["fmt"] = x.ext
grp = x.groupby(["model_key", "question"]).agg(n_fmt=("fmt", "nunique"), fmts=("fmt", lambda s: ",".join(sorted(s.unique()))),
                                                 answers=("answer", lambda s: sorted(set(map(str, s)))))
cross = grp[grp.n_fmt > 1]
print("ifc_models: identical questions asked on both the PDF floor plan and the IFC model:", len(cross),
      " with disagreeing answers:", (cross.answers.map(len) > 1).sum())
pdfq = x[x.ext == "pdf"]
print("ifc_models PDF questions:", len(pdfq), "by family:")
print(pdfq.groupby(["path", "family"]).size().to_string())

print("=" * 30, "6. GROUNDING")
print(pd.crosstab(df.source, df.grounding, margins=True))
print("share needing a named entity/label/sheet located:",
      round(df.grounding.isin(["named_label_set", "named_room", "named_apartment", "table_filter", "table_row", "plan_detail", "named_entity_report", "level", "level_report"]).mean(), 3))

df.drop(columns=["slots"]).assign(slots=df.slots.map(lambda s: " | ".join(s))).to_csv(WORK + "questions_annotated.csv", index=False)
print("wrote questions_annotated.csv, templates.csv, families.csv, questions_per_file.csv, numeric_answers_by_family_en.csv")

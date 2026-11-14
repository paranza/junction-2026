"""Rule-based classification of the 249 ifc_bench questions + answer-format stats.
Usage: python -I classify.py <work_dir>   (reads ifc_bench_questions.jsonl, writes questions_classified.csv, category_stats.csv)"""
import sys, os, re, json, collections
import pandas as pd

W = sys.argv[1]
rows = [json.loads(l) for l in open(os.path.join(W, "ifc_bench_questions.jsonl"))]

# first matching rule wins; order matters (specific before generic). Patterns are matched on the lowercased question.
RULES = [
    ("element_lookup", r"\bguid\b|1hosvn6df7f8|room a203|room 01\.014|staff room|open-plan office on the ground|stair in house a"),
    ("takeoff_estimate", r"skirting|painting|tiles|tiling|flooring are required|facade's total surface|surface area of the fa|glazed windows|volume of insulation|concrete required for the foundation|doorknob"),
    ("performance_lifecycle", r"thermal|air tightness|solar heat|lifespan|warranty|embodied carbon|recyclab|energy efficiency|maintenance|live load|vapor barrier|glazing is used"),
    ("fire_safety_access", r"fire|emergency|escape|accessib|outdoor space"),
    ("spaces_areas", r"toilet|bathroom|bedroom"),  # reference answers count WC/bath rooms (IfcSpace), not fixtures
    ("mep", r"\bmep\b|pipe|piping|heating|cooling|electrical|lighting|voltage|sanitary"),
    ("metadata", r"software|ifc standard|modeling standards|project information|type of building|building's type|where is it situated"),
    ("materials", r"material|insulation|layers"),
    ("lengths_volumes", r"length|volume"),
    ("structural_interpretation", r"structural|load-bearing|load bearing|load path|foundation|roof structure|steel beams|spans|beams are used|beams? (is|are) used"),
    ("inventory_counts", r"quantit|how many|count|distribution|percentage|which .*types|what .*types|kinds of|furniture|coverings|railing|which walls are used|what walls are used|names of all the rooms"),
    ("element_dimensions", r"width|widest|narrowest|thickness|sizes|dimensions|height of each window"),
    ("levels_heights", r"height|elevation|floor-to-floor|tallest|lowest"),
    ("spaces_areas", r"space|room|floor area|footprint|gross area|area of each floor|office|restroom|parking|lot"),
]

def classify(q):
    s = q.lower()
    for cat, pat in RULES:
        if re.search(pat, s):
            # space-type questions that ask for counts stay in spaces_areas
            if cat == "inventory_counts" and re.search(r"space|room|floor area|office|parking|lot|restroom", s) and not re.search(r"door|window|wall|furniture|stair|column|beam|slab", s):
                return "spaces_areas"
            return cat
    return "other"

INTERP = re.compile(r"most probably|probably|likely|estimat|approximately|around|typical|potential|assum|inferred|could serve|may indicate|would usually|would normally|in practice|rough|should be determined|based on the geometry|appears to be", re.I)
NEG = re.compile(r"\bno\b[^.\n]{0,60}\b(found|available|present|elements|information)\b|not available|not found|cannot be determined|not directly available|not provided|not defined|not specified|is empty|: 0 elements|not explicitly|coverings: 0|not include", re.I)
GUID = re.compile(r"\b[0-9A-Za-z_$]{22}\b")

out = []
for i, r in enumerate(rows):
    a = r["answer"]
    cat = classify(r["question"])
    nums = re.findall(r"\d+(?:\.\d+)?", a)
    out.append({
        "idx": i, "model": r["path"].split("/")[-1].replace(".ifc", ""), "category": cat,
        "question": r["question"], "answer_chars": len(a), "answer_lines": a.count("\n") + 1,
        "n_numbers": len(nums), "has_pct": "%" in a, "has_list": bool(re.search(r"^\s*(-|\d+\.|•|\*)\s", a, re.M)),
        "interpretive": bool(INTERP.search(a)), "negative": bool(NEG.search(a)),
        "fully_negative": bool(NEG.search(a)) and len(nums) <= 1 and len(a) < 200,
        "has_guid": bool(GUID.search(a)),
        "has_unit_sqm": bool(re.search(r"sq ?m|sqm|m²|square met", a)),
        "answer": a,
    })
df = pd.DataFrame(out)
# answer style: one label per answer
EXTERNAL = re.compile(r"industry standard|generally between|typically|typical |standard german|likely used|would normally|in practice", re.I)
def style(r):
    if r.negative and r.interpretive and r.n_numbers >= 1:
        return "not_available_plus_estimate"
    if r.negative and (r.fully_negative or r.n_numbers == 0):
        return "not_available"
    if r.interpretive:
        return "interpretive"
    return "factual_list" if r.has_list else "factual_short"
df["answer_style"] = df.apply(style, axis=1)
df["uses_external_knowledge"] = df.answer.str.contains(EXTERNAL)
df["template_family"] = df.model.map({"ac20_arc": "T1 (ac20/hitos)", "hitos_arc": "T1 (ac20/hitos)", "digital_hub_arc": "T2 (dh/fantasy)",
                                      "fantasy_office_building_3_arc": "T2 (dh/fantasy)", "duplex_arc": "T3 (duplex prose)"})
df.to_csv(os.path.join(W, "questions_classified.csv"), index=False)
g = df.groupby("category").agg(n=("idx", "size"), models=("model", lambda s: s.nunique()),
                                med_chars=("answer_chars", "median"), max_chars=("answer_chars", "max"),
                                med_lines=("answer_lines", "median"), med_numbers=("n_numbers", "median"),
                                pct_list=("has_list", "mean"), pct_pct=("has_pct", "mean"),
                                n_interp=("interpretive", "sum"), n_neg=("negative", "sum"), n_fully_neg=("fully_negative", "sum"))
g = g.sort_values("n", ascending=False)
g.to_csv(os.path.join(W, "category_stats.csv"))
pd.set_option("display.width", 250)
print(g.round(2).to_string())
print("total", len(df), "interpretive", df.interpretive.sum(), "negative", df.negative.sum(), "fully_negative", df.fully_negative.sum())
print(pd.crosstab(df.category, df.model))
print(pd.crosstab(df.category, df.answer_style, margins=True))
print(pd.crosstab(df.model, df.answer_style, margins=True))
print("external-knowledge answers:", int(df.uses_external_knowledge.sum()))
print("answer chars: median", df.answer_chars.median(), "p90", df.answer_chars.quantile(0.9), "max", df.answer_chars.max())
print(df.groupby("model").answer_chars.median())

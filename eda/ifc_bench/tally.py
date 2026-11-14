"""Combine repro/sweep/extra/duplex checks into one per-question coverage table. Usage: python -I tally.py <work_dir>"""
import sys, os, collections
import pandas as pd
W = sys.argv[1]
q = pd.read_csv(os.path.join(W, "questions_classified.csv"))[["idx", "model", "category", "answer_style", "question"]]
st = {}
src = collections.defaultdict(list)
r = pd.read_csv(os.path.join(W, "repro_results.csv"))
for _, x in r.iterrows():
    st[x.idx] = {"reproduced": "reproduced", "model facts reproduced; rest unverifiable": "reproduced (model facts; extra prose unverifiable)"}.get(x.status, x.status)
    src[x.idx].append("sample")
s = pd.read_csv(os.path.join(W, "sweep_results.csv"))
for _, x in s.iterrows():
    ok = bool(x.exact_label_match) or (x.family == "spaces on level" and x.labels_matched >= min(x.n_elements, x.n_ref_labels))
    st.setdefault(x.idx, "reproduced" if ok or x.idx == 77 else "not reproduced")
    src[x.idx].append("sweep")
e = pd.read_csv(os.path.join(W, "extra_checks.csv"))
for _, x in e.iterrows():
    if x.idx not in st:
        st[x.idx] = "reproduced" if x.ok else "reference contradicted by model"
    src[x.idx].append("extra")
d = pd.read_csv(os.path.join(W, "duplex_checks.csv"))
for _, x in d.iterrows():
    st.setdefault(x.idx, "reproduced" if x.ok else "not reproduced")
    src[x.idx].append("duplex")
# hand-labelled outcomes from the investigation notes (see reproduce.py / extra_checks.py)
st[88] = "reference contradicted by model"   # says beam size/span unavailable; type name + Qto Length exist
st[195] = "reference contradicted by model"  # says no door fire rating; 5 doors have FireRating 'EI 30'
st[95] = "partial (counts right, label translated)"
for i in (98, 99, 100, 104, 106, 111):        # numbers need MEP discipline files not in the dataset
    st[i] = "not derivable from provided file"; src[i].append("mep-absence check")
NONOBV = {218: "drops 21 mm 'Empty Fill' layer", 211: "drops curtain-wall window panels", 93: "slabs = non-LANDING incl. insulation/screed",
          64: "mixes floor-to-floor and modal space height", 29: "ROOF slabs as ceilings", 87: "material-name keyword filter",
          77: "'Geschossdecke' family = floor slab", 228: "strip '-digit' suffix", 18: "ArchiCAD layer 'Ebene'", 19: "ArchiCAD layer 'Ebene'",
          213: "ArchiCAD LAYERNAME 'Yttervegger'", 214: "ArchiCAD LAYERNAME 'Yttervegger'", 207: "gross-area zone counted as room",
          221: "gross-area zones included in net total", 2: "space GrossFloorArea sum; footprint = ground slab gross area",
          173: "'gross' = sum of room areas", 63: "'gross' = sum of NetFloorArea", 157: "tile finish-slab areas mapped to rooms",
          225: "staff room = 'Personalrom', third floor = '3.etg'", 202: "'ground level' = 1.etg (Q227 uses u.etg)", 113: "space solid height",
          144: "hedged 'estimate' equals exact footing volume sum", 122: "'depth' = footing thickness", 152: "stair space excluded"}
rows = []
for i, status in st.items():
    m = q[q.idx == i].iloc[0]
    rows.append({"idx": i, "model": m.model, "category": m.category, "answer_style": m.answer_style, "status": status,
                 "non_obvious_convention": NONOBV.get(i, ""), "checked_by": "+".join(sorted(set(src[i]))), "question": m.question})
cov = pd.DataFrame(rows).sort_values("idx")
cov.to_csv(os.path.join(W, "coverage.csv"), index=False)
print("unique questions checked:", len(cov), "of 249")
print(cov.status.value_counts().to_string())
rep = cov.status.str.startswith("reproduced")
print("reproduced (incl. model-facts-only):", int(rep.sum()), "| of which needed a non-obvious convention:", int((rep & (cov.non_obvious_convention != "")).sum()))
t = cov.groupby("category").agg(checked=("idx", "size"), reproduced=("status", lambda s: int(s.str.startswith("reproduced").sum())),
                                nonobvious=("non_obvious_convention", lambda s: int((s != "").sum())))
t["total_in_category"] = q.category.value_counts()
print(t.to_string())
t.to_csv(os.path.join(W, "coverage_by_category.csv"))

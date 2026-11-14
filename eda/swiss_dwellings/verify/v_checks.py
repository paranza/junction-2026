# Second-pass checks on my independent PDF model (all 65 files): printed areas, net vs raw under the 2% rule,
# fill categories, duplicate room numbers, zero-count questions, rotated text.
import sys, os, collections, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_pdf, v_parse, v_local, v_eval
import pymupdf

stems = v_local.stems("pdf")
qs = [q for q in v_parse.load() if q["lang"] == "en"]
M = {s: v_eval.model(s) for s in stems}
C = collections.Counter()

# 1. printed areas vs computed
worst_raw = []
for s, m in M.items():
    pr = [r for r in m["rooms"] if r["printed"] is not None]
    if pr: C["files_with_printed"] += 1
    for r in pr:
        C["printed_rooms"] += 1
        C["printed==round(net)"] += round(r["net"], 2) == r["printed"]
        C["printed==round(raw)"] += round(r["raw"], 2) == r["printed"]
        rel = abs(r["raw"] - r["printed"]) / r["printed"]
        C["raw_off_by_gt_2pct"] += rel > 0.02
        worst_raw.append((rel, r["raw"] - r["printed"], s, r["num"], r["label"]))
    C["rooms_total"] += len(m["rooms"])
    C["rooms_unlabelled"] += sum(r["label"] is None for r in m["rooms"])
    C["unlabelled_with_printed"] += sum(r["label"] is None and r["printed"] is not None for r in m["rooms"])
    nums = collections.Counter(r["num"] for r in m["rooms"])
    C["files_with_duplicate_room_numbers"] += any(v > 1 for v in nums.values())
    C["rooms_without_polygon"] += sum(r["poly"] is None for r in m["rooms"])
worst_raw.sort(reverse=True)
print({k: v for k, v in C.items()})
print("worst raw vs printed:", [(round(a, 4), round(b, 2), s[:22], n, l) for a, b, s, n, l in worst_raw[:6]])

# 2. area exactness vs gold (English; twins carry identical answers)
ex = collections.Counter(); maxrel = collections.defaultdict(float); rawrel = collections.defaultdict(float)
for q in qs:
    if q["type"] != "area": continue
    P = v_eval.predict(q["fam"], q["param"], M[q["stem"]])
    netk = {"area_room": "net", "area_label_total": "net", "area_apartment": "net_excl_outdoor_fill", "area_total_indoor": "all_but_outdoor_fill"}[q["fam"]]
    rawk = {"area_room": "raw", "area_label_total": "raw", "area_apartment": "raw_excl_outdoor_fill", "area_total_indoor": "raw_all_but_outdoor"}[q["fam"]]
    ex[(q["fam"], "net==gold_2dp")] += abs(P[netk] - q["ans"]) < 0.005
    ex[(q["fam"], "n")] += 1
    ex[(q["fam"], "raw!=net")] += abs(P[rawk] - P[netk]) >= 0.005
    maxrel[q["fam"]] = max(maxrel[q["fam"]], abs(P[netk] - q["ans"]) / q["ans"])
    rawrel[q["fam"]] = max(rawrel[q["fam"]], abs(P[rawk] - q["ans"]) / q["ans"])
for k in sorted(ex): print(k, ex[k])
print("max rel err net:", {k: round(v, 6) for k, v in maxrel.items()})
print("max rel err raw:", {k: round(v, 5) for k, v in rawrel.items()})

# 3. fill categories
fills = collections.Counter(); lab_by_fill = collections.defaultdict(collections.Counter); common_unit = collections.Counter()
for s, m in M.items():
    for r in m["rooms"]:
        f = v_eval.FILL.get(r["fill"], r["fill"])
        fills[f] += 1
        lab_by_fill[f][r["label"]] += 1
        if f == "common": common_unit[("common", r["unit"] is None)] += 1
        if f == "room": common_unit[("room", r["unit"] is None)] += 1
        if r["label"] in v_eval.OUT_LABELS: common_unit[("outdoor_label_fill", f)] += 1
print("room fills", fills)
print("common/room vs unit None", common_unit)
print("unlabelled by fill", {f: c[None] for f, c in lab_by_fill.items()})
print("outdoor-fill labels", lab_by_fill["outdoor"].most_common(12))

# 4. zero-count questions: bathtubs/showers on floors without that question
asked = collections.defaultdict(set)
for q in qs: asked[q["stem"]].add(q["fam"])
for fam, k in [("count_bathtubs", "bathtub"), ("count_showers", "shower"), ("count_wc", "wc"), ("count_washbasins", "washbasin")]:
    no_q = [s for s in stems if fam not in asked[s]]
    print(fam, "floors without question", len(no_q), "their model counts", collections.Counter(M[s]["fxc"].get(k, 0) for s in no_q))

# 5. text direction (rotated labels) and label/number association sanity
rot = collections.Counter()
for s in stems:
    pg = pymupdf.open(f"{v_pdf.D}/{s}.pdf")[0]
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            rot[tuple(round(v, 2) for v in l["dir"])] += 1
print("text line directions", rot.most_common(5))

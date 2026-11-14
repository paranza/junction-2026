"""Extra family checks beyond the stratified sample: negative answers (fire rating, MEP, load-bearing),
storey elevations, largest room, area totals. Prints k/n per family and writes extra_checks.csv.
Usage: python -I extra_checks.py <dataset_dir> <work_dir>"""
import sys, os, re, json, collections, csv
import ifcopenshell
import ifcopenshell.util.element as E

DS, W = sys.argv[1], sys.argv[2]
ROWS = [json.loads(l) for l in open(os.path.join(W, "ifc_bench_questions.jsonl"))]
_M = {}
M = lambda n: _M.setdefault(n, ifcopenshell.open(os.path.join(DS, "data", "ifc_bench", n + ".ifc")))
P = E.get_psets


def storey(e):
    c = E.get_container(e) or E.get_aggregate(e)
    while c is not None and not c.is_a("IfcBuildingStorey"):
        c = E.get_aggregate(c) or E.get_container(c)
    return c


def placeholder(name, v):
    return v is None or (isinstance(v, str) and v.strip().lower().replace(" ", "") in ("", name.lower().replace(" ", "")))


def real_fire_values(f, cls):
    out = []
    for e in f.by_type(cls):
        for el in [e]:  # get_psets(e) already merges the type's psets; checking the type too double-counts
            if el is None:
                continue
            for pn, ps in P(el).items():
                for k, v in ps.items():
                    if re.search(r"fire|feuer|brand|brann", k, re.I) and not placeholder(k, v) and k != "id":
                        out.append((pn, k, v))
    return out


res = []


def rec(fam, i, ok, detail):
    res.append({"family": fam, "idx": i, "model": ROWS[i]["path"].split("/")[-1], "question": ROWS[i]["question"], "ok": ok, "detail": detail})


# fire rating negatives: doors 37 82 195 234 ; windows 38 83 196 235
for i, cls in [(37, "IfcDoor"), (82, "IfcDoor"), (195, "IfcDoor"), (234, "IfcDoor"), (38, "IfcWindow"), (83, "IfcWindow"), (196, "IfcWindow"), (235, "IfcWindow")]:
    f = M(ROWS[i]["path"].split("/")[-1][:-4])
    vals = real_fire_values(f, cls)
    rec("fire rating absent", i, len(vals) == 0, f"{len(vals)} real fire-rating values; sample {collections.Counter(map(str, vals)).most_common(3)}")

# MEP negatives
MEPQ = {31: "sanitary", 45: "any", 46: "pipe", 47: "heating", 242: "pipe", 243: "pipe", 246: "heating", 247: "cooling", 248: "electrical", 108: "lighting"}
for i, kind in MEPQ.items():
    f = M(ROWS[i]["path"].split("/")[-1][:-4])
    els = f.by_type("IfcDistributionElement")
    if kind == "sanitary":
        n = len([e for e in els if "sanitary" in str(E.get_type(e).is_a() if E.get_type(e) else "").lower()])
    elif kind == "any":
        n = len(els)
    elif kind == "pipe":
        n = len([e for e in els if re.search(r"pipe|rør", e.is_a() + str(e.Name), re.I) or e.is_a() in ("IfcFlowSegment", "IfcFlowFitting")])
    elif kind == "lighting":
        n = len([e for e in f.by_type("IfcProduct") if re.search(r"light|leuchte|lampe|belysning", str(e.Name) + str(e.ObjectType), re.I)])
    else:
        pat = {"heating": r"heat|heiz|radiat|boiler|varme", "cooling": r"cool|chill|kjøl|kühl", "electrical": r"electr|elektr|outlet|switch|panel|steckdose"}[kind]
        n = len([e for e in els if re.search(pat, e.is_a() + str(e.Name) + str(e.ObjectType), re.I)])
    rec("MEP absent", i, n == 0, f"{kind}: {n} matching elements (distribution elements in file: {len(els)})")

# load-bearing: 24 ac20 'not available'; 70 dh '0 of 178'; 219 hitos 'not available'
f = M("ac20_arc")
v = collections.Counter(P(w)["ArchiCADProperties"].get("Tragende Funktion") for w in f.by_type("IfcWall"))
rec("load-bearing", 24, set(v) == {"Nicht definiert"}, f"ArchiCAD 'Tragende Funktion' values {dict(v)}; no Pset_WallCommon")
f = M("digital_hub_arc")
v = collections.Counter(P(w)["Pset_WallCommon"].get("LoadBearing") for w in f.by_type("IfcWall"))
rec("load-bearing", 70, v == collections.Counter({False: 178}), f"LoadBearing flags {dict(v)} (incl. reinforced-concrete 'STB' walls flagged False)")
f = M("hitos_arc")
has = sum(1 for w in f.by_type("IfcWall") for ps in P(w).values() for k in ps if re.search(r"load|bær", k, re.I))
rec("load-bearing", 219, has == 0, f"{has} load-bearing properties on walls (material name 'Betong bærende' = load-bearing concrete exists though)")

# storey elevations
for i, model in [(9, "ac20_arc"), (172, "fantasy_office_building_3_arc"), (206, "hitos_arc"), (118, "duplex_arc")]:
    f = M(model)
    sc = 0.001 if model == "hitos_arc" else 1.0
    a = ROWS[i]["answer"]
    ok = True
    det = []
    for s in f.by_type("IfcBuildingStorey"):
        m = re.search(re.escape(s.Name) + r":\s*\n?\s*(?:Elevation: )?(-?[\d.]+)", a)
        if m:
            got = round(s.Elevation * sc, 2)
            ok &= abs(got - float(m.group(1))) < 0.051
            det.append(f"{s.Name}:{m.group(1)}/{got}")
    rec("storey elevation", i, ok and bool(det), "; ".join(det) or "parsed via level-to-level difference")

# largest room
for i, model, area in [(10, "ac20_arc", lambda s: P(s)["BaseQuantities"]["NetFloorArea"]),
                       (55, "digital_hub_arc", lambda s: P(s)["Qto_SpaceBaseQuantities"]["NetFloorArea"]),
                       (207, "hitos_arc", lambda s: [v for k, v in P(s).items() if isinstance(v, dict) and "NetFootprintArea" in v][0]["NetFootprintArea"])]:
    f = M(model)
    sp = f.by_type("IfcSpace")
    big = max(sp, key=area)
    real = max([s for s in sp if "brutto" not in (s.LongName or "").lower()], key=area)
    a = ROWS[i]["answer"]
    ok = (big.Name in a or (big.LongName or "") in a) and f"{area(big):.1f}" in a
    rec("largest room", i, ok, f"max IfcSpace {big.Name} {big.LongName} {area(big):.1f}; largest excluding gross-area zones {real.Name} {real.LongName} {area(real):.1f}")

# totals
f = M("ac20_arc")
sp = f.by_type("IfcSpace")
rec("area totals", 27, abs(sum(P(s)["BaseQuantities"]["NetFloorArea"] for s in sp) - 1939.4) < 0.05 and abs(P(f.by_type("IfcBuilding")[0])["BaseQuantities"]["GrossFloorArea"] - 2727.0) < 0.05,
    "net = sum space NetFloorArea 1939.38; gross = IfcBuilding BaseQuantities.GrossFloorArea 2727.04")
rec("area totals", 2, abs(sum(P(s)["BaseQuantities"]["GrossFloorArea"] for s in sp) - 2266.7) < 0.05,
    "Q2 'Total Floor Area 2266.7' = sum of space GrossFloorArea (2266.66); footprint 537 = GrossArea of ground-floor slab Decke-001")
f = M("hitos_arc")
A = lambda s: [v for k, v in P(s).items() if isinstance(v, dict) and "NetFootprintArea" in v][0]["NetFootprintArea"]
tot = sum(A(s) for s in f.by_type("IfcSpace"))
brut = sum(A(s) for s in f.by_type("IfcSpace") if "brutto" in (s.LongName or "").lower())
rec("area totals", 221, abs(tot - 8491.3) < 0.05, f"sum all IfcSpace NetFootprintArea {tot:.1f} INCLUDING {brut:.1f} of 'Bruttoareal' gross-area zones (double count); rooms only {tot - brut:.1f}")
f = M("digital_hub_arc")
tot = sum(P(s)["Qto_SpaceBaseQuantities"]["NetFloorArea"] for s in f.by_type("IfcSpace"))
rec("area totals", 63, abs(tot - 2842.1) < 0.05, f"'gross floor area' 2842.1 = sum of space NetFloorArea {tot:.2f} (Net=Gross in this export)")
f = M("fantasy_office_building_3_arc")
tot = sum(P(s)["PSet_Room"]["Area"] for s in f.by_type("IfcSpace"))
rec("area totals", 173, abs(tot - 1613.73) < 0.005, f"'total gross area' 1613.73 = sum of PSet_Room.Area {tot:.2f} (room areas, not gross)")

with open(os.path.join(W, "extra_checks.csv"), "w", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(res[0].keys()))
    wr.writeheader(); wr.writerows(res)
fam = collections.defaultdict(lambda: [0, 0])
for r in res:
    fam[r["family"]][0] += r["ok"]; fam[r["family"]][1] += 1
    print(f"[{r['idx']:3d}] {r['family']:18s} {'OK ' if r['ok'] else 'NO '} {r['model'][:12]:12s} {r['detail'][:170]}")
print({k: f"{v[0]}/{v[1]}" for k, v in fam.items()})

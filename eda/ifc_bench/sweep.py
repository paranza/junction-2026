"""Family sweep: for every templated 'types with quantities' and 'spaces per level' question across all 5 models,
test which label source / area source reproduces the reference exactly.
Usage: python -I sweep.py <dataset_dir> <work_dir>  -> sweep_results.csv"""
import sys, os, re, json, collections
import ifcopenshell
import ifcopenshell.util.element as E

DS, W = sys.argv[1], sys.argv[2]
ROWS = [json.loads(l) for l in open(os.path.join(W, "ifc_bench_questions.jsonl"))]
_M = {}


def M(n):
    if n not in _M:
        _M[n] = ifcopenshell.open(os.path.join(DS, "data", "ifc_bench", n + ".ifc"))
    return _M[n]


def P(e):
    return E.get_psets(e)


def storey(e):
    c = E.get_container(e) or E.get_aggregate(e)
    while c is not None and not c.is_a("IfcBuildingStorey"):
        c = E.get_aggregate(c) or E.get_container(c)
    return c


def strip_id(s):
    return re.sub(r":\d+$", "", s) if s else s


def labels(e):
    t = E.get_type(e)
    tn = t.Name if t else None
    return {
        "type.Name": tn,
        "type family (before ':')": tn.split(":")[0] if tn else None,
        "element.Name": e.Name,
        "element.Name minus ':id'": strip_id(e.Name),
        "element.Name before ':'": e.Name.split(":")[0] if e.Name else None,
        "element.Name minus '-digit' suffix": re.sub(r"-\d+$", "", e.Name) if e.Name else None,
        "element.ObjectType": e.ObjectType,
        "ObjectType minus ':id'": strip_id(e.ObjectType),
    }


def ext_flag(model, w):
    ps = P(w)
    if model == "ac20_arc":
        return ps["ArchiCADProperties"]["Ebene"] == "Außenwände"
    if model == "hitos_arc":
        lay = ps["Graphisoft AC110 WALL"]["WALL"]["properties"]["LAYERNAME"] if "Graphisoft AC110 WALL" in ps else \
            ps["Graphisoft AC110 OBJECT"]["OBJECT"]["properties"]["LAYERNAME"]
        return "Yttervegger" in lay
    return bool(ps.get("Pset_WallCommon", {}).get("IsExternal"))


UNIT = r"(?:doors?|windows?|walls?|columns?|beams?|railings?|stairs?|items?|elements|members|slabs?|door\(s\)|window\(s\)|wall\(s\)|column\(s\)|railing\(s\)|stair\(s\)|item\(s\)|slab\(s\)|element\(s\))"


def parse_counts(a):
    out = {}
    for m in re.finditer(r"^\s*-\s*(.+?):\s*(\d+)\s+" + UNIT + r"(?![A-Za-z])", a, re.M):
        out[m.group(1).strip()] = int(m.group(2))
    return out


# idx: (classes, filter) ; filter in {None, 'ext', 'int'}
TYPE_FAMILIES = {
    # doors
    11: ("IfcDoor", None), 58: ("IfcDoor", None), 180: ("IfcDoor", None), 208: ("IfcDoor", None),
    # windows
    14: ("IfcWindow", None), 59: ("IfcWindow", None), 181: ("IfcWindow", None), 210: ("IfcWindow", None),
    # walls all / ext / int
    17: ("IfcWall", None), 60: ("IfcWall", None), 182: ("IfcWall", None), 212: ("IfcWall", None),
    18: ("IfcWall", "ext"), 61: ("IfcWall", "ext"), 183: ("IfcWall", "ext"), 213: ("IfcWall", "ext"),
    19: ("IfcWall", "int"), 62: ("IfcWall", "int"), 184: ("IfcWall", "int"), 214: ("IfcWall", "int"),
    # columns, beams, members, railings, stairs, coverings, curtain walls, furniture
    41: ("IfcColumn", None), 86: ("IfcColumn", None), 197: ("IfcColumn", None), 238: ("IfcColumn", None),
    85: ("IfcBeam", None), 237: ("IfcBeam", None),
    35: ("IfcRailing", None), 79: ("IfcRailing", None), 230: ("IfcRailing", None),
    33: ("IfcStair", None), 228: ("IfcStair", None),
    78: ("IfcCovering", None), 190: ("IfcCurtainWall", None),
    30: ("IfcFurnishingElement", None), 224: ("IfcFurnishingElement", None),
    77: ("IfcSlab", "floor"), 90: ("IfcSlab", None),
}

res = []
for i, (cls, flt) in TYPE_FAMILIES.items():
    r = ROWS[i]
    model = r["path"].split("/")[-1][:-4]
    f = M(model)
    els = f.by_type(cls)
    if flt in ("ext", "int"):
        els = [w for w in els if ext_flag(model, w) == (flt == "ext")]
    if flt == "floor":
        els = [s for s in els if s.PredefinedType in ("FLOOR", "BASESLAB")]
    ans = r["answer"].split("Column Materials")[0].split("   Furniture Types:\n")[0] if i in (30, 41) else r["answer"]
    ref = parse_counts(ans)
    tot_m = re.search(r"Total [A-Za-z ]*?:\s*(\d+)", r["answer"])
    best = None
    for lab in labels(els[0]).keys() if els else []:
        c = collections.Counter()
        word = cls.replace("Ifc", "").replace("FurnishingElement", "Furniture")
        for e in els:
            v = labels(e)[lab]
            c[v if v else ("Unknown Type" if cls == "IfcDoor" else "Unknown Furniture" if word == "Furniture" else f"Unnamed {word}")] += 1
        exact = dict(c) == ref
        hits = sum(1 for k, v in ref.items() if c.get(k) == v)
        same_counts = sorted(c.values()) == sorted(ref.values())
        cand = (exact, hits, same_counts, lab, len(c))
        if best is None or cand[:3] > best[:3]:
            best = cand
    # blind baseline: one fixed rule for every model (type name if typed, else element name, Revit ':id' stripped)
    dflt = collections.Counter()
    for e in els:
        t = E.get_type(e)
        v = strip_id(t.Name if t and t.Name else e.Name)
        dflt[v if v else ("Unknown Type" if cls == "IfcDoor" else "Unknown Furniture" if cls == "IfcFurnishingElement" else f"Unnamed {cls[3:]}")] += 1
    res.append({"idx": i, "model": model, "family": f"{cls}{'/' + flt if flt else ''}", "question": r["question"],
                "default_rule_exact": dict(dflt) == ref, "default_rule_labels_matched": sum(1 for k, v in ref.items() if dflt.get(k) == v),
                "n_ref_labels": len(ref), "ref_total": int(tot_m.group(1)) if tot_m else None, "n_elements": len(els),
                "total_ok": (int(tot_m.group(1)) == len(els)) if tot_m else None,
                "exact_label_match": best[0] if best else False, "labels_matched": best[1] if best else 0,
                "count_multiset_match": best[2] if best else False, "best_label_source": best[3] if best else None})

# ---------- spaces per level ----------
AREA = {
    "ac20_arc": lambda s: P(s)["BaseQuantities"]["NetFloorArea"],
    "digital_hub_arc": lambda s: P(s)["Qto_SpaceBaseQuantities"]["NetFloorArea"],
    "fantasy_office_building_3_arc": lambda s: P(s)["PSet_Room"]["Area"],
    "hitos_arc": lambda s: [v for k, v in P(s).items() if isinstance(v, dict) and "NetFootprintArea" in v][0]["NetFootprintArea"],
}
LEVELQ = {4: "Keller", 5: "Erdgeschoss", 6: "1. Obergeschoss", 7: "2. Obergeschoss", 8: "Dachgeschoss",
          52: "B01_OKRD", 53: "E00_OKRD", 54: "E01_OKRD",
          167: "EG", 168: "OG1", 169: "OK OG2", 170: "OK OG3", 171: "OK OG4",
          201: "kjeller", 202: "1.etg", 203: "1.etg", 204: "2.etg", 205: "3.etg"}
for i, lvl in LEVELQ.items():
    r = ROWS[i]
    model = r["path"].split("/")[-1][:-4]
    f = M(model)
    sp = [s for s in f.by_type("IfcSpace") if storey(s) and storey(s).Name == lvl]
    areas = [AREA[model](s) for s in sp]
    a = r["answer"]
    cnt = re.search(r"(?:Total spaces: |: )(\d+) spaces?", a)
    tot = re.search(r"Total (?:Area|area|NetFootprintArea): ([\d.]+) sq m", a)
    ref_areas = sorted(float(x) for x in re.findall(r"([\d.]+) sq m\)?\s*$", a, re.M))
    if tot and ref_areas and abs(ref_areas[-1] - float(tot.group(1))) < 1e-9:
        ref_areas.remove(float(tot.group(1)))
    dec = 1 if model in ("ac20_arc", "digital_hub_arc", "hitos_arc") else 2
    comp_areas = sorted(round(x, dec) for x in areas)
    # hitos/dh answers also list per-function subtotals; keep only per-room values via multiset containment
    res.append({"idx": i, "model": model, "family": "spaces on level", "question": r["question"], "default_rule_exact": None, "default_rule_labels_matched": None,
                "n_ref_labels": len(ref_areas), "ref_total": int(cnt.group(1)) if cnt else None, "n_elements": len(sp),
                "total_ok": (int(cnt.group(1)) == len(sp)) if cnt else None,
                "exact_label_match": (abs(float(tot.group(1)) - sum(areas)) <= 0.05 * 10 ** (1 - dec) * 10) if tot else None,
                "labels_matched": sum((collections.Counter(comp_areas) & collections.Counter(round(x, dec) for x in ref_areas)).values()),
                "count_multiset_match": None, "best_label_source": f"area total ref={tot.group(1) if tot else None} comp={round(sum(areas), 2)}"})

import csv
keys = list(res[0].keys())
with open(os.path.join(W, "sweep_results.csv"), "w", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=keys)
    wr.writeheader()
    wr.writerows(res)
for x in res:
    print(f"[{x['idx']:3d}] {x['model'][:10]:10s} {x['family']:20s} ref_total={x['ref_total']} n={x['n_elements']} total_ok={x['total_ok']} "
          f"exact={x['exact_label_match']} matched={x['labels_matched']}/{x['n_ref_labels']} multiset={x['count_multiset_match']} src={x['best_label_source']}")

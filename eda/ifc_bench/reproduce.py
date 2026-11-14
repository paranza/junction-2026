"""Reproduce the seed-0 stratified sample of ifc_bench answers (repro_sample.json) with ifcopenshell.
Each handler parses facts out of the reference answer text and recomputes them from the IFC.
Counts must match exactly; numbers must match at the reference's displayed precision (exact) or within 2% (tol).
Usage: python -I reproduce.py <dataset_dir> <work_dir>  -> repro_results.csv / repro_results.json"""
import sys, os, re, json, collections, statistics as st
import numpy as np
import ifcopenshell, ifcopenshell.geom
import ifcopenshell.util.element as E

DS, W = sys.argv[1], sys.argv[2]
ROWS = [json.loads(l) for l in open(os.path.join(W, "ifc_bench_questions.jsonl"))]
_M = {}


def M(n):
    if n not in _M:
        _M[n] = ifcopenshell.open(os.path.join(DS, "data", "ifc_bench", n + ".ifc"))
    return _M[n]


def tname(e):
    t = E.get_type(e)
    return t.Name if t else None


def P(e):
    return E.get_psets(e)


def storey(e):
    c = E.get_container(e) or E.get_aggregate(e)
    while c is not None and not c.is_a("IfcBuildingStorey"):
        c = E.get_aggregate(c) or E.get_container(c)
    return c


def mat_names(e):
    m = E.get_material(e, should_skip_usage=True)
    if m is None:
        return []
    if m.is_a("IfcMaterial"):
        return [m.Name]
    if m.is_a("IfcMaterialLayerSet"):
        return [l.Material.Name for l in m.MaterialLayers if l.Material]
    if m.is_a("IfcMaterialConstituentSet"):
        return [c.Material.Name for c in m.MaterialConstituents if c.Material]
    if m.is_a("IfcMaterialList"):
        return [x.Name for x in m.Materials]
    return []


def is_placeholder(name, value):
    # Revit IFC exports fill unset text properties with their own name ('Fire Rating' = 'Fire Rating')
    return value is None or (isinstance(value, str) and value.strip().lower().replace(" ", "") in ("", name.lower().replace(" ", "")))


def C(label, ref, comp, kind="count", role="primary"):
    """one fact check. kind: count (exact int), num (displayed precision or 2%), eq, set, dict.
    role: primary (scored) | diag (alternative convention, not scored) | unverifiable (not derivable from the model, not scored)"""
    d = {"label": label, "ref": ref, "comp": comp, "role": role}
    if kind == "count":
        d["ok"] = d["exact"] = (comp is not None and int(ref) == int(comp))
    elif kind == "num":
        r = float(str(ref).replace(",", ""))
        dec = len(str(ref).split(".")[1]) if "." in str(ref) else 0
        d["exact"] = comp is not None and round(comp, dec) == round(r, dec)
        d["ok"] = comp is not None and (d["exact"] or (abs(comp - r) <= 0.02 * abs(r) if r else abs(comp) < 1e-9))
        d["comp"] = None if comp is None else round(comp, 4)
    elif kind == "set":
        d["ok"] = d["exact"] = set(ref) == set(comp)
        d["ref"], d["comp"] = sorted(map(str, ref)), sorted(map(str, comp))
        d["missing"], d["extra"] = sorted(map(str, set(ref) - set(comp))), sorted(map(str, set(comp) - set(ref)))
    elif kind == "dict":
        d["ok"] = d["exact"] = dict(ref) == dict(comp)
        diff = {k: (ref.get(k), comp.get(k)) for k in set(ref) | set(comp) if ref.get(k) != comp.get(k)}
        d["diff"] = {str(k): v for k, v in list(diff.items())[:10]}
        d["ref"], d["comp"] = len(ref), len(comp)
    else:
        d["ok"] = d["exact"] = ref == comp
    return d


def parse_counts(a, unit_words=r"[a-zA-Z()]+"):
    """lines like '- NAME: 142 columns (68.3%)' -> {NAME: 142}"""
    out = {}
    for m in re.finditer(r"^\s*-\s*(.+?):\s*(\d+)\s+" + unit_words, a, re.M):
        out[m.group(1).strip()] = int(m.group(2))
    return out


H = {}  # idx -> handler(answer) -> (checks, note)


def h(i):
    def deco(fn):
        H[i] = fn
        return fn
    return deco


# ---------------- element_dimensions ----------------
@h(218)
def _(a):
    f = M("hitos_arc")
    d = collections.defaultdict(lambda: [set(), 0])
    for w in f.by_type("IfcWall"):
        m = E.get_material(w)
        if m and m.is_a("IfcMaterialLayerSetUsage"):
            t = round(sum(l.LayerThickness for l in m.ForLayerSet.MaterialLayers if l.Material and l.Material.Name != "Empty Fill"))
            d[w.Name][0].add(t)
        d[w.Name][1] += 1
    ref = {}
    for m in re.finditer(r"^\s*-\s*(.+?):\s*([\dmm, ]+)\((\d+) walls\)", a, re.M):
        ref[m.group(1).strip()] = (frozenset(int(x) for x in re.findall(r"(\d+)mm", m.group(2))), int(m.group(3)))
    comp = {k: (frozenset(v[0]), v[1]) for k, v in d.items() if k in ref or v[0]}
    lo = min(t for v in d.values() for t in v[0]); hi = max(t for v in d.values() for t in v[0])
    rr = re.search(r"range: (\d+) - (\d+)", a)
    return [C("thickness set + count per wall type (39 types)", ref, {k: comp.get(k) for k in ref}, "dict"),
            C("range min", rr.group(1), lo), C("range max", rr.group(2), hi)], \
        "thickness = sum of IfcMaterialLayer thicknesses EXCLUDING the 21 mm 'Empty Fill' layer; type = IfcWall.Name"


@h(74)
def _(a):
    f = M("digital_hub_arc")
    ds = f.by_type("IfcDoor")
    clear = [P(d)["Abmessungen"]["Angabe Lichter Durchgang Breite"] for d in ds if "Angabe Lichter Durchgang Breite" in P(d).get("Abmessungen", {})]
    rough = [P(d)["Abmessungen"]["Rohbaubreite"] for d in ds if "Rohbaubreite" in P(d).get("Abmessungen", {})]
    qto = [P(d)["Qto_DoorBaseQuantities"]["Width"] for d in ds]
    return [C("avg (clear width, n=62)", "1.00", st.mean(clear), "num"), C("max (clear width)", "1.64", max(clear), "num"),
            C("min (clear width)", "0.80", min(clear), "num"), C("n with width data", 62, len(clear)),
            C("avg (Qto Width)", "1.00", st.mean(qto), "num", "diag"), C("max (Qto/rough width)", "1.64", max(rough), "num", "diag")], \
        "no single width property reproduces all 4 numbers: clear-opening width gives n=62, min 0.80 (avg 0.98, max 1.60); rough-opening/Qto width gives max 1.635 (avg 1.07)"


@h(211)
def _(a):
    f = M("hitos_arc")
    ws = [w for w in f.by_type("IfcWindow") if w.Name not in ("Vindusfelt", "Del av VF")]
    v = sorted(((round(w.OverallWidth), w.Name) for w in ws), key=lambda o: -o[0])
    ref = [(int(x), n.strip()) for x, n in re.findall(r"^\s*\d\.\s*(\d+) mm - (\S+)", a, re.M)]
    allw = [w.OverallWidth for w in f.by_type("IfcWindow")]
    return [C("top-5 widths+names (curtain-wall panels excluded)", ref, v[:5], "eq"),
            C("avg width", re.search(r"Average width: (\d+)", a).group(1), st.mean(x[0] for x in v), "num"),
            C("min width", 490, min(x[0] for x in v)), C("max incl. curtain-wall panels would be", 2030, round(max(allw)), role="diag")], \
        "reference silently excludes 'Vindusfelt' (curtain-wall panels, up to 19.5 m wide) and 'Del av VF' (6.25 m)"


# ---------------- element_lookup ----------------
@h(225)
def _(a):
    f = M("hitos_arc")
    sp = [s for s in f.by_type("IfcSpace") if "personalrom" in (s.LongName or "").lower() and storey(s).Name == "3.etg"]
    items = collections.Counter(x.Name for x in f.by_type("IfcFurnishingElement") if E.get_container(x) in sp)
    ref = {m.group(1).strip(): int(m.group(2)) for m in re.finditer(r"-\s*(.+?) \((\d+) items?\)", a)}
    return [C("staff room found (LongName 'Personalrom/møterom' on '3.etg')", 1, len(sp)), C("furniture by name", ref, dict(items), "dict")], \
        "'staff room' -> Norwegian 'Personalrom'; 'third floor' -> storey named '3.etg'; furniture contained in IfcSpace"


@h(113)
def _(a):
    f = M("duplex_arc")
    s = [x for x in f.by_type("IfcSpace") if x.Name == "A203"][0]
    depth = [i.Depth for r in s.Representation.Representations for i in r.Items if i.is_a("IfcExtrudedAreaSolid")][0]
    return [C("A203 height = IfcSpace body extrusion depth", "2.58", depth, "num"),
            C("Revit 'Unbounded Height' would give", "2.58", P(s)["PSet_Revit_Dimensions"]["Unbounded Height"], "num", "diag")], \
        "ceiling height = space solid height (2.581 m), not the Revit 2.6 m limit offset"


def bbox(e, s=None):
    s = s or ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    v = np.array(ifcopenshell.geom.create_shape(s, e).geometry.verts).reshape(-1, 3)
    return v.min(0), v.max(0)


@h(121)
def _(a):
    f = M("duplex_arc")
    sp = [x for x in f.by_type("IfcSpace") if x.Name == "A203"][0]
    lo, hi = bbox(sp)
    hits = collections.Counter()
    lb = {}
    for w in f.by_type("IfcWall"):
        wl, wh = bbox(w)
        tol = 0.05
        if (wl[:2] <= hi[:2] + tol).all() and (wh[:2] >= lo[:2] - tol).all() and wl[2] < hi[2] and wh[2] > lo[2]:
            hits[w.ObjectType.split(":")[1]] += 1
            lb[w.ObjectType.split(":")[1]] = P(w)["Pset_WallCommon"].get("LoadBearing")
    fams = {k.split(" - ")[0] if " - " in k else k for k in hits}
    return [C("3 wall kinds touch A203 (interior / party / exterior)", 3, len({("Interior" if k.startswith("Interior") else k) for k in hits})),
            C("model LoadBearing flag of 'Exterior - Brick on Block' (reference: 'likely load-bearing')", True, lb.get("Exterior - Brick on Block"), "eq")], \
        f"walls whose bbox touches A203: {dict(hits)}; LoadBearing flags {lb}. Reference load-bearing wording is interpretive and contradicts the explicit Pset_WallCommon.LoadBearing=False"


# ---------------- fire_safety_access ----------------
@h(131)
def _(a):
    return [C("estimated egress distance ~22 m", "estimate", "not derivable from stored data", "eq", "unverifiable")], \
        "interpretive estimate (no path/egress data in IFC); not reproducible deterministically"


@h(130)
def _(a):
    f = M("duplex_arc")
    ext = [d for d in f.by_type("IfcDoor") if P(d)["Pset_DoorCommon"].get("IsExternal") and storey(d).Name == "Level 1"]
    fr = [P(d)["Pset_DoorCommon"].get("FireRating") for d in ext]
    return [C("exterior doors on ground floor", 4, len(ext)),
            C("fire rating not specified (placeholder only)", True, all(is_placeholder("FireRating", x) or is_placeholder("Fire Rating", x) for x in fr), "eq")], \
        "IsExternal doors on 'Level 1'; FireRating holds the placeholder text 'Fire Rating'"


@h(129)
def _(a):
    f = M("duplex_arc")
    vals = [(P(d)["Pset_DoorCommon"].get("FireRating"), P(d).get("PSet_Revit_Type_Identity Data", {}).get("Fire Rating")) for d in f.by_type("IfcDoor") if not P(d)["Pset_DoorCommon"].get("IsExternal")]
    return [C("all internal-door fire ratings are placeholders", True, all(is_placeholder("Fire Rating", x) and is_placeholder("Fire Rating", y) for x, y in vals), "eq")], \
        f"{len(vals)} internal doors; FireRating values {collections.Counter(map(str, vals))}"


# ---------------- inventory_counts ----------------
@h(238)
def _(a):
    f = M("hitos_arc")
    c = collections.Counter((x.Name or "Unnamed Column") for x in f.by_type("IfcColumn"))
    ref = parse_counts(a, "columns")
    pct = {m.group(1).strip(): float(m.group(2)) for m in re.finditer(r"-\s*(.+?): \d+ columns \(([\d.]+)%\)", a)}
    n = sum(c.values())
    return [C("total", re.search(r"Total Columns: (\d+)", a).group(1), n), C("count per name", ref, dict(c), "dict"),
            C("percentages (1 dp)", pct, {k: round(100 * v / n, 1) for k, v in c.items()}, "dict")], "type = IfcColumn.Name (IFC2X3, no type objects); empty name -> 'Unnamed Column'"


@h(76)
def _(a):
    f = M("digital_hub_arc")
    c = collections.Counter(tname(s).split(":")[0] for s in f.by_type("IfcStair"))
    ref = parse_counts(a, "stairs")
    return [C("total stairs", 5, len(f.by_type("IfcStair"))), C("flights", 10, len(f.by_type("IfcStairFlight"))), C("by family name", ref, dict(c), "dict")], \
        "type = family part of 'Family:Type' type name"


@h(176)
def _(a):
    f = M("fantasy_office_building_3_arc")
    fu = f.by_type("IfcFurniture")
    c = collections.Counter(tname(x) for x in fu)
    ref = {m.group(1).strip(): int(m.group(2)) for m in re.finditer(r"^\s*-\s*(.+?): (\d+) item\(s\)", a, re.M)}
    fl = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s*-\s*(EG|OG1|OK OG\d): (\d+) items", a, re.M)}
    cf = collections.Counter(storey(x).Name for x in fu)
    return [C("total", 112, len(fu)), C("by type", ref, dict(c), "dict"), C("by floor", fl, {k: cf.get(k, 0) for k in fl}, "dict")], "IfcFurniture by IfcFurnitureType.Name; floor via containment"


# ---------------- lengths_volumes ----------------
@h(188)
def _(a):
    f = M("fantasy_office_building_3_arc")
    has_len = sum(1 for w in f.by_type("IfcWall") for k, v in P(w).items() for kk in v if kk.lower() in ("length", "länge"))
    return [C("no stored wall length quantity", 0, has_len)], "absent from properties/quantities (no Qto sets in this Revit export); a geometric length could still be computed from the wall axis"


@h(71)
def _(a):
    f = M("digital_hub_arc")
    L = collections.defaultdict(float)
    for w in f.by_type("IfcWall"):
        L[P(w)["Pset_WallCommon"]["IsExternal"]] += P(w)["Qto_WallBaseQuantities"]["Length"]
    g = lambda k: re.search(k + r": ([\d.]+) m", a).group(1)
    return [C("exterior", g("Total Exterior Walls"), L[True], "num"), C("interior", g("Total Interior Walls"), L[False], "num"),
            C("total", g("Total All Walls"), L[True] + L[False], "num")], "sum of Qto_WallBaseQuantities.Length split by Pset_WallCommon.IsExternal"


@h(93)
def _(a):
    f = M("digital_hub_arc")
    vol = lambda cls, q: sum(P(e)[q].get("NetVolume", 0) for e in f.by_type(cls))
    slabs = [s for s in f.by_type("IfcSlab") if s.PredefinedType != "LANDING"]
    sv = sum(P(s)["Qto_SlabBaseQuantities"]["NetVolume"] for s in slabs)
    conc = sum(P(s)["Qto_SlabBaseQuantities"]["NetVolume"] for s in slabs if "beton" in " ".join(mat_names(s)).lower())
    return [C("beams", "10.76", vol("IfcBeam", "Qto_BeamBaseQuantities"), "num"), C("columns", "18.52", vol("IfcColumn", "Qto_ColumnBaseQuantities"), "num"),
            C("slabs (all non-LANDING slabs)", "1612.18", sv, "num"), C("elements with volume", 94, 14 + 62 + len(slabs)),
            C("slabs if only concrete-material slabs counted", "1612.18", conc, "num", "diag")], \
        "NetVolume; slabs = 18 non-LANDING slabs incl. insulation (WD 200 hart), screed (FB 150) and 'Sohle 1 mm' -> label 'concrete' is inaccurate"


# ---------------- levels_heights ----------------
@h(64)
def _(a):
    f = M("digital_hub_arc")
    sts = sorted(f.by_type("IfcBuildingStorey"), key=lambda s: s.Elevation)
    out = []
    for i, s in enumerate(sts):
        ref = re.search(re.escape(s.Name) + r": ([\d.]+) m", a).group(1)
        if i + 1 < len(sts):
            out.append(C(f"{s.Name} floor-to-floor", ref, sts[i + 1].Elevation - s.Elevation, "num"))
        else:
            hs = collections.Counter(round(P(x)["Qto_SpaceBaseQuantities"]["Height"], 2) for x in f.by_type("IfcSpace") if storey(x) == s)
            out.append(C(f"{s.Name} mode of space heights", ref, hs.most_common(1)[0][0], "num"))
    return out, "reference mixes definitions: storey elevation difference for B01/E00, modal IfcSpace height for top storey E01"


@h(118)
def _(a):
    f = M("duplex_arc")
    e = {s.Name: s.Elevation for s in f.by_type("IfcBuildingStorey")}
    return [C("Level 2 - Level 1 elevation", "3.1", e["Level 2"] - e["Level 1"], "num")], "storey elevations"


@h(36)
def _(a):
    f = M("ac20_arc")
    hs = {round(P(s)["BaseQuantities"]["FinishCeilingHeight"], 2) for s in f.by_type("IfcSpace")}
    return [C("single ceiling height for all 82 rooms", {2.7}, hs, "set")], "BaseQuantities.FinishCeilingHeight"


# ---------------- materials ----------------
@h(29)
def _(a):
    f = M("ac20_arc")
    rs = [s for s in f.by_type("IfcSlab") if s.PredefinedType == "ROOF"]
    return [C("roof slabs counted as 'ceilings'", 21, len(rs)), C("IfcCovering count", 0, len(f.by_type("IfcCovering"))),
            C("materials", {"Aluminium 131198"}, {n for s in rs for n in mat_names(s)}, "set")], "reference treats ROOF slabs as 'potential ceilings' when no IfcCovering exists"


@h(87)
def _(a):
    f = M("digital_hub_arc")
    ref = set(re.findall(r"^\s*-\s*(.+?)\s*$", a, re.M))
    kw = {m.Name for m in f.by_type("IfcMaterial") if re.search(r"beton|metall|stahl", m.Name or "", re.I)}
    struct = {n for cls in ("IfcBeam", "IfcColumn", "IfcSlab", "IfcMember", "IfcPlate", "IfcFooting") for e in f.by_type(cls) for n in mat_names(e)}
    return [C("keyword filter on all material names (beton|metall|stahl)", ref, kw, "set"),
            C("materials actually assigned to beams/columns/slabs/members/plates", ref, struct, "set", "diag")], \
        "reference list = name keyword filter over all IfcMaterial, not materials of structural elements (Metall - Zink is only on proxies)"


@h(65)
def _(a):
    f = M("digital_hub_arc")
    comp = collections.defaultdict(set)
    for w in f.by_type("IfcWall"):
        comp[tname(w)].update(mat_names(w))
    ref = {}
    cur = None
    for line in a.splitlines():
        m = re.match(r"^\s{2,4}(Basiswand:.+):\s*$", line)
        if m:
            cur = m.group(1).strip(); ref[cur] = set(); continue
        m = re.match(r"^\s*-\s*(.+?)\s*$", line)
        if m and cur:
            ref[cur].add(m.group(1))
    cmp_ = {k: frozenset(comp.get(k, set())) for k in ref}
    return [C("material set per wall type", {k: frozenset(v) for k, v in ref.items()}, cmp_, "dict"),
            C("wall types covered", set(ref), set(comp), "set")], "union of IfcMaterial/IfcMaterialConstituentSet names over walls of each IfcWallType"


# ---------------- mep ----------------
MEP_CLASSES = ["IfcFlowSegment", "IfcFlowFitting", "IfcFlowTerminal", "IfcFlowController", "IfcFlowMovingDevice",
               "IfcFlowStorageDevice", "IfcFlowTreatmentDevice", "IfcEnergyConversionDevice", "IfcDistributionControlElement", "IfcDistributionFlowElement"]


def n_mep(f, storey_name=None):
    n = 0
    for c in MEP_CLASSES:
        try:
            es = f.by_type(c)
        except RuntimeError:
            continue
        n += sum(1 for e in es if storey_name is None or (storey(e) and storey(e).Name == storey_name))
    return n


@h(103)
def _(a):
    f = M("digital_hub_arc")
    return [C("MEP components on E01_OKRD in the provided arc model", 0, n_mep(f, "E01_OKRD")),
            C("'primary functions' text", "generic text", "not derivable", "eq", "unverifiable")], "zero counts reproducible; listed functions are generic prose not grounded in the file"


@h(47)
def _(a):
    f = M("ac20_arc")
    heat = sum(len(f.by_type(c)) for c in ["IfcSpaceHeater", "IfcBoiler", "IfcPipeSegment", "IfcPump", "IfcHeatExchanger"])
    return [C("heating components", 0, heat), C("any distribution elements", 0, n_mep(f))], ""


@h(247)
def _(a):
    f = M("hitos_arc")
    cool = sum(1 for e in f.by_type("IfcDistributionFlowElement") if re.search(r"chill|cool|kjøl|air ?terminal|duct|coil", (e.is_a() + " " + str(tname(e)) + " " + str(e.Name)), re.I))
    terms = collections.Counter(tname(x) for x in f.by_type("IfcFlowTerminal"))
    return [C("cooling components", 0, cool)], f"only distribution elements are 69 IfcFlowTerminal (sanitary types: {dict(terms)})"


# ---------------- metadata ----------------
@h(1)
def _(a):
    f = M("ac20_arc")
    return [C("originating system string", True, f.header.file_name.originating_system.startswith("IFC file generated by GRAPHISOFT ARCHICAD-64 20.0.0 GER FULL Windows version"), "eq"),
            C("schema", "IFC4", f.schema, "eq")], "IFC header FILE_NAME.originating_system + schema"


@h(198)
def _(a):
    f = M("hitos_arc")
    s = f.by_type("IfcSite")[0]
    lat, lon = s.RefLatitude, s.RefLongitude
    return [C("project name", "Default Project", f.by_type("IfcProject")[0].Name, "eq"), C("building name", "Default Building", f.by_type("IfcBuilding")[0].Name, "eq"),
            C("site name", "Default Site", s.Name, "eq"), C("lat/lon", "69°40'0\"N, 18°50'0\"E", f"{lat[0]}°{lat[1]}'{lat[2]}\"N, {lon[0]}°{lon[1]}'{lon[2]}\"E", "eq"),
            C("building usage defined", False, bool(P(f.by_type("IfcBuilding")[0]).get("Pset_BuildingCommon", {}).get("OccupancyType")), "eq")], "IfcProject/IfcBuilding/IfcSite attributes"


@h(164)
def _(a):
    f = M("fantasy_office_building_3_arc")
    ap = f.by_type("IfcApplication")[0]
    return [C("schema", "IFC4", f.schema, "eq"), C("application", "Autodesk Revit 2024 (DEU)", ap.ApplicationFullName, "eq"), C("version", "2024", ap.Version, "eq")], "IfcApplication"


# ---------------- performance_lifecycle ----------------
def any_prop(f, pat):
    return [(p.Name, p.NominalValue.wrappedValue if p.NominalValue else None) for p in f.by_type("IfcPropertySingleValue") if re.search(pat, p.Name or "", re.I)]


@h(138)
def _(a):
    hits = any_prop(M("duplex_arc"), r"thermal ?bridge|wärmebrück|psi")
    return [C("no thermal-bridge property", 0, len(hits))], ""


@h(140)
def _(a):
    hits = any_prop(M("duplex_arc"), r"solar|shgc|g-?value")
    return [C("no solar-heat-gain property", 0, len(hits))], ""


@h(141)
def _(a):
    f = M("duplex_arc")
    r = f.by_type("IfcRoof")[0]
    el = P(r)["PSet_Revit_Type_Other"].get("ExpectedLife")
    return [C("ExpectedLife present but unset (placeholder)", True, is_placeholder("ExpectedLife", el), "eq"),
            C("roofing material contains 'Roofing - EPDM Membrane'", True, "Roofing - EPDM Membrane" in mat_names(r), "eq"),
            C("industry lifespan 30-50 years", "external knowledge", "not in model", "eq", "unverifiable")], "model facts reproducible; lifespan range is outside knowledge"


# ---------------- spaces_areas ----------------
@h(8)
def _(a):
    f = M("ac20_arc")
    sp = [s for s in f.by_type("IfcSpace") if storey(s).Name == "Dachgeschoss"]
    comp = {(s.Name, s.LongName): round(P(s)["BaseQuantities"]["NetFloorArea"], 1) for s in sp}
    ref = {(m.group(1), m.group(2).strip()): float(m.group(3)) for m in re.finditer(r"-\s*(\d+): (.+?) \(([\d.]+) sq m\)", a)}
    tot = sum(P(s)["BaseQuantities"]["NetFloorArea"] for s in sp)
    return [C("rooms+areas (NetFloorArea, 1 dp)", ref, comp, "dict"), C("total", "202.4", tot, "num"), C("count", 3, len(sp))], "BaseQuantities.NetFloorArea (GrossFloorArea would give 201.78 per attic room)"


@h(153)
def _(a):
    f = M("duplex_arc")
    return [C("rooms named A*", 10, sum(1 for s in f.by_type("IfcSpace") if re.match(r"A\d", s.Name)))], \
        "house A = IfcSpace.Name prefix 'A' (includes A105 'Stair'); note Q152's reference lists only 9 rooms"


@h(167)
def _(a):
    f = M("fantasy_office_building_3_arc")
    sp = [s for s in f.by_type("IfcSpace") if storey(s).Name == "EG"]
    comp = collections.Counter()
    for s in sp:
        comp[(s.LongName, round(P(s)["PSet_Room"]["Area"], 2))] += 1
    ref = collections.Counter((m.group(1).strip(), float(m.group(2))) for m in re.finditer(r"^\s*-\s*(.+?): ([\d.]+) sq m", a, re.M))
    return [C("count", 18, len(sp)), C("total", "358.01", sum(P(s)["PSet_Room"]["Area"] for s in sp), "num"), C("name+area multiset", dict(ref), dict(comp), "dict")], \
        "area = PSet_Room.Area (no Qto sets in this export)"


# ---------------- structural_interpretation ----------------
@h(95)
def _(a):
    f = M("digital_hub_arc")
    c = collections.Counter(tname(m) for m in f.by_type("IfcMember"))
    ref = parse_counts(a, "members")
    relabel = {("Stair Stringer" if k.startswith("Wange") else k): v for k, v in c.items()}
    return [C("raw type names", ref, dict(c), "dict"), C("after translating 'Wange:Metall 10 x 260' -> 'Stair Stringer'", ref, relabel, "dict", "diag")], \
        "reference renamed the German type 'Wange' (stringer) to 'Stair Stringer'"


@h(88)
def _(a):
    f = M("digital_hub_arc")
    bs = f.by_type("IfcBeam")
    lens = [P(b)["Qto_BeamBaseQuantities"]["Length"] for b in bs]
    return [C("reference says span/size info not available; model has it", "not available",
              f"{len(bs)} beams, type '{tname(bs[0])}', Qto Length {min(lens):.2f}-{max(lens):.2f} m", "eq")], \
        "reference 'not available' is contestable: section size is in the type name and lengths are in Qto_BeamBaseQuantities"


@h(187)
def _(a):
    f = M("fantasy_office_building_3_arc")
    ws = f.by_type("IfcWall")
    lb = [w for w in ws if P(w)["Pset_WallCommon"].get("LoadBearing")]
    ref = parse_counts(a, r"wall\(s\)")
    return [C("total", 223, len(ws)), C("load-bearing", 98, len(lb)), C("pct", "43.9", 100 * len(lb) / len(ws), "num"),
            C("by type", ref, dict(collections.Counter(tname(w) for w in lb)), "dict")], "Pset_WallCommon.LoadBearing"


# ---------------- takeoff_estimate ----------------
@h(149)
def _(a):
    f = M("duplex_arc")
    s1 = sum(2 * (P(w).get("PSet_Revit_Dimensions", {}).get("Area") or 0) for w in f.by_type("IfcWall") if not P(w)["Pset_WallCommon"].get("IsExternal"))
    s2 = s1 + sum((P(w).get("PSet_Revit_Dimensions", {}).get("Area") or 0) for w in f.by_type("IfcWall") if P(w)["Pset_WallCommon"].get("IsExternal") and "Foundation" not in w.ObjectType)
    return [C("estimate ~398 m2 (method A: 2 sides of interior walls)", "398", s1, "num"), C("method B: + inner face of above-ground exterior walls", "398", s2, "num", "diag")], \
        "reference is an unexplained estimate; two simple methods shown"


@h(161)
def _(a):
    f = M("duplex_arc")
    b = {s.Name: P(s)["PSet_Revit_Dimensions"]["Area"] for s in f.by_type("IfcSpace") if "bathroom" in (s.LongName or "").lower()}
    ref = {m.group(1): m.group(2) for m in re.finditer(r"-\s*([AB]\d{3}): ([\d.]+) sqm", a)}
    return [C(f"{k} floor area", v, b.get(k), "num") for k, v in ref.items()] + [C("total", "18.85", sum(b.values()), "num")], "bathroom IfcSpace floor areas (PSet_Revit_Dimensions.Area)"


@h(157)
def _(a):
    f = M("duplex_arc")
    out = {}
    tiles = [s for s in f.by_type("IfcSlab") if "Ceramic Tile" in (s.Name or "")]
    for room in [x for x in f.by_type("IfcSpace") if x.Name in ("A104", "A204")]:
        lo, hi = bbox(room)
        tot = 0
        for t in tiles:
            tl, th = bbox(t)
            c = (tl + th) / 2
            if lo[0] <= c[0] <= hi[0] and lo[1] <= c[1] <= hi[1] and abs(tl[2] - lo[2]) < 0.3:
                tot += P(t)["PSet_Revit_Dimensions"]["Area"]
        out[room.Name] = tot
    return [C("A204 tile area", "6.34", out["A204"], "num"), C("A104 tile area", "3.16", out["A104"], "num"), C("total", "9.50", sum(out.values()), "num")], \
        "area of 'Floor:Finish Floor - Ceramic Tile' slabs located in each bathroom (differs from Q161 which uses room floor area)"


def main():
    sample = json.load(open(os.path.join(W, "repro_sample.json")))
    res = []
    for cat, i in sample:
        r = ROWS[i]
        try:
            checks, note = H[i](r["answer"])
        except Exception as e:  # keep going, record the failure
            checks, note = [{"label": "handler error", "ok": False, "exact": False, "ref": None, "comp": repr(e)}], "error"
        prim = [c for c in checks if c.get("role", "primary") == "primary"]
        k = sum(c["ok"] for c in prim)
        unver = sum(c.get("role") == "unverifiable" for c in checks)
        status = ("reproduced" if k == len(prim) and not unver else "model facts reproduced; rest unverifiable" if k == len(prim) and prim
                  else "unverifiable" if not prim else "partial" if k else "not reproduced")
        res.append({"idx": i, "category": cat, "model": r["path"].split("/")[-1], "question": r["question"],
                    "facts_ok": k, "facts_total": len(prim), "n_unverifiable": unver, "status": status,
                    "all_ok": k == len(prim) and len(prim) > 0, "all_exact": all(c.get("exact", c["ok"]) for c in prim) and len(prim) > 0,
                    "note": note, "checks": checks})
    json.dump(res, open(os.path.join(W, "repro_results.json"), "w"), indent=1, default=str, ensure_ascii=False)
    import csv
    with open(os.path.join(W, "repro_results.csv"), "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["idx", "category", "model", "question", "status", "facts_ok", "facts_total", "n_unverifiable", "all_ok", "all_exact", "note"])
        for x in res:
            wr.writerow([x["idx"], x["category"], x["model"], x["question"], x["status"], x["facts_ok"], x["facts_total"], x["n_unverifiable"], x["all_ok"], x["all_exact"], x["note"]])
    for x in res:
        print(f"[{x['idx']:3d}] {x['category']:26s} {x['facts_ok']}/{x['facts_total']} {x['status']:42s} {x['question'][:60]}")
        for c in x["checks"]:
            if not c["ok"] and c.get("role") == "primary":
                print("        FAIL", c["label"], "| ref:", str(c["ref"])[:150], "| comp:", str(c["comp"])[:150], "| diff:", str(c.get("diff", c.get("missing", "")))[:200], str(c.get("extra", ""))[:150])


    cats = collections.defaultdict(lambda: [0, 0, 0])
    for x in res:
        cats[x["category"]][0] += x["status"] == "reproduced"
        cats[x["category"]][1] += x["status"] in ("reproduced", "model facts reproduced; rest unverifiable")
        cats[x["category"]][2] += 1
    print("\nper category: fully reproduced / model facts reproduced / n")
    for k, v in sorted(cats.items()):
        print(f"  {k:26s} {v[0]}/{v[2]}  {v[1]}/{v[2]}")
    print("TOTAL", collections.Counter(x["status"] for x in res))


if __name__ == "__main__":
    main()

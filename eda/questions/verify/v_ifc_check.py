import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Independent reproduction of ifc_models answers (F5, F6). Own rules, own geometry code.
import json, os, re, collections, time
import numpy as np
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue, ifcopenshell.util.unit as uu
from shapely.geometry import Polygon
from shapely.ops import unary_union
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
Q = [(i, r) for i, r in enumerate(rows) if r["path"].startswith("data/ifc_models/") and langs[i] == "en"]
def source_ifc(path):
    d, fn = os.path.split(path); stem = os.path.splitext(fn)[0]
    if fn.endswith(".ifc"): return path
    m = re.match(r"(.*)_plan-\d+-.*$", stem)
    return os.path.join(d, m.group(1) + ".ifc") if m else None
models = {}
def load(p):
    if p not in models:
        full = os.path.join(DS, p)
        models[p] = ifcopenshell.open(full) if os.path.exists(full) else None
    return models[p]
S = ifcopenshell.geom.settings(); S.set("use-world-coords", True)
def footprint(e):
    sh = ifcopenshell.geom.create_shape(S, e)
    v = np.array(sh.geometry.verts).reshape(-1, 3); fa = np.array(sh.geometry.faces).reshape(-1, 3)
    tris = [Polygon(v[t][:, :2]) for t in fa]
    tris = [t for t in tris if t.area > 1e-12]
    return unary_union(tris).area, v[:, 2].min(), v[:, 2].max()  # metres (iterator converts to SI)
def qto(e, name):
    vals = []
    for rel in getattr(e, "IsDefinedBy", []) or []:
        if rel.is_a("IfcRelDefinesByProperties") and rel.RelatingPropertyDefinition.is_a("IfcElementQuantity"):
            for q in rel.RelatingPropertyDefinition.Quantities:
                if q.Name == name:
                    vals.append((rel.RelatingPropertyDefinition.Name, q[3]))
    return vals
def contained(st):
    return [o for r in (st.ContainsElements or []) for o in r.RelatedElements]
def spaces(st):
    return [o for r in (st.IsDecomposedBy or []) for o in r.RelatedObjects if o.is_a("IfcSpace")]
def storey(f, name):
    c = [s for s in f.by_type("IfcBuildingStorey") if s.Name == name]
    assert len(c) == 1, (name, len(c)); return c[0]
CLS = {"doors": "IfcDoor", "walls": "IfcWall", "columns": "IfcColumn", "stairs": "IfcStair", "windows": "IfcWindow", "beams": "IfcBeam", "rooms (spaces)": "IfcSpace"}
res = []
area_cache = {}
def space_area(f, sp):
    k = sp.id()
    if k in area_cache: return area_cache[k]
    q = qto(sp, "NetFloorArea")
    g = footprint(sp)[0]
    lu = uu.calculate_unit_scale(f)  # length unit -> metres
    qv = q[0][1] if q else None
    area_cache[k] = dict(qto=qv, geom=g, qto_src=q[0][0] if q else None)
    return area_cache[k]
for i, r in Q:
    q = r["question"]; a = r["answer"]; src = source_ifc(r["path"]); f = load(src)
    rec = dict(i=i, path=r["path"].split("/")[-1], q=q, ans=a, src=src.split("/")[-1], asked_on=os.path.splitext(r["path"])[1])
    if f is None:
        rec.update(status="no_source_ifc"); res.append(rec); continue
    m = re.match(r"What is the net floor area of the room '(.*)' on '(.*)', in m²\?$", q)
    if m:
        room, stn = m.groups(); st = storey(f, stn)
        cand = [s for s in spaces(st) if f"{s.LongName} ({s.Name})" == room]
        rec["n_match"] = len(cand)
        if len(cand) == 1:
            A = space_area(f, cand[0]); rec.update(qto=A["qto"], geom=A["geom"])
        res.append(rec); continue
    m = re.match(r"What is the total net floor area of all rooms \(spaces\) on '(.*)', in m²\?$", q)
    if m:
        st = storey(f, m.group(1)); A = [space_area(f, s) for s in spaces(st)]
        rec.update(qto=sum(x["qto"] for x in A) if all(x["qto"] is not None for x in A) else None, geom=sum(x["geom"] for x in A)); res.append(rec); continue
    m = re.match(r"How many (doors|walls|columns|stairs|windows|rooms \(spaces\)) are shown on the floor plan of '(.*)'\?$", q)
    if m:
        k, stn = m.groups(); st = storey(f, stn)
        if k == "rooms (spaces)": rec["count"] = len(spaces(st))
        else: rec["count"] = sum(1 for o in contained(st) if o.is_a(CLS[k]))
        res.append(rec); continue
    m = re.match(r"How many (doors|walls|columns|stairs|windows|beams|rooms \(spaces\)|sanitary fixtures) are there in the model '(.*)'\?$", q)
    if m:
        k = m.group(1)
        if k == "sanitary fixtures":
            rec["count_alts"] = {c: len(f.by_type(c)) for c in ["IfcFlowTerminal"] if True}
            rec["count"] = len(f.by_type("IfcFlowTerminal"))
        elif k == "stairs":
            # stairs not nested inside another element (contained directly in spatial structure)
            rec["count"] = sum(1 for s in f.by_type("IfcStair") if not s.Decomposes)
            rec["count_all"] = len(f.by_type("IfcStair"))
        else:
            rec["count"] = len(f.by_type(CLS[k]))
        res.append(rec); continue
    m = re.match(r"What is the total (net volume|net side area|length) of all (walls|slabs) on '(.*)', in (m³|m²|metres)\?$", q)
    if m:
        what, cls, stn, unit = m.groups(); st = storey(f, stn)
        els = [o for o in contained(st) if o.is_a("IfcWall" if cls == "walls" else "IfcSlab")]
        qn = {"net volume": "NetVolume", "net side area": "NetSideArea", "length": "Length"}[what]
        vals = [qto(o, qn) for o in els]
        rec["n_el"] = len(els); rec["n_with_q"] = sum(1 for v in vals if v)
        s = sum(v[0][1] for v in vals if v)
        lu = uu.calculate_unit_scale(f)
        rec["qto_raw"] = s
        rec["qto"] = s * lu if what == "length" else s  # IFC2X3 ArchiCAD: areas/volumes already in m2/m3? checked below
        res.append(rec); continue
    rec["status"] = "unparsed"; res.append(rec)
json.dump(res, open(os.path.join(OUT, "ifc_res.json"), "w"), default=str, ensure_ascii=False)
# scoring
def ok(pred, ans, typ):
    if pred is None: return False
    return pred == ans if typ == "count" else abs(pred - ans) <= 0.02 * abs(ans)
tally = collections.Counter(); fails = []
for rec in res:
    r = rows[rec["i"]]
    fam = re.sub(r"'[^']*'", "<Q>", r["question"])
    if rec.get("status"): tally[(fam, rec["status"])] += 1; continue
    if r["type"] == "count": good = ok(rec.get("count"), r["answer"], "count")
    else:
        good = ok(rec.get("qto"), r["answer"], r["type"]) or ok(rec.get("geom"), r["answer"], r["type"])
    tally[(fam, "ok" if good else "FAIL")] += 1
    if not good: fails.append(rec)
for k, v in sorted(tally.items()): print(v, k)
print("total ok", sum(v for k, v in tally.items() if k[1] == "ok"), "testable", sum(v for k, v in tally.items() if k[1] in ("ok", "FAIL")))
for x in fails[:30]: print("FAIL", x)

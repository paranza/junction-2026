"""Reproduce ifc_models answers from the source IFC (also for questions asked on the rendered PDF floor plans),
to learn the ground-truth conventions. English rows only. Counts exact, quantities within 2%.
Run: python -I ifc_models_check.py"""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
import sys, re
sys.path.insert(0, _ROOT + "/eda/questions")
import pandas as pd
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue, ifcopenshell.util.shape as us, ifcopenshell.util.unit as uu
from qlib import DATASET, WORK

q = pd.read_csv(WORK + "questions_annotated.csv")
q = q[(q.source == "ifc_models") & (q.lang == "en")].copy()
q["ifc"] = q.path.map(lambda p: re.sub(r"_plan-\d+-.*\.pdf$", ".ifc", p) if p.endswith(".pdf") else p)
GEOM = ifcopenshell.geom.settings()
TYPES = {"doors": "IfcDoor", "windows": "IfcWindow", "walls": "IfcWall", "columns": "IfcColumn", "beams": "IfcBeam",
         "stairs": "IfcStair", "rooms": "IfcSpace", "sanitary": "IfcFlowTerminal"}


def qto(el, keys):
    for pset in ue.get_psets(el, qtos_only=True).values():
        for k in keys:
            if k in pset:
                return pset[k]
    return None


def storey_of(el):
    c = ue.get_container(el) or ue.get_aggregate(el)
    while c is not None and not c.is_a("IfcBuildingStorey"):
        c = ue.get_aggregate(c)
    return c.Name if c is not None else None


def top_level(el):
    agg = ue.get_aggregate(el)
    return agg is None or agg.is_a("IfcSpatialStructureElement")


def space_area(s):
    a = qto(s, ["NetFloorArea"])
    if a is not None:
        return a, "qto"
    return us.get_footprint_area(ifcopenshell.geom.create_shape(GEOM, s).geometry), "footprint"


rows = []
for ifc_path, g in q.groupby("ifc"):
    try:
        f = ifcopenshell.open(DATASET + ifc_path)
    except Exception as e:
        for r in g.itertuples():
            rows.append(dict(line=r.line, path=r.path, family=r.family, answer=r.answer, pred=None, correct=None, note=f"IFC missing: {type(e).__name__}"))
        continue
    lscale = uu.calculate_unit_scale(f)  # project length unit -> metres
    spaces = []
    for s in f.by_type("IfcSpace"):
        spaces.append(dict(el=s, name=f"{s.LongName} ({s.Name})", level=storey_of(s)))
    sp = pd.DataFrame(spaces)
    for r in g.itertuples():
        slots = r.slots.split(" | ") if isinstance(r.slots, str) else []
        pred, note = None, ""
        fam = r.family
        level = slots[-1] if slots else None
        if fam == "area_room_by_name":
            m = sp[(sp.name == slots[0]) & (sp.level == slots[1])]
            if len(m) == 1:
                pred, note = space_area(m.el.iloc[0])
            else:
                note = f"{len(m)} matching spaces"
        elif fam == "area_level_spaces_total":
            m = sp[sp.level == level]
            areas = [space_area(e) for e in m.el]
            pred, note = sum(a for a, _ in areas), f"{len(m)} spaces, {set(k for _, k in areas)}"
        elif fam.startswith("count_level_"):
            t = TYPES[fam.split("_")[-1]]
            els = [e for e in f.by_type(t) if storey_of(e) == level]
            if t == "IfcStair":
                els = [e for e in els if top_level(e)]
            pred = len(els)
        elif fam.startswith("count_model_"):
            t = TYPES[fam.split("_")[-1]]
            els = f.by_type(t)
            if t == "IfcStair":
                note = f"all IfcStair={len(els)}"
                els = [e for e in els if top_level(e)]
            pred = len(els)
        elif fam in ("length_level_walls", "volume_level_walls", "area_level_wall_side", "volume_level_slabs"):
            t = "IfcSlab" if "slabs" in fam else "IfcWall"
            key = {"length_level_walls": ["Length"], "volume_level_walls": ["NetVolume"], "area_level_wall_side": ["NetSideArea"],
                   "volume_level_slabs": ["NetVolume"]}[fam]
            els = [e for e in f.by_type(t) if storey_of(e) == level]
            vals = [qto(e, key) for e in els]
            missing = sum(v is None for v in vals)
            s = sum(v for v in vals if v is not None)
            pred = s * lscale if fam == "length_level_walls" else s
            note = f"{len(els)} elements, {missing} without qto"
        ok = None
        if pred is not None:
            a = float(r.answer); ok = round(pred) == a if r.type == "count" else abs(pred - a) <= 0.02 * abs(a)
        rows.append(dict(line=r.line, path=r.path.split("/")[-1], family=fam, slots=r.slots, answer=r.answer,
                         pred=round(pred, 4) if pred is not None else None, correct=ok, note=note))

res = pd.DataFrame(rows)
res.to_csv(WORK + "ifc_models_check.csv", index=False)
print(res.groupby("family").correct.agg(tested=lambda s: s.notna().sum(), correct=lambda s: (s == True).sum()))
print("untested:", res[res.correct.isna()].groupby(["path", "note"]).size().to_dict())
print(res[res.correct == False].to_string(index=False))
print("asked on PDF and correct from IFC:", res[res.path.str.endswith(".pdf") & res.correct.notna()].correct.agg(["sum", "size"]).to_dict())

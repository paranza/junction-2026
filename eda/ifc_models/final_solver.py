import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# One-method-per-family solver implementing the ground-truth conventions found in the EDA; returns value + GUIDs used.
import os, re, sys, functools, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir; parse_q lives next to this file
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue, ifcopenshell.util.unit as uu
from parse_q import parse
DS = _DATA + "/"
CLS = {"door": "IfcDoor", "window": "IfcWindow", "wall": "IfcWall", "column": "IfcColumn", "beam": "IfcBeam", "stair": "IfcStair", "space": "IfcSpace", "sanitary": "IfcFlowTerminal"}
def model_path(path):  # <model>_<level>.pdf/.svg -> <model>.ifc (README convention)
    if path.endswith(".ifc"): return path
    return re.sub(r"_plan-[^/]*$", "", path.rsplit(".", 1)[0]) + ".ifc"
@functools.lru_cache(maxsize=4)
def load(p):
    f = ifcopenshell.open(DS + p)
    sc = {u: uu.calculate_unit_scale(f, u) for u in ("LENGTHUNIT", "AREAUNIT", "VOLUMEUNIT")}
    return f, sc
def children(storey):  # direct spatial children only (contained elements + aggregated spaces)
    out = [e for r in storey.ContainsElements or [] for e in r.RelatedElements]
    return out + [e for r in storey.IsDecomposedBy or [] for e in r.RelatedObjects]
def qto(e, name):
    for qs in ue.get_psets(e, qtos_only=True).values():
        if name in qs: return qs[name]
    return None
def floor_face_area(e):  # fallback: area of the lowest downward-facing faces of the body
    st = ifcopenshell.geom.settings(); st.set("use-world-coords", True)
    g = ifcopenshell.geom.create_shape(st, e).geometry
    v = np.array(g.verts).reshape(-1, 3); t = np.array(g.faces).reshape(-1, 3)
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    n = np.cross(b - a, c - a); ln = np.linalg.norm(n, axis=1)
    down = n[:, 2] / np.maximum(ln, 1e-12) < -0.999
    low = (a[:, 2] + b[:, 2] + c[:, 2]) / 3 < v[:, 2].min() + 0.001
    return float(ln[down & low].sum() / 2)
def space_area(e, sc):
    q = qto(e, "NetFloorArea")
    return (q * sc["AREAUNIT"], "qto") if q is not None else (floor_face_area(e), "geometry")
def answer(path, question):
    p = parse(question); fam = p["family"]
    if fam is None: return None, [], "unparsed"
    mp = model_path(path)
    if not os.path.exists(DS + mp): return None, [], "model IFC not available"
    f, sc = load(mp)
    if fam == "model_count":
        X = [e for e in f.by_type(CLS[p["what"]]) if ue.get_container(e, should_get_direct=True) or (ue.get_aggregate(e) or e).is_a("IfcSpatialStructureElement")]
        if p["what"] == "sanitary": X = [e for e in X if (ue.get_type(e) or e).is_a() in ("IfcSanitaryTerminalType", "IfcSanitaryTerminal")]
        return len(X), [e.GlobalId for e in X], "containment"
    S = [s for s in f.by_type("IfcBuildingStorey") if s.Name == p["storey"]]
    if len(S) != 1: return None, [], f"storey match count {len(S)}"
    kids = children(S[0])
    if fam == "storey_count":
        X = [e for e in kids if e.is_a(CLS[p["what"]])]
        return len(X), [e.GlobalId for e in X], "containment"
    if fam in ("room_area", "storey_space_area"):
        sp = [e for e in kids if e.is_a("IfcSpace")]
        if fam == "room_area": sp = [e for e in sp if f"{e.LongName} ({e.Name})" == p["room"]]
        if fam == "room_area" and len(sp) != 1: return None, [], f"label match count {len(sp)}"
        vals = [space_area(e, sc) for e in sp]
        return round(sum(v for v, _ in vals), 2), [e.GlobalId for e in sp], "+".join(sorted({s for _, s in vals}))
    cls, qn, unit = {"wall_length": ("IfcWall", "Length", "LENGTHUNIT"), "wall_side_area": ("IfcWall", "NetSideArea", "AREAUNIT"),
                     "wall_volume": ("IfcWall", "NetVolume", "VOLUMEUNIT"), "slab_volume": ("IfcSlab", "NetVolume", "VOLUMEUNIT")}[fam]
    X = [e for e in kids if e.is_a(cls)]
    vals = [qto(e, qn) for e in X]
    miss = sum(v is None for v in vals)
    return round(sum(v for v in vals if v is not None) * sc[unit], 3), [e.GlobalId for e in X], f"qto (missing on {miss} of {len(X)})"
if __name__ == "__main__":
    q = "How many stairs are there in the model 'Molio Demo-hus'?"
    v, g, how = answer("data/ifc_models/bsc-molio_molio-with-uris_plan-02-klder.pdf", q)
    assert v == 15, v  # self-check: nested stair parts must not be counted
    print(q, v, how)

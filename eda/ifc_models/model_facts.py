import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Extract per-model facts (spaces, element membership per storey, quantity sets, geometry metrics) into pickles.
import sys, time, pickle, collections
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue, ifcopenshell.util.shape as us
DS = _DATA + "/data/ifc_models/"
model = sys.argv[1]
t0 = time.time()
f = ifcopenshell.open(DS + model + ".ifc")
st = ifcopenshell.geom.settings(); st.set("use-world-coords", True)
def storey_of(e):
    x = e
    for _ in range(10):
        c = ue.get_container(x)
        if c is not None:
            x = c
        else:
            a = ue.get_aggregate(x)
            if a is None: return None
            x = a
        if x.is_a("IfcBuildingStorey"): return x.Name
    return None
def num(v):
    try: return float(str(v).replace(",", "."))
    except Exception: return None
def bottom_areas(g):
    # area of down-facing triangles: all of them, and only those at the lowest z (the floor face)
    import numpy as np
    v = np.array(g.verts).reshape(-1, 3); t = np.array(g.faces).reshape(-1, 3)
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    n = np.cross(b - a, c - a); area = np.linalg.norm(n, axis=1) / 2; nz = n[:, 2] / np.maximum(np.linalg.norm(n, axis=1), 1e-12)
    down = nz < -0.999; zc = (a[:, 2] + b[:, 2] + c[:, 2]) / 3
    return {"g_bottom_down": float(area[down].sum()), "g_bottom_minz": float(area[down & (zc < v[:, 2].min() + 0.001)].sum())}
def geo(e):
    try:
        g = ifcopenshell.geom.create_shape(st, e).geometry
        return {"g_footprint": us.get_footprint_area(g), "g_volume": us.get_volume(g), "g_side": us.get_side_area(g),
                "g_maxside": us.get_max_side_area(g), "g_area": us.get_area(g), "g_top": us.get_top_area(g), **bottom_areas(g)}
    except Exception as ex:
        return {"g_err": str(ex)[:80]}
classes = ["IfcSpace","IfcDoor","IfcWindow","IfcWall","IfcColumn","IfcBeam","IfcStair","IfcSlab","IfcFlowTerminal","IfcRailing","IfcStairFlight","IfcRoof","IfcCovering","IfcBuildingElementProxy","IfcMember","IfcPlate","IfcCurtainWall"]
els = []
for cls in classes:
    for e in f.by_type(cls):  # includes subtypes
        ps = ue.get_psets(e)
        d = {"cls": cls, "ifc_class": e.is_a(), "gid": e.GlobalId, "Name": e.Name, "LongName": getattr(e, "LongName", None),
             "storey": storey_of(e), "direct_container": (ue.get_container(e, should_get_direct=True).is_a() if ue.get_container(e, should_get_direct=True) else None),
             "parent": (ue.get_aggregate(e).is_a() if ue.get_aggregate(e) else None),
             "type": (ue.get_type(e).is_a() if ue.get_type(e) else None), "type_name": (ue.get_type(e).Name if ue.get_type(e) else None),
             "predef": getattr(e, "PredefinedType", None), "objtype": getattr(e, "ObjectType", None)}
        for qn in ["BaseQuantities", "ArchiCADQuantities", "Qto_SpaceBaseQuantities", "Qto_WallBaseQuantities", "Qto_SlabBaseQuantities", "Component Quantities", "AR_Ruum"]:
            for k, v in (ps.get(qn) or {}).items():
                if k != "id": d[f"{qn}.{k}"] = v
        if cls in ("IfcSpace", "IfcWall", "IfcSlab") and "--nogeo" not in sys.argv: d.update(geo(e))
        els.append(d)
pickle.dump({"model": model, "storeys": [(s.Name, s.Elevation) for s in f.by_type("IfcBuildingStorey")], "els": els}, open(f"facts_{model}.pkl", "wb"))
print(model, len(els), "elements", round(time.time() - t0, 1), "s")

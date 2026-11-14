import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Build a per-space table for each IFC: storey, labels, pset/qto areas, geometric areas (footprint, brep bottom, FootPrint curve).
import sys, time, json
import numpy as np, pandas as pd, shapely.geometry as sg, shapely.ops as so
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue, ifcopenshell.util.shape as us, ifcopenshell.util.placement as up
DS = _DATA + "/data/ifc_models/"
model = sys.argv[1]
f = ifcopenshell.open(DS + model + ".ifc")
st = ifcopenshell.geom.settings()
st.set("use-world-coords", True)
def storey_of(e):
    c = ue.get_container(e)
    if c is None:
        a = ue.get_aggregate(e)
        while a is not None and not a.is_a("IfcBuildingStorey"): a = ue.get_aggregate(a) or ue.get_container(a)
        c = a
    return c.Name if c is not None else None
def num(v):
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    try: return float(str(v).replace(",", ".").strip())
    except Exception: return None
def footprint_curve_area(s):
    # area of polygon from FootPrint GeometricCurveSet (in local coords, mm -> m2)
    if not s.Representation: return None
    for r in s.Representation.Representations:
        if r.RepresentationIdentifier == "FootPrint":
            polys = []
            for it in r.Items:
                for el in getattr(it, "Elements", []) or []:
                    pts = None
                    if el.is_a("IfcPolyline"): pts = [p.Coordinates[:2] for p in el.Points]
                    if pts and len(pts) >= 3: polys.append(sg.Polygon(pts))
            if not polys: return None
            # shortcut: outer minus holes via symmetric difference, good enough for simple footprints
            a = polys[0]
            for p in polys[1:]: a = a.symmetric_difference(p)
            return a.area * 1e-6
    return None
rows = []
t0 = time.time()
for s in f.by_type("IfcSpace"):
    ps = ue.get_psets(s)
    r = {"gid": s.GlobalId, "storey": storey_of(s), "Name": s.Name, "LongName": s.LongName, "label": f"{s.LongName} ({s.Name})"}
    bq = ps.get("BaseQuantities", {})
    for k in ["NetFloorArea", "GrossFloorArea", "NetVolume", "GrossVolume", "Height"]: r["bq_" + k] = num(bq.get(k))
    aq = ps.get("ArchiCADQuantities", {})
    for k in ["Area", "Measured Net Area", "Calculated Area", "Reduced Area"]: r["ac_" + k] = num(aq.get(k))
    ar = ps.get("AR_Ruum", {})
    r["ar_pindala"] = num(ar.get("120_Pindala"))
    r["fp_curve_area"] = footprint_curve_area(s)
    try:
        sh = ifcopenshell.geom.create_shape(st, s)
        g = sh.geometry
        r["geo_footprint"] = us.get_footprint_area(g)
        r["geo_top"] = us.get_top_area(g)
        r["geo_area_total"] = us.get_area(g)
        r["geo_volume"] = us.get_volume(g)
        z = us.get_vertices(g)[:, 2]
        r["zmin"], r["zmax"] = float(z.min()), float(z.max())
    except Exception as e:
        r["geo_err"] = str(e)[:100]
    rows.append(r)
df = pd.DataFrame(rows)
df.to_csv(f"spaces_{model}.csv", index=False)
print(model, len(df), "spaces", round(time.time() - t0, 1), "s")
print(df.head(10).to_string())

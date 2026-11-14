# Per-IFC inventory: schema, size, load time, peak memory, entity counts, storeys, units, psets/qsets.
import sys, os, time, resource, json, collections
import ifcopenshell, ifcopenshell.util.element as ue, ifcopenshell.util.unit as uu
p = sys.argv[1]
t0 = time.time(); f = ifcopenshell.open(p); t_load = time.time() - t0
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6  # macOS: bytes -> MB
out = {"file": os.path.basename(p), "bytes": os.path.getsize(p), "schema": f.schema, "load_s": round(t_load, 2), "peak_rss_mb_after_load": round(rss, 1)}
out["n_entities"] = len(list(f))
types = ["IfcProject","IfcSite","IfcBuilding","IfcBuildingStorey","IfcSpace","IfcZone","IfcDoor","IfcWindow","IfcWall","IfcWallStandardCase","IfcCurtainWall",
         "IfcSlab","IfcRoof","IfcColumn","IfcBeam","IfcStair","IfcStairFlight","IfcRamp","IfcRailing","IfcCovering","IfcMember","IfcPlate","IfcFooting",
         "IfcFurnishingElement","IfcBuildingElementProxy","IfcOpeningElement","IfcFlowTerminal","IfcSanitaryTerminalType","IfcFlowSegment","IfcFlowFitting",
         "IfcDistributionElement","IfcAnnotation","IfcGrid","IfcElementQuantity","IfcPropertySet","IfcRelSpaceBoundary","IfcRelContainedInSpatialStructure","IfcRelAggregates"]
cnt = {}
for t in types:
    try: cnt[t] = len(f.by_type(t, include_subtypes=False))
    except Exception: cnt[t] = None
cnt["IfcWall+subtypes"] = len(f.by_type("IfcWall"))
cnt["IfcElement(all)"] = len(f.by_type("IfcElement"))
out["counts"] = cnt
# units
out["units"] = {}
for u in f.by_type("IfcUnitAssignment")[0].Units:
    if u.is_a("IfcSIUnit"): out["units"][u.UnitType] = f"{u.Prefix or ''}{u.Name}"
    elif u.is_a("IfcConversionBasedUnit"): out["units"][u.UnitType] = u.Name
out["length_unit_scale_to_m"] = uu.calculate_unit_scale(f)
# storeys
st = []
for s in f.by_type("IfcBuildingStorey"):
    contained = [e for r in (s.ContainsElements or []) for e in r.RelatedElements]
    agg = [e for r in (s.IsDecomposedBy or []) for e in r.RelatedObjects]
    tc = collections.Counter(e.is_a() for e in contained + agg)
    st.append({"name": s.Name, "longname": s.LongName, "elev": s.Elevation, "n_contained": len(contained), "n_aggregated": len(agg), "types": dict(tc.most_common(12))})
out["storeys"] = st
# pset/qset names on spaces and walls/slabs
def pset_names(ents, n=200):
    c = collections.Counter()
    for e in ents[:n]:
        for k in ue.get_psets(e).keys(): c[k] += 1
    return dict(c.most_common(40))
for t in ["IfcSpace","IfcWall","IfcSlab","IfcDoor","IfcWindow"]:
    out[f"psets_{t}"] = pset_names(f.by_type(t))
qn = collections.Counter(q.Name for q in f.by_type("IfcElementQuantity"))
out["IfcElementQuantity_names"] = dict(qn.most_common(30))
out["peak_rss_mb_end"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 1)
print(json.dumps(out, indent=1, ensure_ascii=False, default=str))

import sys, time, collections
import ifcopenshell, ifcopenshell.util.element as ue
p = sys.argv[1]
t = time.time(); f = ifcopenshell.open(p); print("loaded", round(time.time()-t, 1), "s", f.schema)
for e in ["IfcProject", "IfcBuilding", "IfcBuildingStorey", "IfcSpace", "IfcDoor", "IfcWindow", "IfcWall", "IfcWallStandardCase", "IfcColumn", "IfcBeam", "IfcStair", "IfcStairFlight", "IfcSlab", "IfcFlowTerminal", "IfcSanitaryTerminal", "IfcCovering", "IfcRailing", "IfcMember", "IfcPlate", "IfcCurtainWall", "IfcBuildingElementProxy"]:
    try: n = len(f.by_type(e)); print(f"  {e}: {n}  (exact class {sum(1 for x in f.by_type(e) if x.is_a() == e)})")
    except Exception as ex: print("  ", e, "ERR", ex)
print([ (x.Name, x.LongName) for x in f.by_type("IfcProject")], [(x.Name, x.LongName) for x in f.by_type("IfcBuilding")])
for s in f.by_type("IfcBuildingStorey"):
    agg = [o for r in (s.IsDecomposedBy or []) for o in r.RelatedObjects]
    cont = [o for r in (s.ContainsElements or []) for o in r.RelatedElements]
    print("STOREY", repr(s.Name), repr(s.LongName), s.Elevation, "agg:", collections.Counter(o.is_a() for o in agg).most_common(4), "cont:", collections.Counter(o.is_a() for o in cont).most_common(8))
sp = f.by_type("IfcSpace")
for x in sp[:3]:
    print("SPACE", repr(x.Name), repr(x.LongName))
    for k, v in ue.get_psets(x).items(): print("    ", k, {kk: vv for kk, vv in v.items() if kk != "id"})

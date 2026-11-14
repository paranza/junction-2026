"""IFC probe: schema, authoring tool, units, storeys, element counts, spaces with quantities.
Usage: python -I ifc_probe.py <dataset_dir>"""
import sys, os, collections
import ifcopenshell
import ifcopenshell.util.element as ue
import ifcopenshell.util.unit as uu

D = sys.argv[1]
root = os.path.join(D, "data", "opening_design")
TYPES = ["IfcBuildingStorey", "IfcSpace", "IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcDoor", "IfcWindow",
         "IfcStair", "IfcRoof", "IfcColumn", "IfcBeam", "IfcMember", "IfcPlate", "IfcRailing", "IfcCovering",
         "IfcFurnishingElement", "IfcFlowTerminal", "IfcBuildingElementProxy", "IfcAnnotation", "IfcGrid"]
for dp, _, fs in sorted(os.walk(root)):
    for f in sorted(fs):
        if not f.lower().endswith(".ifc"):
            continue
        full = os.path.join(dp, f)
        m = ifcopenshell.open(full)
        hdr = m.header
        try:
            app = hdr.file_name.originating_system
            auth = hdr.file_name.preprocessor_version
        except Exception:
            app = auth = "?"
        print("=" * 100)
        print(os.path.relpath(full, root), f"| {os.path.getsize(full)/1e6:.1f} MB | schema {m.schema} | {app} | {auth}")
        try:
            lu = uu.get_project_unit(m, "LENGTHUNIT")
            print("   length unit:", lu.Prefix if hasattr(lu, "Prefix") else "", lu.Name if hasattr(lu, "Name") else lu)
        except Exception as e:
            print("   length unit: ?", e)
        c = {t: len(m.by_type(t, include_subtypes=False)) for t in TYPES}
        print("   counts:", {k: v for k, v in c.items() if v})
        print("   total entities:", len(list(m)), "| products:", len(m.by_type("IfcProduct")))
        for s in m.by_type("IfcBuildingStorey"):
            n = sum(len(r.RelatedElements) for r in s.ContainsElements) if s.ContainsElements else 0
            print(f"   storey {s.Name!r} elev={s.Elevation} contained={n}")
        sp = m.by_type("IfcSpace")
        for s in sp[:15]:
            q = ue.get_psets(s, qtos_only=True)
            areas = {k2: round(v2, 2) for qn, qs in q.items() for k2, v2 in qs.items() if "Area" in k2 and isinstance(v2, float)}
            print(f"   space {s.Name!r} {s.LongName!r} {areas}")
        names = collections.Counter((e.is_a(), (e.Name or "")[:30]) for e in m.by_type("IfcProduct")
                                    if e.is_a() not in ("IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace", "IfcOpeningElement"))
        print("   top product names:", names.most_common(12))
        props = collections.Counter(p.Name for p in m.by_type("IfcPropertySet"))
        print("   property sets:", props.most_common(8))

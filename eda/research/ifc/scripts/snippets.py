import sys
import ifcopenshell
import ifcopenshell.util.unit as uu
import ifcopenshell.util.element as ue
import ifcopenshell.util.selector as sel

# 1. Open + unit scales (project unit -> SI)
model = ifcopenshell.open(sys.argv[1])
print("schema", model.schema)
L = uu.calculate_unit_scale(model)               # LENGTHUNIT by default: mm -> 0.001
A = uu.calculate_unit_scale(model, "AREAUNIT")    # area has its own unit; do not use L**2
V = uu.calculate_unit_scale(model, "VOLUMEUNIT")
print("scales L A V", L, A, V)

# 2. Spaces per storey (spaces hang under storeys via IfcRelAggregates, not containment)
def qto_value(el, name):
    for qset in ue.get_psets(el, qtos_only=True).values():   # e.g. 'BaseQuantities' (IFC2X3 exporters) or 'Qto_SpaceBaseQuantities'
        if name in qset:
            return qset[name]
    return None

for storey in model.by_type("IfcBuildingStorey"):
    spaces = [e for e in ue.get_decomposition(storey) if e.is_a("IfcSpace")]
    for sp in spaces:
        nfa = qto_value(sp, "NetFloorArea")
        print(storey.Name, "|", sp.Name, "|", sp.LongName, "|", None if nfa is None else nfa * A)
print("get_contained(storey) has spaces?", any(e.is_a("IfcSpace") for e in ue.get_contained(model.by_type("IfcBuildingStorey")[0])))
print("get_parts(storey):", [e.Name for e in ue.get_parts(model.by_type("IfcBuildingStorey")[0])])
print("get_container(space):", [ (sp.Name, getattr(ue.get_container(sp), "Name", None)) for sp in model.by_type("IfcSpace")])
print("get_aggregate(space):", [ (sp.Name, getattr(ue.get_aggregate(sp), "Name", None)) for sp in model.by_type("IfcSpace")])

# 3. Count a class (by_type includes subtypes, e.g. IfcWallStandardCase is an IfcWall) per storey
def count_in_storey(model, storey, ifc_class):
    return sum(1 for e in model.by_type(ifc_class)
               if ue.get_container(e, ifc_class="IfcBuildingStorey") == storey)
for st in model.by_type("IfcBuildingStorey"):
    print(st.Name, "walls", count_in_storey(model, st, "IfcWall"), "doors", count_in_storey(model, st, "IfcDoor"),
          "| direct-only doors", sum(1 for e in ue.get_contained(st) if e.is_a("IfcDoor")))
print("by_type IfcWall include_subtypes=False:", len(model.by_type("IfcWall", include_subtypes=False)), "vs", len(model.by_type("IfcWall")))

# 4. Type name and material
w = [e for e in model.by_type("IfcWall") if e.Name == "W1"][0]
t = ue.get_type(w)
print("type", t.is_a() if t else None, t.Name if t else None)
mat = ue.get_material(w)                       # may be a usage, a set or a single IfcMaterial
print("material", mat.is_a() if mat else None, [m.Name for m in ue.get_materials(w)])
print("psets W1", ue.get_psets(w, psets_only=True))
print("qtos W1", ue.get_psets(w, qtos_only=True))
print("sum NetVolume m3", sum((qto_value(e, "NetVolume") or 0) for e in model.by_type("IfcWall")) * V)
print("sum Length m", sum((qto_value(e, "Length") or 0) for e in model.by_type("IfcWall")) * L)

# 5. Selector
for q in ['IfcWall, location="Level 1"', 'IfcWall, Pset_WallCommon.IsExternal=TRUE', 'IfcWall, type=WT01', 'IfcWall, material=Concrete', 'IfcDoor, location="Level 1"', 'IfcSpace, LongName=/Kit.*/']:
    print(repr(q), sorted(e.Name for e in sel.filter_elements(model, q)))
print("get_element_value", sel.get_element_value(w, "type.Name"), sel.get_element_value(w, "Pset_WallCommon.IsExternal"))

# 6. Geometry: create_shape output units + util.shape helpers
import ifcopenshell.geom, ifcopenshell.util.shape as us
s = ifcopenshell.geom.settings()
shape = ifcopenshell.geom.create_shape(s, w)
g = shape.geometry
print("volume", us.get_volume(g), "footprint", us.get_footprint_area(g), "side", us.get_side_area(g, axis="Y"), "max side", us.get_max_side_area(g))
print("settings use-world-coords", s.get("use-world-coords"), "convert-back-units", s.get("convert-back-units"))

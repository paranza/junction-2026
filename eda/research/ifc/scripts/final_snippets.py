import sys
# --- 1. open + unit scales
import ifcopenshell
import ifcopenshell.util.unit as uu

model = ifcopenshell.open(sys.argv[1])
print(model.schema)                                  # 'IFC2X3' for the ifc_models split
L = uu.calculate_unit_scale(model)                   # LENGTHUNIT is the default: mm project -> 0.001
A = uu.calculate_unit_scale(model, "AREAUNIT")       # separate unit, often m2 (1.0) in mm projects: never use L**2
V = uu.calculate_unit_scale(model, "VOLUMEUNIT")
# project_value * scale = SI value (m, m2, m3)
print(L, A, V)

# --- 2. spaces per storey
import ifcopenshell.util.element as ue

def qto_value(el, name):
    # {set_name: {quantity: value, ..., "id": step_id}}; IFC2X3 exporters usually call the set "BaseQuantities"
    for qset in ue.get_psets(el, qtos_only=True).values():
        if name in qset:
            return qset[name]
    return None

for storey in model.by_type("IfcBuildingStorey"):
    # spaces hang under the storey via IfcRelAggregates: get_contained(storey) does not return them
    for sp in (e for e in ue.get_decomposition(storey) if e.is_a("IfcSpace")):
        nfa = qto_value(sp, "NetFloorArea")
        print(storey.Name, sp.Name, sp.LongName, None if nfa is None else nfa * A)

# --- 3. count a class (with subtypes) per storey
def count_in_storey(model, storey, ifc_class):
    # by_type includes subtypes (IfcWallStandardCase is an IfcWall);
    # get_container(ifc_class=...) walks up from spaces and aggregates to the storey
    return sum(1 for e in model.by_type(ifc_class)
               if ue.get_container(e, ifc_class="IfcBuildingStorey") == storey)

for storey in model.by_type("IfcBuildingStorey"):
    direct = sum(1 for e in ue.get_contained(storey) if e.is_a("IfcDoor"))  # direct containment only
    print(storey.Name, count_in_storey(model, storey, "IfcDoor"), direct)

# --- 4. type name and material
wall = model.by_type("IfcWall")[0]
t = ue.get_type(wall)                                # IfcRelDefinesByType (IFC2X3: IsDefinedBy, IFC4: IsTypedBy)
print(t.Name if t else None)
mat = ue.get_material(wall)                          # IfcMaterial, a set, or a *Usage (e.g. IfcMaterialLayerSetUsage)
print(mat.is_a() if mat else None, [m.Name for m in ue.get_materials(wall)])  # individual IfcMaterial names

# --- 5. selector
import ifcopenshell.util.selector as sel
ext_l1 = sel.filter_elements(model, 'IfcWall, Pset_WallCommon.IsExternal=TRUE, location="Level 1"')
print(len(ext_l1), sel.get_element_value(wall, "type.Name"), sel.get_element_value(wall, "storey.Name"))

# --- 6. geometry fallback (output is in metres regardless of project units)
import ifcopenshell.geom
import ifcopenshell.util.shape as us
settings = ifcopenshell.geom.settings()
for el in model.by_type("IfcWall"):
    try:
        shape = ifcopenshell.geom.create_shape(settings, el)   # openings applied by default
    except RuntimeError as e:                                  # e.g. "No suitable IfcRepresentation found"
        print(el.Name, "no geometry:", e)
        continue
    print(el.Name, us.get_footprint_area(shape.geometry), us.get_volume(shape.geometry))  # plan area m2, volume m3

# Runs the reading-list snippets verbatim on the synthetic model, then probes edge cases.
import sys, traceback
path = sys.argv[1]
def section(t): print("\n#####", t)
# ---- snippet 1 (verbatim, file name swapped)
section("1 units")
import ifcopenshell
import ifcopenshell.util.unit as uu
model = ifcopenshell.open(path)
print(model.schema)
L = uu.calculate_unit_scale(model)
A = uu.calculate_unit_scale(model, "AREAUNIT")
V = uu.calculate_unit_scale(model, "VOLUMEUNIT")
print(L, A, V)
# ---- snippet 2 (verbatim)
section("2 spaces per storey")
import ifcopenshell.util.element as ue
def qto_value(el, name):
    for qset in ue.get_psets(el, qtos_only=True).values():
        if name in qset:
            return qset[name]
    return None
for storey in model.by_type("IfcBuildingStorey"):
    for sp in (e for e in ue.get_decomposition(storey) if e.is_a("IfcSpace")):
        nfa = qto_value(sp, "NetFloorArea")
        print(storey.Name, sp.Name, sp.LongName, None if nfa is None else nfa * A)
sp = model.by_type("IfcSpace")[0]
print("all qto sets on space:", ue.get_psets(sp, qtos_only=True))
print("get_container(space):", ue.get_container(sp), "| with ifc_class:", ue.get_container(sp, ifc_class="IfcBuildingStorey"), "| get_aggregate:", ue.get_aggregate(sp).Name)
# ---- snippet 3 (verbatim)
section("3 counts per storey")
def count_in_storey(model, storey, ifc_class):
    return sum(1 for e in model.by_type(ifc_class)
               if ue.get_container(e, ifc_class="IfcBuildingStorey") == storey)
for storey in model.by_type("IfcBuildingStorey"):
    for cls in ("IfcDoor", "IfcWall", "IfcSlab", "IfcWindow"):
        direct = sum(1 for e in ue.get_contained(storey) if e.is_a(cls))
        print(storey.Name, cls, "walkup:", count_in_storey(model, storey, cls), "direct:", direct)
print("get_decomposition(L2) classes:", sorted(e.is_a() for e in ue.get_decomposition(model.by_type("IfcBuildingStorey")[1])))
# ---- snippet 4 (verbatim, wall defined)
section("4 type and material")
wall = model.by_type("IfcWall")[0]
t = ue.get_type(wall)
type_name = t.Name if t else None
mat = ue.get_material(wall)
material_names = [m.Name for m in ue.get_materials(wall)]
print(wall.is_a(), type_name, mat.is_a() if mat else None, material_names)
print("get_material(should_skip_usage=True):", ue.get_material(wall, should_skip_usage=True).is_a())
# ---- snippet 5 (verbatim)
section("5 selector")
import ifcopenshell.util.selector as sel
ext_l1 = sel.filter_elements(model, 'IfcWall, Pset_WallCommon.IsExternal=TRUE, location="Level 1"')
n = len(ext_l1)
print("n ext walls L1:", n, type(ext_l1).__name__)
print("type.Name:", sel.get_element_value(wall, "type.Name"))
print("storey.Name:", sel.get_element_value(wall, "storey.Name"))
door = model.by_type("IfcDoor")[0]
print("door storey.Name:", sel.get_element_value(door, "storey.Name"), "| container.Name:", sel.get_element_value(door, "container.Name"))
print("union:", sorted(e.Name for e in sel.filter_elements(model, 'IfcWall, location="Level 1" + IfcDoor')))
print("IfcWall, IfcSlab (OR?):", sorted(e.Name for e in sel.filter_elements(model, 'IfcWall, IfcSlab')))
print("IfcDoor, location=Level 1 (door in space):", [e.Name for e in sel.filter_elements(model, 'IfcDoor, location="Level 1"')])
print("IfcSlab, location=Level 2 (roof parts?):", sorted(e.Name for e in sel.filter_elements(model, 'IfcSlab, location="Level 2"')))
for q in ['material.Name', 'material.item.0.Name', 'materials.count', 'mats.0.Name']:
    try: print(q, "->", sel.get_element_value(wall, q))
    except Exception as e: print(q, "ERROR", e)
for f in ['IfcElement, query:"parent.Name"="Level 1"', 'IfcWall /* + IfcSlab */']:
    try: print(f, "->", sorted(e.Name for e in sel.filter_elements(model, f)))
    except Exception as e: print(f, "ERROR", type(e).__name__, e)
# ---- snippet 6 (verbatim)
section("6 geometry")
import ifcopenshell.geom
import ifcopenshell.util.shape as us
settings = ifcopenshell.geom.settings()
for el in model.by_type("IfcWall"):
    try:
        shape = ifcopenshell.geom.create_shape(settings, el)
    except RuntimeError as e:
        print(el.Name, "no geometry:", e)
        continue
    print(el.Name, us.get_footprint_area(shape.geometry), us.get_volume(shape.geometry))
s = ifcopenshell.geom.create_shape(settings, sp)
print("space footprint m2:", us.get_footprint_area(s.geometry), "get_area (total surface):", us.get_area(s.geometry))
try:
    s2 = ifcopenshell.geom.create_shape(settings, wall, geometry_library="hybrid-cgal-simple-opencascade")
    print("hybrid kernel volume:", us.get_volume(s2.geometry))
except Exception as e: print("hybrid kernel ERROR", type(e).__name__, e)
import multiprocessing
it = ifcopenshell.geom.iterator(settings, model, multiprocessing.cpu_count())
seen = []
if it.initialize():
    while True:
        seen.append(model.by_id(it.get().id).is_a())
        if not it.next(): break
print("default iterator processed:", seen)
# ---- extra traps
section("extra")
try: model.by_type("IfcDoorType")
except Exception as e: print("by_type('IfcDoorType') on IFC2X3:", type(e).__name__, e)
print("IfcDoorStyle count:", len(model.by_type("IfcDoorStyle")))
print("include_subtypes=False IfcWall:", len(model.by_type("IfcWall", include_subtypes=False)), "vs", len(model.by_type("IfcWall")))
try: uu.calculate_unit_scale(model, "AREA")
except Exception as e: print("bad unit_type:", type(e).__name__, e)
print("has svg serializer:", hasattr(ifcopenshell.geom, "serializers") and hasattr(ifcopenshell.geom.serializers, "svg"))

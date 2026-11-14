# Corrected snippet 2 plus IFC2X3 selector checks, run on the synthetic model.
import sys, ifcopenshell, ifcopenshell.util.element as ue, ifcopenshell.util.unit as uu, ifcopenshell.util.selector as sel
model = ifcopenshell.open(sys.argv[1])
A = uu.calculate_unit_scale(model, "AREAUNIT")

def qto_value(el, name, prefer=("BaseQuantities", "Qto_SpaceBaseQuantities")):
    # {set_name: {quantity: value, ..., "id": step_id}}; type sets are merged in (should_inherit=True)
    hits = {s: q[name] for s, q in ue.get_psets(el, qtos_only=True).items() if name in q}
    if len(set(hits.values())) > 1:
        print("  qto conflict on", el.GlobalId, hits)  # check against reference answers which set wins
    for s in prefer:
        if s in hits:
            return hits[s]
    return next(iter(hits.values()), None)

for storey in model.by_type("IfcBuildingStorey"):
    for sp in (e for e in ue.get_decomposition(storey) if e.is_a("IfcSpace")):
        nfa = qto_value(sp, "NetFloorArea")
        print(storey.Name, sp.Name, sp.LongName, None if nfa is None else nfa * A)

assert qto_value(model.by_type("IfcSpace")[0], "NetFloorArea") == 19.5
sp = model.by_type("IfcSpace")[0]
print("space storey via selector:", sel.get_element_value(sp, "storey.Name"), "| parent.Name:", sel.get_element_value(sp, "parent.Name"))
w1 = [w for w in model.by_type("IfcWall") if w.Name == "W1"][0]
print("IFC2X3 layer material:", sel.get_element_value(w1, "material.item.0.Material.Name"), "| material.item.0.Name:", sel.get_element_value(w1, "material.item.0.Name"))
print("slabs on Level 2, direct only:", [e.Name for e in sel.filter_elements(model, 'IfcSlab, query:"container.Name"="Level 2"')])

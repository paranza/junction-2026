import sys, multiprocessing
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.shape as us
model = ifcopenshell.open(sys.argv[1])
settings = ifcopenshell.geom.settings()
it = ifcopenshell.geom.iterator(settings, model, multiprocessing.cpu_count(), include=model.by_type("IfcWall"))
n = 0
if it.initialize():
    while True:
        shape = it.get()
        el = model.by_id(shape.id)
        print(el.is_a(), el.Name, shape.guid == el.GlobalId, "vol m3", round(us.get_volume(shape.geometry), 6), "footprint m2", round(us.get_footprint_area(shape.geometry), 6))
        n += 1
        if not it.next():
            break
print("shapes", n)

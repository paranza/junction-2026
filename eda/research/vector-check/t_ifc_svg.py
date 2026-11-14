# Synthetic IFC2X3 (one storey, 2 walls, 1 slab-free space) -> SVG via ifcopenshell.draw, then run svg_elements on it.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ifcopenshell, numpy as np
import ifcopenshell.api as api
import ifcopenshell.api.project, ifcopenshell.api.root, ifcopenshell.api.unit, ifcopenshell.api.context, ifcopenshell.api.aggregate, ifcopenshell.api.geometry, ifcopenshell.api.spatial
FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fx")
f = api.project.create_file(version="IFC4")
proj = api.root.create_entity(f, ifc_class="IfcProject", name="P")
api.unit.assign_unit(f)
model = api.context.add_context(f, context_type="Model")
body = api.context.add_context(f, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model)
site = api.root.create_entity(f, ifc_class="IfcSite"); bldg = api.root.create_entity(f, ifc_class="IfcBuilding"); st = api.root.create_entity(f, ifc_class="IfcBuildingStorey", name="L0")
st.Elevation = 0.0
for o in (site, bldg, st): api.geometry.edit_object_placement(f, product=o)
api.aggregate.assign_object(f, products=[site], relating_object=proj); api.aggregate.assign_object(f, products=[bldg], relating_object=site); api.aggregate.assign_object(f, products=[st], relating_object=bldg)
for i, (x, y, ang) in enumerate([(0, 0, 0), (0, 0, 90)]):
    w = api.root.create_entity(f, ifc_class="IfcWall", name=f"W{i}")
    rep = api.geometry.add_wall_representation(f, context=body, length=5, height=3, thickness=0.2)
    api.geometry.assign_representation(f, product=w, representation=rep)
    m = np.eye(4); a = np.radians(ang); m[:2, :2] = [[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]
    api.geometry.edit_object_placement(f, product=w, matrix=m)
    api.spatial.assign_container(f, products=[w], relating_structure=st)
sp = api.root.create_entity(f, ifc_class="IfcSpace", name="101"); sp.LongName = "Kitchen"
rep = api.geometry.add_slab_representation(f, context=body, depth=2.5, polyline=[(0.2, 0.2), (4, 0.2), (4, 3), (0.2, 3)])
api.geometry.assign_representation(f, product=sp, representation=rep)
api.aggregate.assign_object(f, products=[sp], relating_object=st)
f.write(f"{FX}/syn.ifc")
import ifcopenshell.draw as draw
s = draw.draw_settings(auto_floorplan=True, scale=1 / 100, space_names=True, space_areas=True, door_arcs=True)
svg = draw.main(s, [f])
open(f"{FX}/syn.svg", "wb").write(svg if isinstance(svg, bytes) else svg.encode())
print("svg bytes", len(svg))

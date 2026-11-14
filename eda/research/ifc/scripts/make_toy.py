# Builds a tiny synthetic IFC2X3 model (no dataset content) to check the snippets.
import sys
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.api.project, ifcopenshell.api.root, ifcopenshell.api.unit, ifcopenshell.api.context, ifcopenshell.api.aggregate, ifcopenshell.api.pset, ifcopenshell.api.material, ifcopenshell.api.type, ifcopenshell.api.spatial, ifcopenshell.api.geometry

m = api.project.create_file(version="IFC2X3")
import ifcopenshell.api.owner, ifcopenshell.api.owner.settings
_u = api.owner.add_person_and_organisation(m, person=api.owner.add_person(m), organisation=api.owner.add_organisation(m))
_a = api.owner.add_application(m)
ifcopenshell.api.owner.settings.get_user = lambda f: _u  # IFC2X3 needs OwnerHistory
ifcopenshell.api.owner.settings.get_application = lambda f: _a
proj = api.root.create_entity(m, ifc_class="IfcProject", name="Toy")
mm = api.unit.add_si_unit(m, unit_type="LENGTHUNIT", prefix="MILLI")
m2 = api.unit.add_si_unit(m, unit_type="AREAUNIT")
m3 = api.unit.add_si_unit(m, unit_type="VOLUMEUNIT")
api.unit.assign_unit(m, units=[mm, m2, m3])
model3d = api.context.add_context(m, context_type="Model")
body = api.context.add_context(m, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d)

site = api.root.create_entity(m, ifc_class="IfcSite", name="Site")
bldg = api.root.create_entity(m, ifc_class="IfcBuilding", name="B")
s1 = api.root.create_entity(m, ifc_class="IfcBuildingStorey", name="Level 1")
s2 = api.root.create_entity(m, ifc_class="IfcBuildingStorey", name="Level 2")
api.aggregate.assign_object(m, products=[site], relating_object=proj)
api.aggregate.assign_object(m, products=[bldg], relating_object=site)
api.aggregate.assign_object(m, products=[s1, s2], relating_object=bldg)

# Spaces are aggregated (IfcRelAggregates) under storeys, not contained.
sp1 = api.root.create_entity(m, ifc_class="IfcSpace", name="101")
sp1.LongName = "Kitchen"
sp2 = api.root.create_entity(m, ifc_class="IfcSpace", name="102")
sp2.LongName = "Bath"
api.aggregate.assign_object(m, products=[sp1, sp2], relating_object=s1)
q = api.pset.add_qto(m, product=sp1, name="BaseQuantities")  # IFC2X3 exporters often use this name
api.pset.edit_qto(m, qto=q, properties={"NetFloorArea": 12.5, "GrossFloorArea": 13.0})
q = api.pset.add_qto(m, product=sp2, name="Qto_SpaceBaseQuantities")
api.pset.edit_qto(m, qto=q, properties={"NetFloorArea": 4.25})

wt = api.root.create_entity(m, ifc_class="IfcWallType", name="WT01")
ls = api.material.add_material_set(m, name="Wall200", set_type="IfcMaterialLayerSet")
conc = api.material.add_material(m, name="Concrete")  # IFC2X3 IfcMaterial has no Category
layer = api.material.add_layer(m, layer_set=ls, material=conc)
api.material.edit_layer(m, layer=layer, attributes={"LayerThickness": 200.0})
api.material.assign_material(m, products=[wt], type="IfcMaterialLayerSet", material=ls)

w1 = api.root.create_entity(m, ifc_class="IfcWallStandardCase", name="W1")
w2 = api.root.create_entity(m, ifc_class="IfcWall", name="W2")
w3 = api.root.create_entity(m, ifc_class="IfcWall", name="W3")
api.type.assign_type(m, related_objects=[w1, w2], relating_type=wt)
api.spatial.assign_container(m, products=[w1, w2], relating_structure=s1)
api.spatial.assign_container(m, products=[w3], relating_structure=s2)
api.geometry.edit_object_placement(m, product=w1)
rep = api.geometry.add_wall_representation(m, context=body, length=5.0, height=3.0, thickness=0.2)
api.geometry.assign_representation(m, product=w1, representation=rep)
q = api.pset.add_qto(m, product=w1, name="BaseQuantities")
api.pset.edit_qto(m, qto=q, properties={"Length": 5000.0, "NetSideArea": 15.0, "NetVolume": 3.0})

d1 = api.root.create_entity(m, ifc_class="IfcDoor", name="D01")
api.spatial.assign_container(m, products=[d1], relating_structure=sp1)  # door contained in a space
d2 = api.root.create_entity(m, ifc_class="IfcDoor", name="D02")
api.spatial.assign_container(m, products=[d2], relating_structure=s1)
api.pset.edit_pset(m, pset=api.pset.add_pset(m, product=w1, name="Pset_WallCommon"), properties={"IsExternal": True})
m.write(sys.argv[1])
print("wrote", sys.argv[1], m.schema)

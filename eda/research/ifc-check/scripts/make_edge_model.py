# Independent synthetic IFC2X3 model with edge cases (no dataset content).
import sys
import ifcopenshell, ifcopenshell.api as api
import ifcopenshell.api.project, ifcopenshell.api.root, ifcopenshell.api.unit, ifcopenshell.api.context, ifcopenshell.api.aggregate, ifcopenshell.api.pset, ifcopenshell.api.material, ifcopenshell.api.type, ifcopenshell.api.spatial, ifcopenshell.api.geometry
import ifcopenshell.api.owner, ifcopenshell.api.owner.settings
m = api.project.create_file(version="IFC2X3")
u = api.owner.add_person_and_organisation(m, person=api.owner.add_person(m), organisation=api.owner.add_organisation(m))
a = api.owner.add_application(m)
ifcopenshell.api.owner.settings.get_user = lambda f: u
ifcopenshell.api.owner.settings.get_application = lambda f: a
proj = api.root.create_entity(m, ifc_class="IfcProject", name="P")
api.unit.assign_unit(m, units=[api.unit.add_si_unit(m, unit_type="LENGTHUNIT", prefix="MILLI"),
                               api.unit.add_si_unit(m, unit_type="AREAUNIT"),
                               api.unit.add_si_unit(m, unit_type="VOLUMEUNIT")])
ctx = api.context.add_context(m, context_type="Model")
body = api.context.add_context(m, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=ctx)
site = api.root.create_entity(m, ifc_class="IfcSite", name="S")
bld = api.root.create_entity(m, ifc_class="IfcBuilding", name="B")
l1 = api.root.create_entity(m, ifc_class="IfcBuildingStorey", name="Level 1")
l2 = api.root.create_entity(m, ifc_class="IfcBuildingStorey", name="Level 2")
api.aggregate.assign_object(m, products=[site], relating_object=proj)
api.aggregate.assign_object(m, products=[bld], relating_object=site)
api.aggregate.assign_object(m, products=[l1, l2], relating_object=bld)
sp = api.root.create_entity(m, ifc_class="IfcSpace", name="101"); sp.LongName = "Office"
api.aggregate.assign_object(m, products=[sp], relating_object=l1)
# Space carries two qto sets with conflicting NetFloorArea (Qto_ set added first)
api.pset.edit_qto(m, qto=api.pset.add_qto(m, product=sp, name="Qto_SpaceBaseQuantities"), properties={"NetFloorArea": 20.0})
api.pset.edit_qto(m, qto=api.pset.add_qto(m, product=sp, name="BaseQuantities"), properties={"NetFloorArea": 19.5})
api.geometry.edit_object_placement(m, product=sp)
api.geometry.assign_representation(m, product=sp, representation=api.geometry.add_wall_representation(m, context=body, length=5.0, height=2.5, thickness=4.0))
# Wall type with material layer set; one standard-case wall with geometry
wt = api.root.create_entity(m, ifc_class="IfcWallType", name="WT01")
ls = api.material.add_material_set(m, name="LS200", set_type="IfcMaterialLayerSet")
api.material.edit_layer(m, layer=api.material.add_layer(m, layer_set=ls, material=api.material.add_material(m, name="Concrete")), attributes={"LayerThickness": 200.0})
api.material.assign_material(m, products=[wt], type="IfcMaterialLayerSet", material=ls)
w1 = api.root.create_entity(m, ifc_class="IfcWallStandardCase", name="W1")
w2 = api.root.create_entity(m, ifc_class="IfcWall", name="W2")
api.type.assign_type(m, related_objects=[w1, w2], relating_type=wt)
api.spatial.assign_container(m, products=[w1, w2], relating_structure=l1)
api.geometry.edit_object_placement(m, product=w1)
api.geometry.assign_representation(m, product=w1, representation=api.geometry.add_wall_representation(m, context=body, length=5.0, height=3.0, thickness=0.2))
api.pset.edit_qto(m, qto=api.pset.add_qto(m, product=w1, name="BaseQuantities"), properties={"Length": 5000.0, "NetSideArea": 15.0, "NetVolume": 3.0})
api.pset.edit_pset(m, pset=api.pset.add_pset(m, product=w1, name="Pset_WallCommon"), properties={"IsExternal": True})
# Door in the space (not the storey); window in storey
d1 = api.root.create_entity(m, ifc_class="IfcDoor", name="D01"); api.spatial.assign_container(m, products=[d1], relating_structure=sp)
win = api.root.create_entity(m, ifc_class="IfcWindow", name="WIN1"); api.spatial.assign_container(m, products=[win], relating_structure=l1)
# Roof aggregate on Level 2 with two slab parts that are NOT contained themselves
roof = api.root.create_entity(m, ifc_class="IfcRoof", name="R1"); api.spatial.assign_container(m, products=[roof], relating_structure=l2)
s1 = api.root.create_entity(m, ifc_class="IfcSlab", name="RS1"); s2 = api.root.create_entity(m, ifc_class="IfcSlab", name="RS2")
api.aggregate.assign_object(m, products=[s1, s2], relating_object=roof)
fl = api.root.create_entity(m, ifc_class="IfcSlab", name="FL2"); api.spatial.assign_container(m, products=[fl], relating_structure=l2)
m.write(sys.argv[1]); print("wrote", sys.argv[1], m.schema)

"""Source strings stay exact, and IFC queries do not require a PDF export."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from server import native_query,extraction,llm,store
from tests import test_backend_upgrade as fixture

class TextSourceOperations(unittest.TestCase):
 def plan(self,aggregate='lookup',**extra):
  return {'answerable':True,'object_type':'IfcDoor','object_ids':None,'filters':[],
          'aggregate':aggregate,'property':'properties.fire_rating','output_unit':None,'explanation':'Ignore this invented statement',**extra}
 def setUp(self):
  self.document={'objects':[{'id':'d1','type':'IfcDoor','label':'Door A','properties':{'fire_rating':'EI60','external':True}},
                            {'id':'d2','type':'IfcDoor','label':'Door B','properties':{'fire_rating':'EI30','external':False}},
                            {'id':'d3','type':'IfcDoor','label':'Door C','properties':{'fire_rating':'EI60','external':True}}]}
 def test_exact_lookup_and_unique_values(self):
  result=native_query.answer('What fire rating is recorded for Door A?',self.document,
      lambda *a,**k:self.plan(object_ids=['d1']))
  self.assertEqual(result['answer'],'EI60');self.assertIsNone(result['value'])
  self.assertEqual(result['evidence'][0]['quoted_text'],'EI60');self.assertTrue(result['evidence'][0]['source_verified'])
  result=native_query.answer('Which fire ratings occur in the source?',self.document,
      lambda *a,**k:self.plan('unique_values'))
  self.assertEqual(result['answer'],'EI60\nEI30');self.assertEqual(len(result['evidence']),3)
 def test_values_boolean_and_missing_fields(self):
  result=native_query.execute(self.plan('lookup',object_ids=['d2'],property='properties.external'),self.document)
  self.assertEqual(result['source_text'],'false')
  self.assertIsNone(native_query.execute(self.plan(),self.document))
  self.assertIsNone(native_query.execute(self.plan('values',property='properties.absent'),self.document))
  self.document['objects'][0]['properties']['fire_rating']=60
  self.assertIsNone(native_query.execute(self.plan(object_ids=['d1']),self.document))
 def test_text_cannot_bypass_numeric_intent(self):
  result=native_query.answer('How many doors have this rating?',self.document,
      lambda *a,**k:self.plan(object_ids=['d1']))
  self.assertIsNone(result)

class IfcWithoutDrawing(unittest.TestCase):
 setUp=fixture.BackendUpgrade.setUp
 tearDown=fixture.BackendUpgrade.tearDown
 def fixture_model(self):
  import ifcopenshell
  model=ifcopenshell.file(schema='IFC4')
  units=model.create_entity('IfcUnitAssignment',Units=[model.create_entity('IfcSIUnit',UnitType='LENGTHUNIT',Name='METRE')])
  model.create_entity('IfcProject',GlobalId=ifcopenshell.guid.new(),Name='Independent model',UnitsInContext=units)
  door=model.create_entity('IfcDoor',GlobalId=ifcopenshell.guid.new(),Name='Entry K42',OverallWidth=.9)
  values=[model.create_entity('IfcPropertySingleValue',Name='FireRating',NominalValue=model.create_entity('IfcLabel','EI60')),
          model.create_entity('IfcPropertySingleValue',Name='NetArea',NominalValue=model.create_entity('IfcReal',8.))]
  pset=model.create_entity('IfcPropertySet',GlobalId=ifcopenshell.guid.new(),Name='Pset_DoorCommon',HasProperties=values)
  model.create_entity('IfcRelDefinesByProperties',GlobalId=ifcopenshell.guid.new(),RelatedObjects=[door],RelatingPropertyDefinition=pset)
  path=self.runtime/'uploads'/'independent.ifc';model.write(path)
  return path,store.register(path,uploaded=True)
 def test_model_count_without_any_view_or_paid_request(self):
  path,doc=self.fixture_model()
  with patch.object(llm,'_request',side_effect=AssertionError('No model needed')):
   reply=self.client.post('/api/ask',json={'document_id':doc['id'],'question':'How many doors are in this model?','mode':'native'})
  self.assertEqual(reply.status_code,200,reply.text);self.assertEqual(reply.json()['value'],1)
  self.assertEqual(reply.json()['usage']['model_calls'],0)
  page=self.client.post('/api/ask',json={'document_id':doc['id'],'question':'How many doors?','mode':'native','scope':'page'})
  self.assertEqual(page.status_code,422)
 def test_opening_properties_are_retained_and_queried_as_text(self):
  path,doc=self.fixture_model();data=extraction.extract_document(path,self.data)
  door=next(o for o in data['objects'] if o['type']=='IfcDoor')
  self.assertEqual(door['properties']['property_sets']['Pset_DoorCommon']['FireRating'],'EI60')
  self.assertNotIn('net_area_m2',door['properties'])
  plan={'answerable':True,'object_type':'IfcDoor','object_ids':None,'filters':[],
        'aggregate':'lookup','property':'properties.property_sets.Pset_DoorCommon.FireRating',
        'output_unit':None,'explanation':'Source attribute'}
  with patch.object(llm,'model_available',return_value=True),patch.object(llm,'_request',return_value=plan):
   reply=self.client.post('/api/ask',json={'document_id':doc['id'],'question':'What fire rating is recorded for Entry K42?','mode':'auto'})
  self.assertEqual(reply.status_code,200,reply.text);self.assertEqual(reply.json()['answer'],'EI60')
  self.assertEqual(reply.json()['evidence'][0]['quoted_text'],'EI60')
 def test_wall_properties_material_layers_and_opening_dimensions_use_declared_units(self):
  import ifcopenshell
  path,_=self.fixture_model();model=ifcopenshell.open(path)
  project=model.by_type('IfcProject')[0]
  project.UnitsInContext.Units[0].Prefix='MILLI'
  door=model.by_type('IfcDoor')[0];door.OverallWidth=875.
  wall=model.create_entity('IfcWall',GlobalId=ifcopenshell.guid.new(),Name='Envelope W17')
  prop=model.create_entity('IfcPropertySingleValue',Name='AirTightness',NominalValue=model.create_entity('IfcLabel','Class C'))
  pset=model.create_entity('IfcPropertySet',GlobalId=ifcopenshell.guid.new(),Name='EnvelopeSpec',HasProperties=[prop])
  model.create_entity('IfcRelDefinesByProperties',GlobalId=ifcopenshell.guid.new(),RelatedObjects=[wall],RelatingPropertyDefinition=pset)
  materials=[model.create_entity('IfcMaterial',Name=name) for name in ['Brick','Insulation']]
  layers=[model.create_entity('IfcMaterialLayer',Material=material,LayerThickness=thickness) for material,thickness in zip(materials,[110.,70.])]
  layer_set=model.create_entity('IfcMaterialLayerSet',MaterialLayers=layers)
  model.create_entity('IfcRelAssociatesMaterial',GlobalId=ifcopenshell.guid.new(),RelatedObjects=[wall],RelatingMaterial=layer_set)
  model.write(path)
  data=extraction.extract_document(path,self.data)
  props=next(o['properties'] for o in data['objects'] if o['type']=='IfcWall')
  self.assertEqual(props['property_sets']['EnvelopeSpec']['AirTightness'],'Class C')
  self.assertEqual(props['material_names'],'Brick; Insulation');self.assertAlmostEqual(props['material_thickness_m'],.18)
  opening=next(o for o in data['objects'] if o['type']=='IfcDoor')
  self.assertAlmostEqual(opening['properties']['overall_width_m'],.875)
  plan={'answerable':True,'object_type':'IfcDoor','object_ids':None,'filters':[],
        'aggregate':'value','property':'properties.overall_width_m','output_unit':'mm'}
  self.assertEqual(native_query.execute(plan,data)['value'],875)

class MeasurementBreakdown(unittest.TestCase):
 def test_each_room_uses_typed_units_and_missing_measurements_do_not_make_partial_table(self):
  document={'objects':[{'id':name,'type':'room','label':name,'properties':{'net_area_m2':area,'untyped':area}} for name,area in [('A',13.),('B',7.)]]}
  plan={'answerable':True,'object_type':'room','object_ids':None,'filters':[],
        'aggregate':'values','property':'properties.net_area_m2','output_unit':'ft2'}
  result=native_query.answer('How many square metres of flooring are required for each room?',document,lambda *a,**k:plan)
  self.assertEqual(len(result['rows']),2);self.assertEqual(result['rows'][0]['unit'],'ft²')
  self.assertAlmostEqual(result['rows'][0]['value'],13/.09290304,places=5)
  self.assertIsNone(native_query.execute({**plan,'property':'properties.untyped'},document))
  self.assertIsNone(native_query.answer('How many rooms?',document,lambda *a,**k:plan))
  del document['objects'][1]['properties']['net_area_m2']
  self.assertIsNone(native_query.execute(plan,document))
 def test_measurement_unit_after_how_many_is_not_a_count(self):
  for question,expected in [('How many square meters per room?','area'),('How many m² of flooring?','area'),
    ('How many cubic metres of concrete?','volume'),('How many metres of wall?','length'),('How many doors wider than 2 m?','count'),
    ('Quanti metri di tubi ci sono nel progetto?','length'),('Quanti metri quadrati di pavimento?','area'),
    ('Quanti metri cubi di calcestruzzo?','volume'),('Quante porte più larghe di 2 metri?','count')]:
   with self.subTest(question=question):self.assertEqual(llm.requested_quantity(question),expected)
 def test_large_property_schemas_are_shared_without_erasing_fields(self):
  import json
  psets={'Spec'+str(i):{'Material'+str(j):'source value' for j in range(10)} for i in range(30)}
  records=[{'id':str(i),'type':'Type'+str(i),'label':'sample','properties':{'property_sets':psets,'net_area_m2':7.}} for i in range(20)]
  context=native_query._planner_context(records,'Which materials are declared?')
  self.assertLessEqual(len(json.dumps(context,ensure_ascii=False,separators=(',',':'))),64000)
  self.assertIn('properties.net_area_m2',context['types']['Type0']['fields'])
  self.assertIn('properties.property_sets.Spec0',context['types']['Type0']['field_groups'])
  self.assertIn('Material0',context['shared_field_groups']['properties.property_sets.Spec0'])
if __name__=='__main__':unittest.main()

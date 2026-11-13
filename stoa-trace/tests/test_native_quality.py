"""Native quantity semantics and exporter compatibility, without model calls."""
from pathlib import Path
import math
import tempfile
import unittest
from server.extraction import extract_document
from server.native_qa import answer_native

class NativeQuantityQuality(unittest.TestCase):
    def answer(self, question, objects, suffix='.ifc'):
        root = Path(tempfile.gettempdir())
        return answer_native(question, {'metadata': {}, 'objects': objects}, root/('quality'+suffix), root)

    def test_net_gross_and_unresolved_area_filter(self):
        room = {'id':'r', 'guid':'g', 'label':'Office', 'type':'IfcSpace',
                'properties':{'name':'Office', 'net_area_m2':10, 'gross_area_m2':12}}
        self.assertEqual(self.answer('What is the gross floor area of room Office in m²?', [room])['value'], 12)
        self.assertEqual(self.answer('What is the net floor area of room Office in m²?', [room])['value'], 10)
        del room['properties']['gross_area_m2']
        self.assertIsNone(self.answer('What is the gross floor area of room Office?', [room]))
        self.assertIsNone(self.answer('What is the net floor area of room Office with wooden walls?', [room]))
        self.assertIsNone(self.answer('What is the net and gross floor area of room Office?', [room]))

    def test_all_schedule_constraints_are_consumed(self):
        rows = [{'id':f'd{i}', 'type':'schedule_door', 'label':f'Door 100.{i}', 'properties':{
            'door_number':f'100.{i}', 'door_type':'B1', 'width':width}} for i,width in enumerate(('1m','3m'))]
        question = 'How many doors of door type B1 are wider than 2m in the door schedule?'
        self.assertEqual(self.answer(question, rows, '.pdf')['value'], 1)
        for unknown in ('fire rated','purple','wider than two metres','wider than 2','not'):
            with self.subTest(unknown=unknown):
                self.assertIsNone(self.answer(f'How many {unknown} doors of door type B1 are in the door schedule?',rows,'.pdf'))
        rows[0]['properties']['width'] = 'unknown'
        self.assertIsNone(self.answer(question, rows, '.pdf'))

    def test_unknown_schedule_area_qualifiers(self):
        rows = [{'id':'r', 'type':'schedule_room', 'label':'Room 100 · Office', 'properties':{'room_number':'100','area_ft2':100}}]
        for question in ('What is the total area of all rooms with red ceilings in the finish schedule?',
                         'What is the gross area of room 100 in the finish schedule?',
                         'What is the total area of all rooms > 200 in the finish schedule?'):
            self.assertIsNone(self.answer(question, rows, '.pdf'))
        self.assertEqual(self.answer('What is the total area of all rooms in the finish schedule?',rows,'.pdf')['value'],100)

    def test_wall_quantities_are_role_specific_and_complete(self):
        walls = [{'id':f'w{i}', 'guid':f'g{i}', 'type':'IfcWall','label':f'Wall {i}',
                  'properties':{'length_m':v,'net_volume_m3':v*2,'net_side_area_m2':v*3}} for i,v in enumerate((2,4))]
        self.assertEqual(self.answer('What is the total length of all walls in the model in metres?',walls)['value'],6)
        self.assertEqual(self.answer('What is the total net volume of all walls in the model in m³?',walls)['value'],12)
        self.assertEqual(self.answer('What is the total net side area of all walls in the model in m²?',walls)['value'],18)
        self.assertIsNone(self.answer('What is the total gross volume of all walls in the model?',walls))
        del walls[0]['properties']['length_m']
        self.assertIsNone(self.answer('What is the total length of all walls in the model?',walls))

    def test_ambiguous_room_and_leftover_numeric_selector_abstain(self):
        rooms = [{'id':f'r{i}', 'type':'IfcSpace', 'label':'Office', 'properties':{'name':str(i), 'net_area_m2':10}} for i in (1,2)]
        self.assertIsNone(self.answer('What is the area of room Office in m²?', rooms))
        self.assertIsNone(self.answer('What is the total area of all rooms 999 in m²?', rooms))
        self.assertEqual(self.answer('What is the total area of all rooms Office in m²?', rooms)['value'], 20)

    def test_project_records_are_native_fields(self):
        rows = [{'id':'p','type':'IfcProject','label':'Project','properties':{'name':'Real project'}},
                {'id':'s','type':'IfcSite','label':'Site','properties':{'name':'Site A','RefLatitude':[60,10,1]}}]
        result = self.answer('What is the project information and site location for this project?',rows)
        self.assertIn('Real project',result['answer']); self.assertIn('RefLatitude',result['answer'])
        self.assertEqual(len(result['evidence']),2)

    def test_ifc_explicit_units_and_quantity_paths(self):
        import ifcopenshell
        model=ifcopenshell.file(schema='IFC4')
        length=model.create_entity('IfcSIUnit',UnitType='LENGTHUNIT',Prefix='MILLI',Name='METRE')
        area=model.create_entity('IfcSIUnit',UnitType='AREAUNIT',Name='SQUARE_METRE')
        volume=model.create_entity('IfcSIUnit',UnitType='VOLUMEUNIT',Name='CUBIC_METRE')
        units=model.create_entity('IfcUnitAssignment',Units=[length,area,volume])
        model.create_entity('IfcProject',GlobalId=ifcopenshell.guid.new(),Name='Generated fixture',UnitsInContext=units)
        wall=model.create_entity('IfcWall',GlobalId=ifcopenshell.guid.new(),Name='Wall A')
        qlength=model.create_entity('IfcQuantityLength',Name='Length',LengthValue=2000.)
        qvolume=model.create_entity('IfcQuantityVolume',Name='NetVolume',VolumeValue=3.)
        qto=model.create_entity('IfcElementQuantity',GlobalId=ifcopenshell.guid.new(),Name='Qto_WallBaseQuantities',Quantities=[qlength,qvolume])
        model.create_entity('IfcRelDefinesByProperties',GlobalId=ifcopenshell.guid.new(),RelatedObjects=[wall],RelatingPropertyDefinition=qto)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.ifc'; model.write(path)
            doc=extract_document(path,Path(folder))
        props=next(o for o in doc['objects'] if o['type']=='IfcWall')['properties']
        self.assertEqual(props['length_m'],2); self.assertEqual(props['net_volume_m3'],3)
        self.assertEqual(props['quantity_sources']['length_m']['property_path'],'Qto_WallBaseQuantities.Length')
        # A missing unit assignment cannot silently become metres.
        model.by_type('IfcProject')[0].UnitsInContext = None
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'unitless.ifc'; model.write(path)
            doc=extract_document(path,Path(folder))
        props=next(o for o in doc['objects'] if o['type']=='IfcWall')['properties']
        self.assertNotIn('length_m',props); self.assertNotIn('net_volume_m3',props)

class SwissExporterCompatibility(unittest.TestCase):
    def drawing(self,semantic=True):
        import ezdxf
        drawing=ezdxf.new(); drawing.units=6; model=drawing.modelspace()
        if semantic:
            model.add_lwpolyline([(0,0),(4,0),(4,4),(0,4),(0,0)],dxfattribs={'layer':'UNIT_OUTLINE'})
            model.add_lwpolyline([(0,0),(3,0),(3,3),(0,3),(0,0)],dxfattribs={'layer':'ROOM_OUTLINE'})
            for text,point in [('Whg. A',(3.5,3.5)),('Office',(1,2)),('U1.01',(1,1.7)),('9 m²',(1,1.4))]:
                model.add_text(text,dxfattribs={'layer':'ROOM_TEXT','insert':point})
        return drawing,model

    def test_repeated_endpoint_prefixed_room_and_whg_label(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); drawing,_=self.drawing(); path=root/'fixture.dxf'; drawing.saveas(path)
            doc=extract_document(path,root)
            unit=next(o for o in doc['objects'] if o['type']=='apartment')
            room=next(o for o in doc['objects'] if o['type']=='room')
            self.assertEqual(unit['label'],'Whg. A'); self.assertEqual(room['properties']['room_number'],'U1.01')
            self.assertEqual(room['properties']['unit_id'],unit['id'])
            self.assertEqual(answer_native('What is the net floor area of room U1.01 in m²?',doc,path,root)['value'],9)
            self.assertEqual(answer_native('What is the net floor area of apartment A in m²?',doc,path,root)['value'],9)
            self.assertIsNone(answer_native('What is the gross floor area of room U1.01 in m²?',doc,path,root))

    def test_fixture_requires_semantic_export_signature(self):
        for semantic in (True,False):
            with self.subTest(semantic=semantic),tempfile.TemporaryDirectory() as folder:
                root=Path(folder); drawing,model=self.drawing(semantic)
                model.add_lwpolyline([(1,1),(1.6,1),(1.6,1.8),(1,1.8)],close=True,dxfattribs={'layer':'FIXTURE'})
                model.add_lwpolyline([(1.3+.2*math.cos(i*2*math.pi/47),1.4+.25*math.sin(i*2*math.pi/47)) for i in range(48)],dxfattribs={'layer':'FIXTURE'})
                model.add_lwpolyline([(1.1,1.7),(1.5,1.7)],dxfattribs={'layer':'FIXTURE'})
                path=root/'fixture.dxf'; drawing.saveas(path); doc=extract_document(path,root)
                if semantic:
                    result=answer_native('How many toilets (WC) are drawn on this floor plan?',doc,path,root)
                    self.assertEqual(result['value'],1)
                    self.assertIn('cistern',result['evidence'][0]['properties']['count_basis'])
                else:
                    self.assertFalse(any(o['type']=='toilet' for o in doc['objects']))

if __name__=='__main__': unittest.main()

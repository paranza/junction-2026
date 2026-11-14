"""Native quantity semantics and exporter compatibility, without model calls."""
from pathlib import Path
import math
import tempfile
import unittest
from unittest.mock import patch
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
        self.assertIsNone(self.answer('What is the total area of room 1 and 2 in m²?', rooms))
        self.assertIsNone(self.answer('What is the total area of room 1 and room 2 in m²?', rooms))
        self.assertEqual(self.answer('What is the area of room 1 in m²?', rooms)['value'], 10)
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


class IfcSourceGeometryQuality(unittest.TestCase):
    """Independently generated 4m by 3m rooms and stair assemblies, no labels."""
    def model(self, length_unit=True):
        import ifcopenshell
        model = ifcopenshell.file(schema='IFC4')
        area = model.create_entity('IfcSIUnit', UnitType='AREAUNIT', Name='SQUARE_METRE')
        units = [area]
        if length_unit:
            units.append(model.create_entity('IfcSIUnit', UnitType='LENGTHUNIT', Prefix='MILLI', Name='METRE'))
        assignment = model.create_entity('IfcUnitAssignment', Units=units)
        model.create_entity('IfcProject', GlobalId=ifcopenshell.guid.new(), Name='Generated fixture', UnitsInContext=assignment)
        origin = model.create_entity('IfcCartesianPoint', Coordinates=(0., 0., 0.))
        axis = model.create_entity('IfcAxis2Placement3D', Location=origin)
        context = model.create_entity('IfcGeometricRepresentationContext', CoordinateSpaceDimension=3,
                                      WorldCoordinateSystem=axis)
        return model, context

    def room(self, model, context, footprint='closed', custom_zero=True):
        import ifcopenshell
        room = model.create_entity('IfcSpace', GlobalId=ifcopenshell.guid.new(), Name='Office', CompositionType='ELEMENT')
        if footprint is not None:
            points = [(0., 0.), (4000., 0.), (4000., 3000.), (0., 3000.), (0., 0.)]
            if footprint == 'open':
                points = points[:-1]
            if footprint == 'nonplanar':
                points = [(x, y, 200. if i == 2 else 0.) for i, (x, y) in enumerate(points)]
            curve = model.create_entity('IfcPolyline', Points=[model.create_entity('IfcCartesianPoint', Coordinates=p) for p in points])
            curves = [curve]
            if footprint == 'curved':
                position = model.create_entity('IfcAxis2Placement2D', Location=model.create_entity('IfcCartesianPoint', Coordinates=(0., 0.)))
                curves = [model.create_entity('IfcCircle', Position=position, Radius=2000.)]
            if footprint == 'ambiguous':
                other = [(6000., 0.), (7000., 0.), (7000., 1000.), (6000., 1000.), (6000., 0.)]
                curves.append(model.create_entity('IfcPolyline', Points=[model.create_entity('IfcCartesianPoint', Coordinates=p) for p in other]))
            curve_set = model.create_entity('IfcGeometricCurveSet', Elements=curves)
            representation = model.create_entity('IfcShapeRepresentation', ContextOfItems=context,
                                                  RepresentationIdentifier='FootPrint', RepresentationType='GeometricCurveSet', Items=[curve_set])
            room.Representation = model.create_entity('IfcProductDefinitionShape', Representations=[representation])
        if custom_zero:
            value = model.create_entity('IfcPropertySingleValue', Name='Pindala', NominalValue=model.create_entity('IfcLabel', '0.000'))
            pset = model.create_entity('IfcPropertySet', GlobalId=ifcopenshell.guid.new(), Name='Legacy_CustomSpace', HasProperties=[value])
            model.create_entity('IfcRelDefinesByProperties', GlobalId=ifcopenshell.guid.new(), RelatedObjects=[room], RelatingPropertyDefinition=pset)
        return room

    def quantities(self, model, room, values):
        import ifcopenshell
        quantities = [model.create_entity('IfcQuantityArea', Name=name, AreaValue=float(value)) for name, value in values]
        qto = model.create_entity('IfcElementQuantity', GlobalId=ifcopenshell.guid.new(), Name='Qto_SpaceBaseQuantities', Quantities=quantities)
        model.create_entity('IfcRelDefinesByProperties', GlobalId=ifcopenshell.guid.new(), RelatedObjects=[room], RelatingPropertyDefinition=qto)

    def answer_room(self, model, question='What is the net floor area of room Office in m²?'):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'independent.ifc'
            model.write(path)
            document = extract_document(path, root)
            return answer_native(question, document, path, root)

    def test_custom_zero_area_recovers_from_closed_footprint_with_length_units(self):
        model, context = self.model()
        self.room(model, context)
        answer = self.answer_room(model)
        self.assertIsNotNone(answer)
        self.assertAlmostEqual(answer['value'], 12.)
        self.assertEqual(len(answer['evidence']), 1)
        self.assertIn('footprint', str(answer).lower())

    def test_missing_quantity_can_use_single_valid_room_footprint(self):
        model, context = self.model()
        self.room(model, context, custom_zero=False)
        answer = self.answer_room(model)
        self.assertIsNotNone(answer)
        self.assertAlmostEqual(answer['value'], 12.)

    def test_explicit_typed_net_zero_is_not_replaced_by_positive_geometry(self):
        model, context = self.model()
        room = self.room(model, context)
        self.quantities(model, room, [('NetFloorArea', 0.)])
        answer = self.answer_room(model)
        self.assertIsNotNone(answer)
        self.assertEqual(answer['value'], 0.)

    def test_positive_typed_quantity_retains_precedence(self):
        model, context = self.model()
        room = self.room(model, context)
        self.quantities(model, room, [('NetFloorArea', 10.)])
        answer = self.answer_room(model)
        self.assertEqual(answer['value'], 10.)

    def test_no_gross_quantity_substitution_for_missing_net(self):
        model, context = self.model()
        room = self.room(model, context, footprint=None, custom_zero=False)
        self.quantities(model, room, [('GrossFloorArea', 15.)])
        self.assertIsNone(self.answer_room(model))
        self.assertEqual(self.answer_room(model, 'What is the gross floor area of room Office in m²?')['value'], 15.)

    def test_unsupported_or_ambiguous_zero_area_geometry_refuses(self):
        for footprint, length_unit in [('open', True), ('curved', True), ('ambiguous', True),
                                       ('nonplanar', True), (None, True), ('closed', False)]:
            with self.subTest(footprint=footprint, length_unit=length_unit):
                model, context = self.model(length_unit=length_unit)
                self.room(model, context, footprint=footprint)
                self.assertIsNone(self.answer_room(model))

    def test_conflicting_explicit_same_role_quantities_do_not_fall_back_to_geometry(self):
        model, context = self.model()
        room = self.room(model, context)
        self.quantities(model, room, [('NetFloorArea', 10.), ('NetArea', 11.)])
        self.assertIsNone(self.answer_room(model))

    def stair_fixture(self, parented=True):
        import ifcopenshell
        model, _ = self.model()
        flights = [model.create_entity('IfcStairFlight', GlobalId=ifcopenshell.guid.new(), Name=f'Flight {i}') for i in range(2)]
        stairs = []
        if parented:
            stairs = [model.create_entity('IfcStair', GlobalId=ifcopenshell.guid.new(), Name='Main stair'),
                      model.create_entity('IfcStair', GlobalId=ifcopenshell.guid.new(), Name='Unseen stair')]
            model.create_entity('IfcRelAggregates', GlobalId=ifcopenshell.guid.new(), RelatingObject=stairs[0], RelatedObjects=flights)
        return model, stairs, flights

    def answer_visible_stairs(self, model, visible_guids):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'independent-stairs.ifc'
            model.write(path)
            document = extract_document(path, root)
            visible = [obj for obj in document['objects'] if obj.get('guid') in visible_guids]
            with patch('server.native_qa._ifc_scope', return_value=(document, visible, 'Visible objects on selected floor drawing', [])):
                return answer_native('How many stairs are shown on this floor plan?', document, path, root)

    def test_visible_flights_count_their_distinct_source_stair_assembly(self):
        model, stairs, flights = self.stair_fixture()
        answer = self.answer_visible_stairs(model, {flight.GlobalId for flight in flights})
        self.assertIsNotNone(answer)
        self.assertEqual(answer['value'], 1)
        self.assertEqual(len(answer['evidence']), 1)
        self.assertEqual(answer['evidence'][0]['guid'], stairs[0].GlobalId)

    def test_visible_parent_and_its_flights_are_not_double_counted(self):
        model, stairs, flights = self.stair_fixture()
        answer = self.answer_visible_stairs(model, {stairs[0].GlobalId, *(flight.GlobalId for flight in flights)})
        self.assertEqual(answer['value'], 1)

    def test_unparented_flights_are_not_called_zero_stairs(self):
        model, _, flights = self.stair_fixture(parented=False)
        self.assertIsNone(self.answer_visible_stairs(model, {flight.GlobalId for flight in flights}))

    def test_genuinely_empty_stair_class_can_return_zero(self):
        import ifcopenshell
        model, _ = self.model()
        wall = model.create_entity('IfcWall', GlobalId=ifcopenshell.guid.new(), Name='Only a wall')
        answer = self.answer_visible_stairs(model, {wall.GlobalId})
        self.assertIsNotNone(answer)
        self.assertEqual(answer['value'], 0)

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


class CadPreviewRegistration(unittest.TestCase):
    def drawing(self, root, degenerate=False, pdf=True):
        import ezdxf
        import pymupdf
        drawing=ezdxf.new(); drawing.units=6; model=drawing.modelspace()
        positions=[(0,0),(0,6),(0,12)] if degenerate else [(0,0),(6,0),(0,6),(6,6)]
        model.add_lwpolyline([(-1,-1),(12,-1),(12,18),(-1,18)],close=True,dxfattribs={'layer':'UNIT_OUTLINE'})
        sheet=pymupdf.open(); page=sheet.new_page(width=500,height=600)
        for i,(x,y) in enumerate(positions,1):
            model.add_lwpolyline([(x,y),(x+4,y),(x+4,y+4),(x,y+4)],close=True,dxfattribs={'layer':'ROOM_OUTLINE'})
            for text,point in [('Office',(x+2,y+2.5)),(f'1.0{i}',(x+2,y+2)),('16 m²',(x+2,y+1.5))]:
                model.add_text(text,dxfattribs={'layer':'ROOM_TEXT','insert':point})
            # The PDF has substantial margins, unlike CAD extents.
            page.insert_text((100+(x+2)*15,500-(y+2)*15),f'1.0{i}',fontsize=8)
        path=root/'plan.dxf'; drawing.saveas(path)
        if pdf: sheet.save(root/'plan.pdf')
        sheet.close()
        return path

    def test_paired_dxf_uses_the_same_registered_evidence_as_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); path=self.drawing(root)
            direct=extract_document(path,root); paired=extract_document(path.with_suffix('.pdf'),root)
            rooms=[o for o in direct['objects'] if o['type']=='room']
            self.assertEqual(len(rooms),4)
            self.assertTrue(direct['metadata']['cad_projection_registered'])
            self.assertEqual(direct['metadata']['original_source_path'],'plan.dxf')
            self.assertEqual(direct['pages'][0]['width'],500)
            self.assertEqual([o['bbox']for o in rooms],[o['bbox']for o in paired['objects']if o['type']=='room'])
            self.assertTrue(all(o['source_path']=='plan.pdf' for o in rooms))
            self.assertTrue(all(o['properties']['native_source_path']=='plan.dxf' for o in rooms))
            self.assertGreater(rooms[0]['bbox'][0],.19)
            self.assertLess(rooms[0]['bbox'][0],.25)

    def test_standalone_and_degenerate_fits_retain_unlocated_records(self):
        for standalone,degenerate in ((True,False),(False,True)):
            with self.subTest(standalone=standalone),tempfile.TemporaryDirectory() as folder:
                root=Path(folder); path=self.drawing(root,degenerate,pdf=not standalone)
                doc=extract_document(path,root)
                rooms=[o for o in doc['objects']if o['type']=='room']
                self.assertEqual(len(rooms),3 if degenerate else 4)
                self.assertTrue(all(not o.get('bbox')and not o.get('polygon')for o in rooms))
                self.assertTrue(all(o['properties']['net_area_m2']==16 for o in rooms))
                self.assertFalse(doc['metadata']['cad_projection_registered'])
                self.assertTrue(doc['warnings'])

if __name__=='__main__': unittest.main()

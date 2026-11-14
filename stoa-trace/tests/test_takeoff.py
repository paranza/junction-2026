import copy
import unittest
from pathlib import Path

from server.native_qa import answer_native

ROOT = Path('/tmp')


def room(identity, number, label, points, area, unit=None, **properties):
    # The 1000 x 500 pt page is drawn at 50 pt per metre.
    polygon = [[x / 20, y / 10] for x, y in points]
    return {'id': identity, 'type': 'room', 'label': label, 'page': 1, 'polygon': polygon,
            'bbox': [min(p[0] for p in polygon), min(p[1] for p in polygon), max(p[0] for p in polygon), max(p[1] for p in polygon)],
            'properties': {'room_number': number, 'net_area_m2': area, 'geometry_area_m2': area, 'unit_id': unit, **properties}}


def plan():
    return {'metadata': {}, 'pages': [{'page': 1, 'width': 1000, 'height': 500}], 'objects': [
        room('living', '1.01', 'Living', [(2, 2), (6, 2), (6, 5), (2, 5)], 12.0, 'unit-a'),      # 4 x 3 m
        room('kitchen', '1.02', 'Kitchen', [(6, 2), (8, 2), (8, 5), (6, 5)], 6.0, 'unit-a'),     # 2 x 3 m
        room('balcony', '1.03', 'Balkon', [(2, 5), (6, 5), (6, 6), (2, 6)], 4.0, 'unit-a'),      # outdoor
        room('bedroom', '2.01', 'Bedroom', [(10, 2), (14, 2), (14, 4), (12, 4), (12, 6), (10, 6)], 12.0, 'unit-b'),  # L shape
        room('shaft', '9.01', 'Schacht', [(15, 2), (16, 2), (16, 3), (15, 3)], 1.0, spatial_kind='shaft_or_void'),
        {'id': 'unit-a', 'type': 'apartment', 'label': 'App. A', 'page': 1, 'properties': {}},
        {'id': 'unit-b', 'type': 'apartment', 'label': 'App. B', 'page': 1, 'properties': {}},
    ]}


def ask(question, document=None):
    return answer_native(question, document or plan(), ROOT / 'plan.dxf', ROOT)


class TakeoffTests(unittest.TestCase):
    def test_room_perimeter_is_measured_on_its_outline(self):
        result = ask('What is the perimeter of room 1.01?')
        self.assertEqual((result['value'], result['unit'], result['method']), (14.0, 'm', 'native_cad_room_takeoff'))
        self.assertEqual([item['id'] for item in result['evidence']], ['living'])
        self.assertEqual(ask('What is the perimeter of room 2.01?')['value'], 16.0)
        self.assertEqual(ask("What is the perimeter of the 'Kitchen'?")['value'], 10.0)
        self.assertEqual(ask("What's the perimeter of room 1.01?")['value'], 14.0)
        summed = ask('What is the total perimeter of rooms 1.01 and 1.02?')
        self.assertEqual(summed['value'], 24.0)
        self.assertEqual(summed['calculation']['terms'], [14.0, 10.0])

    def test_skirting_covers_indoor_rooms_and_states_its_basis(self):
        result = ask('How much skirting is needed?')
        self.assertEqual(result['value'], 40.0)  # balcony and shaft are left out
        self.assertEqual([item['id'] for item in result['evidence']], ['living', 'kitchen', 'bedroom'])
        self.assertIn('Door openings are not deducted', result['answer'])
        self.assertEqual(ask('How many metres of skirting board are needed for apartment A?')['value'], 24.0)
        selected = {**plan(), 'metadata': {'requested_scope': 'region'}}
        self.assertIn('in the selected area', ask('How much skirting do I need?', selected)['answer'])

    def test_wall_area_uses_the_stated_ceiling_height_only(self):
        result = ask('What is the wall area of room 1.01 with a 2.6 m ceiling?')
        self.assertEqual((result['value'], result['unit']), (36.4, 'm²'))
        self.assertEqual(result['calculation']['formula'], '14 m × 2.6 m = 36.4 m²')
        self.assertEqual(ask('Wall area of room 1.01, ceiling height of 260 cm')['value'], 36.4)
        self.assertEqual(ask('Wall area of room 1.01, h = 2.6 m')['value'], 36.4)
        missing = ask('What is the wall area of room 1.01?')
        self.assertIsNone(missing['value'])
        self.assertEqual(missing['status'], 'insufficient_evidence')
        self.assertIn('room 1.01 with a 2.6 m ceiling', missing['answer'])
        self.assertIsNone(ask('What is the wall area of room 1.01 with a 40 m ceiling?'))

    def test_waste_is_applied_to_any_native_quantity_and_keeps_the_net_answer(self):
        result = ask('What is the net floor area of room 1.01 plus 10% waste?')
        self.assertEqual((result['value'], result['unit']), (13.2, 'm²'))
        self.assertEqual(result['calculation']['net'], 12.0)
        self.assertEqual([item['id'] for item in result['evidence']], ['living'])
        self.assertIn('Net: 12 m²', result['answer'])
        self.assertEqual(ask('How much skirting is needed for apartment A, with a 5% waste allowance?')['value'], 25.2)
        self.assertEqual(ask('Wall area of room 1.01 with a 2.6 m ceiling + 10%')['value'], 40.04)
        self.assertEqual(ask('Skirting for App. A, add 10%')['value'], 26.4)
        self.assertEqual(ask('How much skirting for apt A plus an extra 5%?')['value'], 25.2)
        self.assertIsNone(ask('How many rooms are labelled Kitchen plus 10% waste?'))
        self.assertIsNone(ask('What is the wall area of room 1.01 plus 10% waste?')['value'])

    def test_unresolved_wording_is_refused(self):
        for question in ('What is the perimeter of room 7.77?', 'What is the perimeter of this floor?',
                         'What is the perimeter of apartment A?', 'How many skirting?',
                         'How much skirting is needed in rooms larger than 10 m²?',
                         "What is the perimeter of the 'Garage'?", 'How much skirting is needed for the bedrooms?',
                         'What is the perimeter of room 1.01 with a 2.6 m ceiling?'):
            self.assertIsNone(ask(question), question)

    def test_incomplete_geometry_refuses_the_whole_sum(self):
        document = plan()
        del document['objects'][1]['properties']['geometry_area_m2']
        self.assertIsNone(ask('How much skirting is needed?', document))
        self.assertEqual(ask('What is the perimeter of room 1.01?', document)['value'], 14.0)

    def test_standalone_and_unregistered_cad_give_the_same_length(self):
        # Page placement u = 0.04 x + 0.1, v = -0.08 y + 0.9 (not the same scale on both axes).
        placed = plan()
        placed['metadata']['preview_transform'] = [0.04, 0, 0.1, 0, -0.08, 0.9]
        placed['objects'][0]['polygon'] = [[0.04 * x + 0.1, -0.08 * y + 0.9] for x, y in ((2, 2), (6, 2), (6, 5), (2, 5))]
        self.assertEqual(ask('What is the perimeter of room 1.01?', placed)['value'], 14.0)
        hidden = plan()
        hidden['metadata']['cad_extents'] = [0, 0, 20, 10]
        target = hidden['objects'][0]
        target['properties']['native_geometry'] = {'polygon': target.pop('polygon'), 'bbox': target.pop('bbox')}
        result = ask('What is the perimeter of room 1.01?', hidden)
        self.assertEqual(result['value'], 14.0)
        self.assertFalse(result['spatial_evidence_complete'])

    def test_room_area_answers_are_unchanged_and_never_stand_in_for_walls(self):
        self.assertEqual(ask('What is the net floor area of room 1.01?')['value'], 12.0)
        self.assertEqual(ask('What is the total net floor area of all rooms?')['method'], 'native_cad_area_annotations')
        original = plan()
        document = copy.deepcopy(original)
        ask('What is the total wall area of all rooms with a 2.6 m ceiling?', document)
        self.assertEqual(document, original)


if __name__ == '__main__':
    unittest.main()

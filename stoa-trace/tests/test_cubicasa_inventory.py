"""CubiCasa count questions share one cached inventory per image, in both languages."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from fastapi.testclient import TestClient

from server import app as api, inventory, llm, store
from server.normalize import TABLE, to_english

EXPECTED = {
    'windows': ('window',), 'floors (storeys)': ('floor',), 'toilet bowls': ('toilet',), 'sinks and wash basins': ('sink',),
    'showers and bathtubs': ('shower', 'bathtub'), 'doors': ('door',), 'saunas': ('sauna',), 'kitchens': ('kitchen',),
    'bedrooms': ('bedroom',), 'separate WC rooms': ('wc_room',), 'bathrooms or washrooms': ('bathroom',), 'balconies': ('balcony',),
}


def finnish_twins():
    """Finnish wording of the plan templates, read back from the translation table."""
    rows = json.loads(TABLE.read_text(encoding='utf-8'))['translated']
    return {row['english']: re.sub(r'\\(.)', r'\1', row['pattern'][1:-1]) for row in rows
            if row['english'] in inventory._TEMPLATE_CATEGORIES and '(?P<' not in row['pattern']}


class Routing(unittest.TestCase):
    def test_every_plan_template_has_its_categories(self):
        templates = inventory._TEMPLATE_CATEGORIES
        self.assertEqual(len(templates), 12)
        for question, categories in templates.items():
            topic = next(k for k in EXPECTED if question.startswith('How many ' + k))
            self.assertEqual(inventory.count_categories(question), EXPECTED[topic])
            self.assertTrue(set(categories) <= set(inventory.CATEGORIES))

    def test_finnish_twins_route_like_english(self):
        twins = finnish_twins()
        self.assertEqual(len(twins), 12)
        for english, finnish in twins.items():
            self.assertEqual(inventory.count_categories(to_english(finnish)), inventory.count_categories(english))

    def test_simple_questions_and_unknown_filters_keep_their_old_routing(self):
        self.assertEqual(inventory.count_categories('How many doors?'), ('door',))
        self.assertIsNone(inventory.count_categories('How many windows in the kitchen?'))

    def test_conventions_apply_only_to_cubicasa_drawings(self):
        self.assertIn('Finnish residential plans', inventory._system(Path('data/cubicasa5k/colorful-1.png')))
        self.assertNotIn('Finnish residential plans', inventory._system(Path('uploads/plan.png')))


class Inventory(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        runtime = Path(self.folder.name) / 'runtime'
        for name in ('cache', 'previews', 'uploads'):
            (runtime / name).mkdir(parents=True)
        self.patches = [patch.object(store, 'RUNTIME', runtime), patch.object(store, 'DATA_ROOT', Path(self.folder.name) / 'dataset'),
                        patch.object(api, 'ACCESS_TOKEN', '')]
        for item in self.patches:
            item.start()
        self.client = TestClient(api.app)
        self.client.__enter__()
        image = Image.new('RGB', (100, 100), 'white')
        path = runtime / 'uploads' / 'plan.png'
        image.save(path)
        self.doc = store.register(path, uploaded=True)
        self.path = path
        # Overview plus one crop covering the right half of the page.
        self.images = [{'page': 1, 'region': [0, 0, 1, 1], 'kind': 'overview', 'image': image},
                       {'page': 1, 'region': [.5, 0, 1, 1], 'kind': 'detail crop', 'image': image}]

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for item in reversed(self.patches):
            item.stop()
        self.folder.cleanup()

    def model_output(self):
        row = lambda category, index, box: {'category': category, 'label': category, 'image_index': index, 'bbox': box, 'ambiguous': False}
        return {'complete': True, 'warnings': [], 'objects': [
            row('shower', 0, [.60, .10, .70, .20]),
            row('shower', 1, [.20, .10, .40, .20]),   # same shower in the crop: [.60, .10, .70, .20] on the page
            row('bathtub', 0, [.60, .30, .80, .40]),
            row('bathtub', 1, [.21, .30, .41, .40]),  # same bathtub, slightly offset: [.605, .30, .705, .40]
            row('toilet', 0, [.10, .10, .15, .15]),
            row('toilet', 0, [.20, .10, .25, .15]),   # a second toilet next to the first
            row('floor', 0, [.05, .05, .95, .95]),
            row('floor', 1, [.00, .05, .90, .95]),    # the same plan cut by the crop edge
        ]}

    def ask(self, question):
        return self.client.post('/api/ask', json={'document_id': self.doc['id'], 'question': question, 'mode': 'auto'}).json()

    def test_twins_share_one_call_and_combined_categories_add_up(self):
        twins = finnish_twins()
        showers = 'How many showers and bathtubs are drawn on this floor plan in total?'
        with patch('server.native_qa.answer_native', return_value=None), patch.object(inventory, 'image_inputs', return_value=self.images), \
                patch.object(llm, '_request', return_value=self.model_output()) as model, patch.object(llm, 'KEY', 'test'):
            english = self.ask(showers)
            finnish = self.ask(twins[showers])
            toilets = self.ask('How many toilet bowls (WC seats) are drawn on this floor plan?')
            floors = self.ask('How many floors (storeys) does this floor plan show?')
        self.assertEqual(model.call_count, 1)
        self.assertEqual((english['value'], finnish['value']), (2, 2))
        self.assertEqual(english['category'], 'shower+bathtub')
        self.assertEqual(finnish['interpreted_question'], showers)
        self.assertEqual(toilets['value'], 2)
        self.assertEqual(floors['value'], 1)
        # The larger box is kept for a whole floor plan.
        self.assertAlmostEqual(floors['evidence'][0]['bbox'][2] - floors['evidence'][0]['bbox'][0], .9)


    def test_focused_passes_ask_each_group_once(self):
        def reply(content, system, schema, max_tokens):
            allowed = schema['properties']['objects']['items']['properties']['category']['enum']
            return {**self.model_output(), 'objects': [o for o in self.model_output()['objects'] if o['category'] in allowed]}
        with patch.object(inventory, 'PASSES', 'focused'), patch('server.native_qa.answer_native', return_value=None), \
                patch.object(inventory, 'image_inputs', return_value=self.images), patch.object(llm, '_request', side_effect=reply) as model, \
                patch.object(llm, 'KEY', 'test'):
            showers = self.ask('How many showers and bathtubs are drawn on this floor plan in total?')
            floors = self.ask('How many floors (storeys) does this floor plan show?')
        self.assertEqual(model.call_count, len(inventory.FOCUSED_GROUPS))
        self.assertEqual((showers['value'], floors['value']), (2, 1))

    def test_votes_keep_the_median_run(self):
        toilet = lambda x: {'category': 'toilet', 'label': 'WC', 'image_index': 0, 'bbox': [x, .1, x + .04, .14], 'ambiguous': False}
        runs = iter([[toilet(.1)], [toilet(.1), toilet(.3), toilet(.5)], [toilet(.1), toilet(.3)]])
        reply = lambda *args, **kwargs: {'complete': True, 'warnings': [], 'objects': next(runs)}
        with patch.object(inventory, 'VOTES', 3), patch('server.native_qa.answer_native', return_value=None), \
                patch.object(inventory, 'image_inputs', return_value=self.images) as crops, patch.object(llm, '_request', side_effect=reply) as model, \
                patch.object(llm, 'KEY', 'test'):
            toilets = self.ask('How many toilet bowls (WC seats) are drawn on this floor plan?')
        self.assertEqual(model.call_count, 3)
        self.assertEqual([c.kwargs.get('layout') for c in crops.call_args_list], [0, 1, 2])
        self.assertEqual(toilets['value'], 2)
        self.assertEqual(len(toilets['evidence']), 2)


if __name__ == '__main__':
    unittest.main()

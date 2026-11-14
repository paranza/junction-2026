"""CubiCasa count questions share one cached inventory per image, in both languages."""
import json
import os
from pathlib import Path
import re
import tempfile
import threading
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

    def test_cubicasa_profile_applies_only_to_that_collection(self):
        cubicasa, upload = Path('data/cubicasa5k/colorful-1.png'), Path('uploads/plan.png')
        with patch.dict(os.environ, {}, clear=True):
            self.assertIn(inventory.CUBICASA_CONVENTIONS, inventory._system(cubicasa))
            self.assertNotIn('Include all visible units', inventory._system(cubicasa))
            self.assertEqual(inventory._system(upload), inventory.SYSTEM)
        with patch.dict(os.environ, {'STOA_ANNOTATION_PROFILE': 'none'}):
            self.assertEqual(inventory._system(cubicasa), inventory._system(upload))

    def test_gemini_inventory_leaves_room_for_reasoning(self):
        doc = {'document_id': 'plan', 'source_fingerprint': 'plan-v1', 'page_count': 1}
        image = {'page': 1, 'region': [0, 0, 1, 1], 'kind': 'overview', 'image': Image.new('RGB', (10, 10), 'white')}
        reply = {'objects': [], 'complete': True, 'warnings': []}
        with tempfile.TemporaryDirectory() as folder, patch.object(store, 'RUNTIME', Path(folder)), \
                patch.object(inventory, 'image_inputs', return_value=[image]), patch.object(llm, 'PROVIDER', 'gemini'), \
                patch.object(llm, '_request', return_value=reply) as model:
            for name in ('cache', 'previews', 'uploads'):
                (Path(folder) / name).mkdir()
            store.initialize()
            inventory.page_inventory(doc, Path('data/cubicasa5k/plan.png'), 1)
        self.assertEqual(model.call_args.kwargs['max_tokens'], 65536)


class Inventory(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        runtime = Path(self.folder.name) / 'runtime'
        for name in ('cache', 'previews', 'uploads'):
            (runtime / name).mkdir(parents=True)
        self.patches = [patch.object(store, 'RUNTIME', runtime), patch.object(store, 'DATA_ROOT', Path(self.folder.name) / 'dataset'),
                        patch.object(api, 'ACCESS_TOKEN', ''), patch.object(inventory, 'READINGS', 1)]
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
        return self.client.post('/api/ask', json={'document_id': self.doc['id'], 'question': question, 'mode': 'auto', 'verify_visual': False}).json()

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
        # The full observed envelope is kept for a whole floor plan.
        self.assertAlmostEqual(floors['evidence'][0]['bbox'][2] - floors['evidence'][0]['bbox'][0], .9)



class TwoReadings(unittest.TestCase):
    """Repeated readings: the first successful one gives the count, a different count is flagged."""
    question = 'How many toilet bowls (WC seats) are drawn on this floor plan?'
    setUp, tearDown, ask = Inventory.setUp, Inventory.tearDown, Inventory.ask

    def reading(self, toilets, complete=True):
        rows = [{'category': 'toilet', 'label': 'WC', 'image_index': 0, 'bbox': [.1 + .2 * n, .1, .15 + .2 * n, .15], 'ambiguous': False}
                for n in range(toilets)]
        return {'complete': complete, 'warnings': [], 'objects': rows}

    def ask_with_readings(self, readings):
        """Fix what each repeated reading returns, independent of thread scheduling."""
        def parallel(tasks):
            self.assertEqual(len(tasks), len(readings))
            return list(readings)
        with patch.object(inventory, 'READINGS', len(readings)), patch('server.native_qa.answer_native', return_value=None), \
                patch.object(inventory, 'image_inputs', return_value=self.images[:1]), \
                patch.object(llm, 'run_in_parallel', side_effect=parallel), patch.object(llm, 'KEY', 'test'):
            return self.client.post('/api/ask', json={'document_id': self.doc['id'], 'question': self.question, 'mode': 'auto'})

    def test_a_different_count_is_flagged_without_changing_the_answer(self):
        answer = self.ask_with_readings([self.reading(1), self.reading(2)]).json()
        self.assertEqual(answer['value'], 1)
        self.assertEqual(answer['agreement'], {'readings': [1, 2], 'agree': False})
        self.assertTrue(any('gave different counts (1 vs 2)' in w for w in answer['warnings']))

    def test_the_same_count_is_reported(self):
        answer = self.ask_with_readings([self.reading(2), self.reading(2)]).json()
        self.assertEqual(answer['agreement'], {'readings': [2, 2], 'agree': True})
        self.assertFalse(any('different counts' in w for w in answer['warnings']))

    def test_a_failed_repeat_keeps_the_first_reading(self):
        answer = self.ask_with_readings([self.reading(2), llm.ModelError('The model did not finish its analysis.')]).json()
        self.assertEqual(answer['value'], 2)
        self.assertIsNone(answer['agreement'])

    def test_any_failure_of_a_repeat_keeps_the_first_reading(self):
        answer = self.ask_with_readings([self.reading(2), RuntimeError('database is locked')]).json()
        self.assertEqual(answer['value'], 2)
        self.assertIsNone(answer['agreement'])

    def test_the_first_successful_reading_gives_the_count(self):
        answer = self.ask_with_readings([llm.ModelError('The model account reached a rate or credit limit.'), self.reading(3)]).json()
        self.assertEqual(answer['value'], 3)
        self.assertIsNone(answer['agreement'])

    def test_all_failed_readings_fail_the_answer(self):
        reply = self.ask_with_readings([llm.ModelError('first'), llm.ModelError('second')])
        self.assertEqual(reply.status_code, 503)

    def test_an_incomplete_repeat_that_found_nothing_is_not_agreement(self):
        answer = self.ask_with_readings([self.reading(0), self.reading(0, complete=False)]).json()
        self.assertEqual(answer['value'], 0)
        self.assertIsNone(answer['agreement'])

    def test_readings_run_through_real_threads(self):
        lock, served = threading.Lock(), []
        replies = [self.reading(1), self.reading(2)]
        def reply(*args, **kwargs):
            with lock:
                served.append(replies[len(served)])
                return served[-1]
        with patch.object(inventory, 'READINGS', 2), patch('server.native_qa.answer_native', return_value=None), \
                patch.object(inventory, 'image_inputs', return_value=self.images[:1]), \
                patch.object(llm, '_request', side_effect=reply), patch.object(llm, 'KEY', 'test'):
            answer = self.ask(self.question)
        self.assertEqual(len(served), 2)
        self.assertEqual(sorted(answer['agreement']['readings']), [1, 2])
        self.assertEqual(answer['value'], answer['agreement']['readings'][0])

    def test_one_reading_has_no_agreement(self):
        with patch('server.native_qa.answer_native', return_value=None), \
                patch.object(inventory, 'image_inputs', return_value=self.images[:1]), \
                patch.object(llm, '_request', return_value=self.reading(2)) as model, patch.object(llm, 'KEY', 'test'):
            answer = self.ask(self.question)
        self.assertEqual(model.call_count, 1)
        self.assertIsNone(answer['agreement'])

    def test_agreement_counts_repeat_readings_like_the_answer(self):
        reading = {'complete': True, 'objects': [{'category': 'toilet', 'bbox': [.1, .1, .2, .2]}, {'category': 'toilet', 'bbox': [.7, .7, .8, .8]},
                                                 {'category': 'sink', 'bbox': [.1, .3, .2, .4]}]}
        page = {'other_readings': [reading]}
        self.assertEqual(inventory._agreement(1, [page], ('toilet',), [0, 0, .5, .5]), {'readings': [1, 1], 'agree': True})
        self.assertEqual(inventory._agreement(1, [page], ('toilet',)), {'readings': [1, 2], 'agree': False})
        self.assertEqual(inventory._agreement(3, [page], ('toilet', 'sink')), {'readings': [3, 3], 'agree': True})
        self.assertEqual(inventory._agreement(4, [page, page], ('toilet',)), {'readings': [4, 4], 'agree': True})
        self.assertIsNone(inventory._agreement(None, [page], ('toilet',)))
        self.assertIsNone(inventory._agreement(1, [{'other_readings': []}], ('toilet',)))
        self.assertIsNone(inventory._agreement(1, [page, {'other_readings': []}], ('toilet',)))

    def test_readings_setting(self):
        for raw, expected in (('', 2), ('1', 1), ('3', 3)):
            with patch.dict(os.environ, {'STOA_INVENTORY_READINGS': raw}):
                self.assertEqual(inventory._reading_count(), expected)
        for raw in ('0', '4', 'two'):
            with patch.dict(os.environ, {'STOA_INVENTORY_READINGS': raw}), self.assertRaises(ValueError):
                inventory._reading_count()
        with patch.object(inventory, 'READINGS', 1):
            single = inventory.config_signature()
        with patch.object(inventory, 'READINGS', 2):
            double = inventory.config_signature()
        self.assertNotIn('readings', single)
        self.assertEqual(double['readings'], 2)

if __name__ == '__main__':
    unittest.main()

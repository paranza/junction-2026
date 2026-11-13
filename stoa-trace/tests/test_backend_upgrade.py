"""Cache, scope, complete review and reconciliation regressions without paid calls."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient

from server import app as api, inventory, llm, store


class BackendUpgrade(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.runtime = Path(self.folder.name) / 'runtime'
        self.data = Path(self.folder.name) / 'dataset'
        self.runtime.mkdir()
        for name in ('cache', 'previews', 'uploads'):
            (self.runtime / name).mkdir()
        self.patches = [patch.object(store, 'RUNTIME', self.runtime), patch.object(store, 'DATA_ROOT', self.data),
                        patch.object(api, 'ACCESS_TOKEN', '')]
        for item in self.patches:
            item.start()
        self.client = TestClient(api.app)
        self.client.__enter__()
        image = Image.new('RGB', (100, 100), 'white')
        self.path = self.runtime / 'uploads' / 'fixture.png'
        image.save(self.path)
        self.doc = store.register(self.path, uploaded=True)
        self.native = {'page_count': 1, 'document_id': self.doc['id'], 'source_fingerprint': 'fixture-v1',
                       'pages': [{'page': 1, 'text': '', 'words': []}], 'objects': [], 'metadata': {}}
        self.images = [{'page': 1, 'region': [0, 0, 1, 1], 'kind': 'overview', 'image': image}]

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for item in reversed(self.patches):
            item.stop()
        self.folder.cleanup()

    def ask(self, question='How many windows?', **kwargs):
        return self.client.post('/api/ask', json={'document_id': self.doc['id'], 'question': question, **kwargs})

    def inventory_result(self):
        return {'complete': True, 'warnings': [], 'objects': [
            {'category': 'window', 'label': 'Window 1', 'image_index': 0, 'bbox': [.1, .1, .2, .2], 'ambiguous': False},
            {'category': 'door', 'label': 'Door 1', 'image_index': 0, 'bbox': [.1, .1, .2, .2], 'ambiguous': False},
            {'category': 'window', 'label': 'Window 1 duplicated in crop', 'image_index': 0, 'bbox': [.1, .1, .2, .2], 'ambiguous': False},
        ]}

    def test_visual_inventory_reused_between_categories_and_answer_cache_has_fresh_id(self):
        with patch('server.native_qa.answer_native', return_value=None), patch.object(inventory, 'image_inputs', return_value=self.images), patch.object(llm, '_request', return_value=self.inventory_result()) as model:
            first = self.ask().json()
            second = self.ask('How many doors?').json()
            repeated = self.ask().json()
        self.assertEqual(model.call_count, 1)
        self.assertEqual(first['value'], 1)
        self.assertEqual(second['value'], 1)
        self.assertTrue(second['inventory_cache_hit'])
        self.assertTrue(repeated['usage']['cache_hit'])
        self.assertNotEqual(first['id'], repeated['id'])
        self.assertEqual(repeated['usage']['model_calls'], 0)
        self.assertEqual(first['evidence'][0]['category'], 'window')

    def test_answer_cache_changes_with_scope_and_source(self):
        native = {'value': 0, 'unit': 'count', 'method': 'native-fixture', 'evidence': [], 'status': 'supported'}
        with patch('server.native_qa.answer_native', return_value=native) as solver:
            first = self.ask(mode='native').json()
            repeat = self.ask(mode='native').json()
            page = self.ask(mode='native', scope='page').json()
            self.path.write_bytes(self.path.read_bytes() + b'changed-source')
            changed = self.ask(mode='native').json()
        self.assertEqual(solver.call_count, 3)
        self.assertFalse(first['usage']['cache_hit'])
        self.assertTrue(repeat['usage']['cache_hit'])
        self.assertFalse(page['usage']['cache_hit'])
        self.assertFalse(changed['usage']['cache_hit'])

    def test_manual_add_exclude_undo_and_original_survive(self):
        original = {'id': 'review-fixture', 'document_id': self.doc['id'], 'question': 'Windows?', 'answer': '1 window',
                    'can_review': True, 'value': 1, 'unit': 'count', 'operation': 'count', 'warnings': [],
                    'evidence': [{'id': 'a', 'label': 'Window A', 'page': 1, 'bbox': [.1, .1, .2, .2]}]}
        store.save_answer(original['id'], self.doc['id'], original['question'], original)
        added = {'id': 'manual-window', 'label': 'Missed window', 'category': 'window', 'page': 1, 'bbox': [.4, .4, .5, .5]}
        route = '/api/answers/review-fixture/review'
        response = self.client.post(route, json={'excluded_evidence_ids': ['a'], 'added_evidence': [added], 'note': 'Remove a false positive, add missed window.'})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result['value'], 1)
        self.assertTrue(result['human_reviewed'])
        self.assertEqual(result['review']['revision'], 1)
        self.assertEqual(result['review']['added_count'], 1)
        self.assertEqual(result['original_evidence'], original['evidence'])
        self.assertEqual(store.read_answer(original['id'], original=True)['value'], 1)
        restored = self.client.post(route, json={'excluded_evidence_ids': [], 'added_evidence': []}).json()
        self.assertEqual(restored['value'], 1)
        self.assertEqual(restored['review']['revision'], 2)
        self.assertEqual(len(restored['review_history']), 2)
        self.assertEqual(restored['added_evidence'], [])
        revisions = self.client.get('/api/answers/review-fixture/reviews').json()['revisions']
        self.assertEqual(revisions[0]['added_evidence'][0]['id'], 'manual-window')
        self.assertEqual(revisions[0]['excluded_evidence_ids'], ['a'])
        self.assertEqual(revisions[1]['changes']['removed_manual_ids'], ['manual-window'])
        self.assertEqual(revisions[1]['changes']['restored_ids'], ['a'])

    def test_zero_count_can_add_and_bad_manual_coordinates_or_sources_are_rejected(self):
        original = {'id': 'zero', 'document_id': self.doc['id'], 'question': 'Windows?', 'can_review': True,
                    'value': 0, 'unit': 'count', 'evidence': [], 'warnings': [], 'request_context': {'document_id': self.doc['id'], 'page': 1, 'scope': 'page', 'region': [0, 0, .5, .5]}}
        store.save_answer('zero', self.doc['id'], 'Windows?', original)
        added = {'id': 'manual-1', 'label': 'Window', 'page': 1, 'bbox': [.1, .1, .2, .2]}
        self.assertEqual(self.client.post('/api/answers/zero/review', json={'added_evidence': [added]}).json()['value'], 1)
        for item in [{**added, 'bbox': [0, 0, 2, 1]}, {**added, 'bbox': [.4, .4, .8, .8]}, {**added, 'page': 2}, {**added, 'document_id': 'unrelated'}]:
            self.assertEqual(self.client.post('/api/answers/zero/review', json={'added_evidence': [item]}).status_code, 422)
        self.assertEqual(self.client.post('/api/answers/zero/review', json={'added_evidence': [added, added]}).status_code, 422)

    def test_native_region_count_never_calls_model_and_excludes_boundary_objects(self):
        data = {**self.native, 'objects': [{'id': 'a', 'type': 'door', 'page': 1, 'bbox': [.1, .1, .2, .2]},
                                         {'id': 'b', 'type': 'door', 'page': 1, 'bbox': [.4, .4, .6, .6]}]}
        with patch.object(api, 'extracted', return_value=data), patch.object(llm, '_request', side_effect=AssertionError('No model allowed')):
            response = self.ask('How many doors?', mode='native', region=[0, 0, .5, .5])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['value'], 1)
        self.assertEqual(response.json()['usage']['model_calls'], 0)
        self.assertIn('boundary', ' '.join(response.json()['warnings']))

    def test_native_cross_check_is_explicit_and_never_compares_model_or_schedule_scope(self):
        native = {'value': 2, 'unit': 'count', 'scope': 'Entire linked IFC model', 'evidence': []}
        payload = api.AskRequest(document_id=self.doc['id'], question='How many windows?', cross_check=True)
        with patch.object(inventory, 'answer_inventory', side_effect=AssertionError('Scope mismatch must not call vision')):
            result = api._cross_check(payload, payload.question, native, self.native, Path('drawing.pdf'))
        self.assertEqual(result['status'], 'scope_mismatch')
        native['scope'] = 'Selected drawing'
        visual = {'value': 1, 'unit': 'count', 'evidence': [], 'scope': 'Selected drawing', 'method': 'visual_inventory'}
        with patch.object(inventory, 'answer_inventory', return_value=visual):
            result = api._cross_check(payload, payload.question, native, self.native, Path('drawing.pdf'))
        self.assertEqual(result['status'], 'disagreement')
        self.assertEqual(result['native_value'], 2)
        self.assertEqual(result['visual_value'], 1)

    def test_printed_area_and_geometry_disagreement_needs_no_model(self):
        native = {'value': 12, 'unit': 'm²', 'scope': 'Selected room', 'evidence': [
            {'id': 'room', 'properties': {'printed_area_m2': 12, 'geometry_area_m2': 10}, 'bbox': [.1, .1, .5, .5]}]}
        payload = api.AskRequest(document_id=self.doc['id'], question='What is the room area?', mode='native', cross_check=True)
        with patch.object(llm, '_request', side_effect=AssertionError('No model allowed')):
            result = api._cross_check(payload, payload.question, native, self.native, Path('drawing.pdf'))
        self.assertEqual(result['status'], 'disagreement')
        self.assertEqual(result['native_value'], 12)
        self.assertEqual(result['visual_value'], 10)
        self.assertEqual(result['visual_method'], 'native_polygon_geometry')
        native['evidence'][0]['properties']['geometry_area_m2'] = 12.01
        self.assertEqual(api._cross_check(payload, payload.question, native, self.native, Path('drawing.pdf'))['status'], 'agreement')

    def test_manual_addition_must_match_known_count_category(self):
        original = {'id': 'typed', 'document_id': self.doc['id'], 'question': 'How many windows?', 'can_review': True,
                    'value': 1, 'unit': 'count', 'evidence': [{'id': 'window', 'type': 'IfcWindow'}], 'warnings': []}
        store.save_answer('typed', self.doc['id'], original['question'], original)
        added = {'id': 'manual-1', 'label': 'A door', 'category': 'door', 'page': 1, 'bbox': [.1, .1, .2, .2]}
        self.assertEqual(self.client.post('/api/answers/typed/review', json={'added_evidence': [added]}).status_code, 422)
        added.update(label='Missed window', category='windows')
        result = self.client.post('/api/answers/typed/review', json={'added_evidence': [added]})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['added_evidence'][0]['category'], 'window')

    def test_native_context_stays_valid_json_and_reports_omissions(self):
        document = {'objects': [{'id': str(i), 'properties': {'long': 'A' * 3000}} for i in range(500)],
                    'metadata': {'long': 'A' * 100000}, 'pages': [{'page': i, 'text': 'B' * 40000} for i in range(30)]}
        encoded = llm._native_context(document, 'How many doors?')
        context = json.loads(encoded)
        self.assertLess(len(encoded), 70000)
        self.assertGreater(context['context_limits']['omitted_objects'], 0)
        self.assertGreater(context['context_limits']['omitted_pages'], 0)

    def test_atomic_allowance_and_unknown_failure_cost(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as pool:
            reserved = list(pool.map(lambda _: store.reserve_model_request(2, {'model': 'test'}), range(5)))
        self.assertEqual(sum(reserved), 2)
        with llm.usage_scope():
            ledger = llm._usage.get()
            ledger.update(model_calls=1, unknown_usage=True)
            self.assertIsNone(llm.usage_snapshot()['cost_estimate_usd'])
            self.assertTrue(llm.usage_snapshot()['usage_incomplete'])

    def test_model_native_numeric_assertion_is_checked_in_answer_path(self):
        native = {**self.native, 'objects': [{'id': 'office', 'label': 'Office', 'page': 1, 'properties': {'net_area_m2': 10}}]}
        assertion = {'object_id': 'office', 'image_index': None, 'bbox': None, 'label': 'Office', 'quoted_text': '', 'value': 999, 'unit': 'm²'}
        output = {'answer': '999 m²', 'operation': 'area', 'value': 999, 'unit': 'm²', 'scope': 'Page 1',
                  'evidence': [assertion], 'complete': True, 'needs_review': False, 'warnings': [], 'calculation': None}
        with patch.object(llm, '_request', return_value=output), patch.object(llm, 'image_inputs', return_value=[]):
            result = llm.answer_with_model('What is the net area?', native, self.path)
        self.assertIsNone(result['value'])
        self.assertNotIn('999', result['answer'])
        self.assertFalse(result['evidence'][0]['source_verified'])

    def test_overlapping_different_categories_are_not_merged(self):
        output = {'answer': '2 objects', 'operation': 'count', 'value': 2, 'unit': 'count', 'scope': 'Page 1',
                  'evidence': [{'object_id': None, 'image_index': 0, 'bbox': [.1, .1, .3, .3], 'label': label, 'quoted_text': '', 'value': None, 'unit': None} for label in ('Door', 'Sink')],
                  'complete': True, 'needs_review': False, 'warnings': [], 'calculation': None}
        with patch.object(llm, '_request', return_value=output), patch.object(llm, 'image_inputs', return_value=self.images):
            result = llm.answer_with_model('How many objects?', self.native, self.path)
        self.assertEqual(result['value'], 2)

    def test_unknown_filters_do_not_use_inventory(self):
        for question in ('How many doors wider than 2m?', 'How many windows in the kitchen?', 'How many doors and windows?'):
            self.assertIsNone(inventory.count_category(question))
        self.assertEqual(inventory.count_category('How many windows are shown on this floor plan?'), 'window')


if __name__ == '__main__':
    unittest.main()

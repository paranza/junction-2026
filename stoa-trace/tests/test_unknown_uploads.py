"""Regression checks for independent uploads and uncalibrated measurements."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import io

from PIL import Image

from fastapi.testclient import TestClient

from server import store
from server.app import app, _guard_visual_measurements


class IndependentUploads(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Path(self.temp.name) / 'runtime'
        (self.runtime / 'uploads').mkdir(parents=True)
        (self.runtime / 'cache').mkdir()
        (self.runtime / 'previews').mkdir()
        self.runtime_patch = patch.object(store, 'RUNTIME', self.runtime)
        self.runtime_patch.start()
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.runtime_patch.stop()
        self.temp.cleanup()

    def upload_pair(self):
        response = self.client.post('/api/upload', files=[
            ('files', ('independent-plan.pdf', b'%PDF test source')),
            ('files', ('independent-plan.dxf', b'0\nEOF\n')),
        ])
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['documents']

    def test_sibling_exports_keep_a_shared_stem_but_batches_are_isolated(self):
        first, second = self.upload_pair(), self.upload_pair()
        a, b = [store.get_path(item['id']) for item in first]
        self.assertEqual(a.with_suffix('.dxf'), b)
        self.assertTrue(a.exists() and b.exists())
        self.assertEqual({item['source'] for item in first}, {'uploads'})
        self.assertTrue({item['id'] for item in first}.isdisjoint(item['id'] for item in second))

    def test_ambiguous_duplicate_names_are_rejected_before_registering(self):
        before = store.list_documents()['total']
        response = self.client.post('/api/upload', files=[
            ('files', ('same.pdf', b'first')), ('files', ('same.pdf', b'second'))])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(store.list_documents()['total'], before)
        self.assertEqual(list((self.runtime / 'uploads').iterdir()), [])

    def measurement_source(self):
        content = io.BytesIO()
        Image.new('RGB', (1200, 600), 'white').save(content, format='PNG')
        response = self.client.post('/api/upload', files=[('files', ('new-drawing.png', content.getvalue()))])
        doc_id = response.json()['documents'][0]['id']
        context = self.client.get(f'/api/documents/{doc_id}/measurement-context?page=1').json()
        payload = {'page': 1, 'kind': 'area', 'source_fingerprint': context['source_fingerprint'],
                   'calibration': {'page': 1, 'document_id': doc_id, 'points': [[.1, .1], [.9, .1]], 'value': 8, 'unit': 'm'},
                   'geometry': [[.1, .1], [.9, .1], [.9, .9], [.1, .9]]}
        return doc_id, payload

    def test_new_image_can_be_measured_and_saved_without_any_model(self):
        doc_id, payload = self.measurement_source()
        with patch('server.llm._request', side_effect=AssertionError('Geometry must make no model request')):
            response = self.client.post(f'/api/documents/{doc_id}/measurement', json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        answer = response.json()
        self.assertAlmostEqual(answer['value'], 32)
        self.assertEqual(answer['unit'], 'm²')
        self.assertEqual(answer['usage']['model_calls'], 0)
        self.assertFalse(answer['evidence'][0]['source_verified'])
        self.assertEqual(answer['evidence'][0]['polygon'], payload['geometry'])
        saved = self.client.get('/api/answers/' + answer['id']).json()
        self.assertEqual(saved['value'], answer['value'])
        self.assertFalse(saved['source_changed'])

    def test_measurement_cannot_reuse_a_different_source_or_page_or_missing_scale(self):
        doc_id, payload = self.measurement_source()
        route = f'/api/documents/{doc_id}/measurement'
        changed = {**payload, 'source_fingerprint': '0' * 64}
        self.assertEqual(self.client.post(route, json=changed).status_code, 409)
        for calibration in ({}, {**payload['calibration'], 'page': 2},
                            {**payload['calibration'], 'document_id': 'other-drawing'}):
            response = self.client.post(route, json={**payload, 'calibration': calibration})
            self.assertEqual(response.status_code, 422, response.text)

    def test_visual_audit_requires_opt_in_and_caches_separately(self):
        doc_id, _ = self.measurement_source()
        initial = {'operation': 'count', 'value': 1, 'unit': 'count', 'method': 'vision',
                   'status': 'visual', 'answer': 'One candidate', 'warnings': [],
                   'evidence': [{'id': 'candidate', 'bbox': [.1, .1, .2, .2], 'page': 1, 'label': 'Door'}]}
        def audited(question, result, *args):
            return {**result, 'status': 'needs_review', 'count_audit': {'status': 'completed'}}
        payload = {'document_id': doc_id, 'question': 'How many doors?', 'mode': 'auto'}
        with patch('server.inventory.answer_inventory', return_value=initial) as inventory, \
             patch('server.visual_audit.audit_visual_count', side_effect=audited) as audit:
            unaudited = self.client.post('/api/ask', json=payload).json()
            first = self.client.post('/api/ask', json={**payload, 'verify_visual': True}).json()
            repeated = self.client.post('/api/ask', json={**payload, 'verify_visual': True}).json()
        self.assertEqual(audit.call_count, 1)
        self.assertEqual(inventory.call_count, 2)
        self.assertEqual(first['count_audit']['status'], 'completed')
        self.assertTrue(repeated['usage']['cache_hit'])
        self.assertNotEqual(first['id'], repeated['id'])
        self.assertNotIn('count_audit', unaudited)


class MeasurementSafety(unittest.TestCase):
    def result(self, quote='', verified=False):
        return {'operation': 'area', 'value': 24, 'unit': 'm²', 'status': 'needs_review',
                'answer': '24 m²', 'calculation': 'estimated from image',
                'evidence': [{'id': 'area', 'value': 24, 'unit': 'm²',
                              'quoted_text': quote, 'source_verified': verified}], 'warnings': []}

    def test_unscaled_visual_estimate_is_withheld(self):
        original = self.result('Assumed 0.9 m door width')
        checked = _guard_visual_measurements(original)
        self.assertIsNone(checked['value'])
        self.assertEqual(checked['status'], 'insufficient_evidence')
        self.assertEqual(original['value'], 24)

    def test_explicit_image_area_remains_provisional(self):
        result = _guard_visual_measurements(self.result('Room area 24 m²'))
        self.assertEqual(result['value'], 24)
        self.assertEqual(result['status'], 'needs_review')
        self.assertFalse(result['evidence'][0]['source_verified'])

    def test_incompatible_or_missing_source_values_cannot_support_area(self):
        for quote in ('Room area 42 m²', 'Wall length 24 m', ''):
            self.assertIsNone(_guard_visual_measurements(self.result(quote))['value'])
        empty = self.result()
        empty['evidence'] = []
        self.assertIsNone(_guard_visual_measurements(empty)['value'])

    def test_verified_native_operand_and_counts_are_preserved(self):
        native = self.result(verified=True)
        self.assertEqual(_guard_visual_measurements(native), native)
        count = {'operation': 'count', 'value': 4, 'evidence': [{}, {}, {}, {}]}
        self.assertEqual(_guard_visual_measurements(count), count)

    def test_rectangular_area_is_recomputed_from_explicit_dimensions(self):
        result = self.result('Width 4 m, height 10 ft')
        result['value'] = None
        checked = _guard_visual_measurements(result, 'What is the area of this rectangular room?')
        self.assertAlmostEqual(checked['value'], 12.192)
        self.assertEqual(checked['status'], 'needs_review')
        self.assertFalse(checked['evidence'][0]['source_verified'])

    def test_dimensions_do_not_imply_an_arbitrary_or_net_area(self):
        for question in ('What is the area of this L-shaped room?', 'What is the net area of this rectangular room?'):
            checked = _guard_visual_measurements(self.result('Width 4 m, height 3 m'), question)
            self.assertIsNone(checked['value'])


if __name__ == '__main__':
    unittest.main()

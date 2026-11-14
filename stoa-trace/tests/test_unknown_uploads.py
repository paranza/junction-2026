"""Regression checks for independent uploads and uncalibrated measurements."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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


if __name__ == '__main__':
    unittest.main()

"""End-to-end API checks using a real uploaded PDF and isolated storage."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

_temp = tempfile.TemporaryDirectory()
os.environ['STOA_RUNTIME_DIR'] = str(Path(_temp.name) / 'runtime')
os.environ['STOA_DATA_ROOT'] = str(Path(_temp.name) / 'dataset')
os.environ['STOA_ACCESS_TOKEN'] = ''

import pymupdf
from fastapi.testclient import TestClient
from server.app import app
from server import store


class ApiFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()
        pdf = pymupdf.open()
        page = pdf.new_page(width=600, height=400)
        page.insert_text((60, 80), 'Room A: 12.5 square metres')
        cls.pdf = pdf.tobytes()
        pdf.close()
        response = cls.client.post('/api/upload', files=[('files', ('../../drawing.pdf', cls.pdf, 'application/pdf'))])
        assert response.status_code == 200, response.text
        cls.doc = response.json()['documents'][0]

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def test_uploaded_pdf_can_be_extracted_and_rendered(self):
        detail = self.client.get('/api/documents/' + self.doc['id'])
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()['page_count'], 1)
        self.assertNotIn('absolute_path', detail.json()['document'])
        self.assertEqual(self.doc['name'].endswith('drawing.pdf'), True)
        image = self.client.get(f'/api/documents/{self.doc["id"]}/pages/1/image')
        self.assertEqual(image.status_code, 200)
        self.assertTrue(image.content.startswith(b'\x89PNG'))
        self.assertEqual(self.client.get(f'/api/documents/{self.doc["id"]}/pages/2/image').status_code, 422)

    def test_invalid_scope_region_and_missing_document(self):
        base = {'document_id': self.doc['id'], 'question': 'How many doors?', 'mode': 'native'}
        for extra in ({'region': [0.8, 0, 0.2, 1]}, {'region': [-0.1, 0, 1, 1]}, {'region': []}, {'page': 2}, {'scope': 'building'}):
            response = self.client.post('/api/ask', json={**base, **extra})
            self.assertEqual(response.status_code, 422, (extra, response.text))
        self.assertEqual(self.client.get('/api/documents/missing').status_code, 404)

    def test_unsupported_question_abstains_without_model(self):
        with patch('server.llm._request', side_effect=AssertionError('Native mode must not call the model')):
            response = self.client.post('/api/ask', json={'document_id': self.doc['id'], 'question': 'How many purple elephants?', 'mode': 'native'})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIsNone(result['value'])
        self.assertEqual(result['status'], 'insufficient_evidence')

    def test_review_is_recomputed_from_original_items(self):
        original = {'id': 'review-fixture', 'document_id': self.doc['id'], 'question': 'Doors?', 'answer': '2 doors',
                    'can_review': True, 'value': 2, 'unit': 'count', 'operation': 'count', 'warnings': [],
                    'evidence': [{'id': 'a', 'label': 'Door A'}, {'id': 'b', 'label': 'Door B'}]}
        store.save_answer(original['id'], self.doc['id'], original['question'], original)
        route = '/api/answers/review-fixture/review'
        for excluded, value in [(['a'], 1), (['a'], 1), ([], 2), (['a', 'b'], 0)]:
            response = self.client.post(route, json={'excluded_evidence_ids': excluded})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['value'], value)
        self.assertEqual(self.client.post(route, json={'excluded_evidence_ids': ['unknown']}).status_code, 422)
        recent = self.client.get('/api/answers?limit=12').json()['answers']
        persisted = next(item for item in recent if item['id'] == original['id'])
        self.assertEqual(persisted['value'], 0)
        self.assertEqual(persisted['excluded_evidence_ids'], ['a', 'b'])

    def test_invalid_uploads_do_not_create_documents(self):
        for name, content, expected in [('script.sh', b'echo hello', 415), ('empty.pdf', b'', 422)]:
            response = self.client.post('/api/upload', files=[('files', (name, content))])
            self.assertEqual(response.status_code, expected)


if __name__ == '__main__':
    unittest.main()

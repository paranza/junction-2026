"""Session costs include failed inference and never recharge cached answers."""
import io
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from server import app as api, llm, store


class SessionApi(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        for name in ('', 'cache', 'previews', 'uploads'):
            (root / 'runtime' / name).mkdir(parents=True, exist_ok=True)
        self.patches = [patch.object(store, 'RUNTIME', root / 'runtime'),
                        patch.object(store, 'DATA_ROOT', root / 'dataset')]
        for item in self.patches:
            item.start()
        self.client = TestClient(api.app).__enter__()
        picture = io.BytesIO()
        Image.new('RGB', (100, 100), 'white').save(picture, format='PNG')
        self.doc = self.client.post('/api/upload', files={'files': ('session.png', picture.getvalue(), 'image/png')}).json()['documents'][0]
        self.session = str(uuid.uuid4())

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for item in reversed(self.patches):
            item.stop()
        self.folder.cleanup()

    def ask(self, **extra):
        return self.client.post('/api/ask', json={'document_id': self.doc['id'],
            'question': 'How many doors?', 'session_id': self.session, **extra})

    def test_cached_native_messages_remain_distinct_and_do_not_add_inference_cost(self):
        native = {'value': 1, 'unit': 'count', 'method': 'native', 'status': 'supported', 'evidence': []}
        with patch.object(api, '_compute_analysis', return_value=native) as compute:
            first = self.ask(mode='native').json()
            second = self.ask(mode='native').json()
        self.assertEqual(compute.call_count, 1)
        self.assertNotEqual(first['message_id'], second['message_id'])
        self.assertTrue(second['usage']['cache_hit'])
        summary = self.client.get('/api/usage', params={'session_id': self.session}).json()
        self.assertEqual(summary['message_count'], 2)
        self.assertEqual(summary['aggregate']['model_calls'], 0)
        self.assertEqual(summary['aggregate']['cost_estimate_usd'], 0)
        self.assertTrue(all(row['status'] == 'completed' for row in summary['by_message']))

    def test_retryable_partial_analysis_does_not_trap_a_question_in_the_answer_cache(self):
        partial={'value':None,'unit':'m','operation':'length','method':'source_inspection_agent',
            'status':'insufficient_evidence','evidence':[],'retryable_analysis':True}
        completed={'value':12,'unit':'m','operation':'length','method':'source_inspection_agent',
            'status':'needs_review','evidence':[]}
        with patch.object(api,'_compute_analysis',side_effect=[partial,completed]) as compute:
            first=self.ask(mode='auto',question='How many metres of pipe are shown?').json()
            second=self.ask(mode='auto',question='How many metres of pipe are shown?').json()
            third=self.ask(mode='auto',question='How many metres of pipe are shown?').json()
        self.assertIsNone(first['value']);self.assertFalse(second['usage']['cache_hit'])
        self.assertEqual(second['value'],12);self.assertEqual(third['value'],12)
        self.assertTrue(third['usage']['cache_hit']);self.assertEqual(compute.call_count,2)
        original=self.client.get('/api/answers/'+first['id']).json()
        self.assertIsNone(original['value'])

    def test_incomplete_provider_answer_keeps_reported_cost_and_isolates_sessions(self):
        body = {'status': 'incomplete', 'usage': {'input_tokens': 100, 'output_tokens': 200,
                'input_tokens_details': {'cached_tokens': 0}}, 'output': []}
        def request_inventory(*args, **kwargs):
            return llm._request([{'type': 'input_text', 'text': 'Read the source.'}], max_tokens=512)
        with patch.object(llm, 'PROVIDER', 'gemini'), patch.object(llm, 'MODEL', 'gemini-4-carbon'), \
             patch.object(llm, 'KEY', 'test-key'), patch.object(llm, 'MAX_CALLS', 10), \
             patch.object(llm.gemini_provider, 'request', return_value=body), \
             patch('server.native_qa.answer_native', return_value=None), \
             patch('server.inventory.answer_inventory', side_effect=request_inventory):
            response = self.ask()
        self.assertEqual(response.status_code, 503, response.text)
        detail = response.json()['detail']
        self.assertEqual(detail['usage']['model_calls'], 1)
        self.assertAlmostEqual(detail['usage']['cost_estimate_usd'], .0022)
        summary = self.client.get('/api/usage', params={'session_id': self.session}).json()
        self.assertEqual(summary['aggregate']['model_calls'], 1)
        self.assertAlmostEqual(summary['aggregate']['cost_estimate_usd'], .0022)
        self.assertEqual(summary['by_message'][0]['request_id'], detail['message_id'])
        self.assertEqual(summary['by_message'][0]['status'], 'error')
        other = self.client.get('/api/usage', params={'session_id': str(uuid.uuid4())}).json()
        self.assertEqual(other['message_count'], 0)
        self.assertEqual(other['aggregate']['model_calls'], 0)


if __name__ == '__main__':
    unittest.main()

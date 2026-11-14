"""Concurrent model requests keep exact usage records without sharing counters."""
import os
import threading
import unittest
from unittest.mock import patch

from server import gemini_provider, llm


def body(tokens):
    return {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': '{"objects": []}'}]}],
            'usage': {'input_tokens': tokens, 'output_tokens': tokens // 10, 'input_tokens_details': {'cached_tokens': 0},
                      'output_tokens_details': {'reasoning_tokens': 0}}}


class ParallelRequests(unittest.TestCase):
    def setUp(self):
        self.patches = [patch.object(llm, 'PROVIDER', 'gemini'), patch.object(llm, 'KEY', 'private-test-key'),
                        patch.object(llm, 'MODEL', 'gemini-4-argon'), patch.object(llm, 'MAX_CALLS', 50),
                        patch.dict(os.environ, {'STOA_GEMINI_IMAGE_RESOLUTION': 'high'}),
                        patch.object(llm.store, 'reserve_model_request', return_value=True),
                        patch.object(llm.store, 'record_event')]
        started = [item.start() for item in self.patches]
        self.reserve = started[-2]
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def request(self):
        return llm._request([{'type': 'input_text', 'text': 'Count doors'}], max_tokens=2000)

    def test_usage_of_concurrent_requests_is_merged_into_the_caller(self):
        barrier, lock, tokens = threading.Barrier(2, timeout=10), threading.Lock(), [100, 300]
        def reply(payload, key):
            barrier.wait()  # both requests must be in flight at once
            with lock:
                return body(tokens.pop(0))
        with patch.object(gemini_provider, 'request', side_effect=reply), \
                llm.usage_scope(session_id='session-1', message_id='message-1'):
            results = llm.run_in_parallel([self.request, self.request])
            ledger = llm._usage.get()
            self.assertEqual((ledger['model_calls'], ledger['input_tokens'], ledger['output_tokens']), (2, 400, 40))
            self.assertEqual(len(ledger['_calls']), 2)
            self.assertEqual(llm.usage_snapshot()['model_calls'], 2)
        self.assertEqual(len(results), 2)
        calls = self.reserve.call_args_list
        self.assertEqual(len(calls), 2)
        for call in calls:
            self.assertEqual((call.args[1]['session_id'], call.args[1]['message_id']), ('session-1', 'message-1'))

    def test_an_error_is_raised_after_usage_is_merged(self):
        def reply(payload, key):
            raise gemini_provider.ProviderError('Gemini could not complete this request.')
        with patch.object(gemini_provider, 'request', side_effect=reply), llm.usage_scope():
            with self.assertRaises(llm.ModelError):
                llm.run_in_parallel([self.request, self.request])
            self.assertEqual(llm.usage_snapshot()['model_calls'], 2)

    def test_without_a_usage_scope_results_are_returned(self):
        with patch.object(gemini_provider, 'request', side_effect=lambda payload, key: body(10)):
            self.assertEqual(len(llm.run_in_parallel([self.request] * 3)), 3)


if __name__ == '__main__':
    unittest.main()

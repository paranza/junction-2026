"""Accounting tests use mocked transports and isolated SQLite only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from server import costs, gemini_provider, llm, store

NOW = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)


def usage(input_tokens=100, output_tokens=20, cached=0):
    return {'input_tokens': input_tokens, 'output_tokens': output_tokens,
            'input_tokens_details': {'cached_tokens': cached}}


def response(status='completed'):
    return {'status': status, 'usage': usage(),
            'output': [{'content': [{'type': 'output_text', 'text': '{"ok":true}'}]}]}


class TokenPricing(unittest.TestCase):
    def test_argon_uses_its_published_price_and_expiry(self):
        result=costs.summarize_calls([{'model':'gemini/gemini-4-argon','created':NOW.timestamp(),
                                      'usage':usage(1_000_000,100_000,500_000)}])
        self.assertEqual(result['cost_estimate_usd'],2.05)
        self.assertIsNone(costs.rates_for('gemini/gemini-4-argon',datetime(2026,12,1,tzinfo=timezone.utc)))

    def test_dated_prices_count_uncached_cached_and_thought_output_once(self):
        result = costs.summarize_calls([{'model': 'gemini/gemini-4-carbon',
                                        'created': NOW.timestamp(), 'usage': usage(100, 10, 20)}])
        self.assertEqual(result['cost_estimate_usd'], .000262)
        self.assertEqual(result['cost_basis'], 'published_rates')
        self.assertEqual(result['model_usage'][0]['pricing']['valid_until'], '2026-12-01T00:00:00Z')

    def test_missing_or_expired_prices_remain_unknown(self):
        for model, at in [('gemini/unknown-model', NOW), ('gemini/gemini-4-carbon', datetime(2026, 12, 1, tzinfo=timezone.utc))]:
            result = costs.summarize_calls([{'model': model, 'created': at.timestamp(), 'usage': usage()}])
            self.assertIsNone(result['cost_estimate_usd'])
            self.assertEqual(result['input_tokens'], 100)
            self.assertEqual(result['cost_unavailable_calls'], 1)

    def test_free_model_and_no_model_calls_are_distinct_from_unknown_usage(self):
        free = costs.summarize_calls([{'model': 'gemini/gemma-4-31b-it', 'created': NOW.timestamp(), 'usage': usage()}])
        self.assertEqual(free['cost_estimate_usd'], 0)
        self.assertEqual(free['model_calls'], 1)
        native = costs.summarize_calls([], cache_hit=True)
        self.assertEqual(native['model_calls'], 0)
        self.assertTrue(native['cache_hit'])
        self.assertEqual(native['cost_estimate_usd'], 0)
        unknown = costs.summarize_calls([{'model': 'gemini/gemma-4-31b-it', 'created': NOW.timestamp(), 'usage': None}])
        self.assertIsNone(unknown['cost_estimate_usd'])
        self.assertTrue(unknown['usage_incomplete'])

    def test_mixed_models_price_separately_and_partial_totals_are_not_a_total(self):
        calls = [{'model': 'gemini/gemini-4-carbon', 'created': NOW.timestamp(), 'usage': usage()},
                 {'model': 'gemini/gemma-4-31b-it', 'created': NOW.timestamp(), 'usage': usage()}]
        result = costs.summarize_calls(calls)
        self.assertEqual(result['cost_estimate_usd'], .0004)
        calls.append({'model': 'other/unknown', 'created': NOW.timestamp(), 'usage': usage()})
        result = costs.summarize_calls(calls)
        self.assertIsNone(result['cost_estimate_usd'])
        self.assertEqual(result['cost_known_usd'], .0004)

    def test_bad_usage_or_override_never_becomes_zero_cost(self):
        for bad in (usage(-1), usage(cached=101), usage(output_tokens='20'), {}):
            self.assertIsNone(costs.normalize_usage(bad))
        with patch.dict('os.environ', {'STOA_PRICE_MODEL': 'gemini/gemini-4-carbon',
                                      'STOA_INPUT_USD_PER_MILLION': 'nan', 'STOA_OUTPUT_USD_PER_MILLION': '2'}):
            self.assertIsNone(costs.rates_for('gemini/gemini-4-carbon', NOW))


class SessionAccounting(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        patches = [patch.object(store, 'RUNTIME', self.root), patch.object(store, 'DATA_ROOT', self.root / 'no-data'),
                   patch.object(llm, 'PROVIDER', 'gemini'), patch.object(llm, 'MODEL', 'gemini-4-carbon'),
                   patch.object(llm, 'KEY', 'mock-key'), patch.object(llm, 'MAX_CALLS', 100),
                   patch.object(gemini_provider, 'request', return_value=response())]
        values = [p.start() for p in patches]
        self.transport = values[-1]
        self.addCleanup(lambda: [p.stop() for p in reversed(patches)])
        self.addCleanup(self.folder.cleanup)
        store.initialize()

    def message(self, message_id, *, model=None, status='completed'):
        store.record_message_usage('session-one', message_id, {}, 'How many doors?', 'pending')
        with llm.usage_scope(session_id='session-one', message_id=message_id):
            try:
                llm._request([], model=model)
            except llm.ModelError:
                snapshot = llm.usage_snapshot()
                store.record_message_usage('session-one', message_id, snapshot, 'How many doors?', 'error')
                return snapshot
            snapshot = llm.usage_snapshot()
            store.record_message_usage('session-one', message_id, snapshot, 'How many doors?', status, 'answer-' + message_id)
            return snapshot

    def test_success_cached_and_pending_metadata_are_not_double_charged(self):
        first = self.message('first')
        with llm.usage_scope(session_id='session-one', message_id='cached'):
            cached = llm.usage_snapshot(cache_hit=True)
        store.record_message_usage('session-one', 'cached', cached, 'Same question', 'completed', 'answer-cached')
        store.record_message_usage('session-one', 'cached', cached, 'Same question', 'completed', 'answer-cached')
        result = store.session_usage('session-one')
        self.assertEqual(result['message_count'], 2)
        self.assertEqual(result['usage']['model_calls'], 1)
        self.assertEqual(result['usage']['input_tokens'], first['input_tokens'])
        self.assertEqual(result['usage']['cost_estimate_usd'], first['cost_estimate_usd'])
        self.assertTrue(result['messages'][1]['usage']['cache_hit'])
        self.assertEqual(result['messages'][1]['usage']['cost_estimate_usd'], 0)
        self.assertGreater(result['revision'], 0)

    def test_failed_structured_result_keeps_provider_reported_tokens(self):
        self.transport.return_value = response(status='incomplete')
        snapshot = self.message('failed')
        stored = store.session_usage('session-one')['messages'][0]
        self.assertEqual(stored['status'], 'error')
        self.assertEqual(stored['usage']['model_calls'], 1)
        self.assertEqual(stored['usage']['output_tokens'], 20)
        self.assertEqual(stored['usage']['cost_estimate_usd'], snapshot['cost_estimate_usd'])

    def test_transport_failure_and_running_attempt_remain_unknown(self):
        self.transport.side_effect = gemini_provider.ProviderError('Provider unavailable')
        self.message('failed-network')
        result = store.session_usage('session-one')
        self.assertIsNone(result['usage']['cost_estimate_usd'])
        self.assertTrue(result['usage']['usage_incomplete'])
        self.assertEqual(result['usage']['model_calls'], 1)
        self.assertEqual(store.session_usage('different-session')['message_count'], 0)

    def test_duplicate_response_events_do_not_double_count_or_mix_messages(self):
        self.message('first')
        with store.connection() as db:
            record = json.loads(db.execute("SELECT detail FROM events WHERE kind='model_response'").fetchone()[0])
        before = store.session_usage('session-one')
        store.record_event('model_response', record)
        after = store.session_usage('session-one')
        self.assertEqual(after['usage'], before['usage'])
        self.assertGreater(after['revision'], before['revision'])
        record['message_id'] = 'other-message'
        store.record_event('model_response', record)
        self.assertIsNone(store.session_usage('session-one')['usage']['cost_estimate_usd'])

    def test_concurrent_usage_contexts_are_isolated_and_persisted(self):
        barrier = threading.Barrier(2)
        def respond(payload, key):
            barrier.wait(timeout=5)
            return response()
        self.transport.side_effect = respond
        with ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(self.message, ['one', 'two']))
        self.assertTrue(all(v['model_calls'] == 1 for v in values))
        result = store.session_usage('session-one')
        self.assertEqual(result['message_count'], 2)
        self.assertEqual(result['usage']['model_calls'], 2)
        self.assertTrue(all(m['usage']['model_calls'] == 1 for m in result['messages']))
        with store.connection() as db:
            details = [json.loads(r[0]) for r in db.execute("SELECT detail FROM events WHERE kind='model_request'")]
        self.assertEqual(len({r['request_id'] for r in details}), 2)
        self.assertEqual({r['message_id'] for r in details}, {'one', 'two'})
        self.assertNotIn('mock-key', json.dumps(details))


if __name__ == '__main__':
    unittest.main()

"""Model-free checks for label isolation, resumability and bulk stopping rules."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

OPS = Path(__file__).resolve().parents[1] / 'ops'
sys.path.insert(0, str(OPS))
import bulk_evaluate as bulk


def case(identity, path='data/cubicasa5k/a.png', question='How many windows are shown on this floor plan?', expected=3, language='en'):
    return {'id': identity, 'path': path, 'question': question, 'expected': expected, 'unit': 'count',
            'type': 'count', 'source': 'cubicasa5k', 'group': path, 'language_hint': language}


def response(value=3, calls=0):
    return {'answer': str(value), 'value': value, 'unit': 'count', 'status': 'needs_review',
            'method': 'visual_inventory', 'evidence': [], 'usage': {'model_calls': calls,
            'input_tokens': calls * 100, 'output_tokens': calls * 10, 'cost_estimate_usd': None if calls else 0}}


class BulkEvaluation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'private.jsonl'
        self.identity = {'model': 'test-model', 'revision': 'test', 'verify_visual': False}

    def checkpoint(self, cases, **kwargs):
        check = bulk.Checkpoint(self.path, self.identity, cases, **kwargs)
        self.addCleanup(check.close)
        return check

    def test_all_raw_questions_run_without_transferring_labels_and_one_inventory_per_image(self):
        cases = [case('en'), case('fi', question='Kuinka monta ikkunaa pohjapiirustuksessa on?', language='fi'),
                 case('other', path='data/cubicasa5k/b.png', expected=999)]
        catalog = {c['path']: {'id': c['path']} for c in cases}
        seen, requests, guard = set(), [], threading.Lock()
        def ask(payload):
            self.assertEqual(set(payload), {'document_id', 'question', 'page', 'scope', 'mode', 'verify_visual'})
            self.assertFalse(payload['verify_visual'])
            with guard:
                calls = int(payload['document_id'] not in seen)
                seen.add(payload['document_id']); requests.append(payload)
            return response(calls=calls)
        check = self.checkpoint(cases)
        run = bulk.Evaluation(cases, catalog, check, ask, max_model_calls=5, concurrency=2)
        self.assertIsNone(run.run())
        report = bulk.summarize(cases, check.rows, self.identity)
        self.assertEqual(len(requests), 3)
        self.assertEqual(report['unique_normalized_requests'], 2)
        self.assertEqual(report['all_selected']['numeric_correct'], 2)
        self.assertEqual(report['all_selected']['usage']['model_calls'], 2)
        self.assertEqual(report['unique_normalized']['numeric_correct'], 1)
        self.assertEqual(report['by_category']['window']['cases'], 3)

    def test_resume_keeps_completed_error_and_success_without_paid_retries(self):
        cases = [case('first'), case('second', path='data/cubicasa5k/b.png')]
        check = bulk.Checkpoint(self.path, self.identity, cases)
        check.append(bulk.result_row(cases[0], error_code='http_503'))
        check.close()
        resumed = self.checkpoint(cases, resume=True)
        asked = []
        def ask(payload):
            asked.append(payload['document_id']); return response(calls=1)
        run = bulk.Evaluation(cases, {c['path']: {'id': c['id']} for c in cases}, resumed, ask, max_model_calls=5)
        run.run()
        self.assertEqual(asked, ['second'])
        self.assertEqual(len(resumed.rows), 2)
        self.assertEqual(run.unknown_failures, 1)
        self.assertIn('error', resumed.rows['first'])

    def test_existing_or_changed_checkpoint_never_silently_overwrites(self):
        cases = [case('first')]
        check = bulk.Checkpoint(self.path, self.identity, cases)
        check.append(bulk.result_row(cases[0], response()))
        check.close()
        original = self.path.read_bytes()
        for identity, resume in ((self.identity, False), ({**self.identity, 'model': 'different'}, True)):
            with self.assertRaises(ValueError):
                bulk.Checkpoint(self.path, identity, cases, resume)
        self.assertEqual(self.path.read_bytes(), original)
        with self.path.open('a') as stream:
            stream.write(self.path.read_text().splitlines()[0] + '\n')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            bulk.Checkpoint(self.path, self.identity, cases, True)

    def test_checkpoint_rejects_foreign_cases_and_concurrent_writer(self):
        cases = [case('first')]
        check = self.checkpoint(cases)
        with self.assertRaisesRegex(ValueError, 'locked'):
            bulk.Checkpoint(self.path, self.identity, cases, True)
        check.append(bulk.result_row(cases[0], response()))
        with self.assertRaises(ValueError):
            bulk.Checkpoint(self.path, self.identity, [case('other')], True)

    def test_fatal_configuration_failure_stops_immediately(self):
        cases = [case(str(i), question=f'Count window {i}') for i in range(5)]
        check = self.checkpoint(cases)
        asked = []
        def ask(payload):
            asked.append(payload); raise bulk.ApiError('http_503', fatal=True)
        run = bulk.Evaluation(cases, {cases[0]['path']: {'id': 'doc'}}, check, ask, concurrency=1)
        self.assertEqual(run.run(), 'fatal_api_or_configuration_failure')
        self.assertEqual(len(asked), 1)
        self.assertEqual(run.unknown_failures, 1)

    def test_three_consecutive_failures_stop_without_retry(self):
        cases = [case(str(i), path=f'data/cubicasa5k/{i}.png') for i in range(6)]
        check = self.checkpoint(cases)
        asked = []
        def ask(payload):
            asked.append(payload); raise bulk.ApiError('http_429')
        run = bulk.Evaluation(cases, {c['path']: {'id': c['id']} for c in cases}, check, ask, concurrency=1)
        self.assertEqual(run.run(), 'three_consecutive_failures')
        self.assertEqual(len(asked), 3)

    def test_failed_shared_inventory_is_not_retried_by_other_questions_or_resume(self):
        cases = [case('first'), case('second', question='How many doors are shown on this floor plan?')]
        check = bulk.Checkpoint(self.path, self.identity, cases)
        requests = []
        def ask(payload):
            requests.append(payload)
            raise bulk.ApiError('http_503')
        catalog = {cases[0]['path']: {'id': 'doc'}}
        run = bulk.Evaluation(cases, catalog, check, ask, concurrency=4)
        self.assertIsNone(run.run())
        self.assertEqual(len(requests), 1)
        report = bulk.summarize(cases, check.rows, self.identity)
        self.assertEqual(report['drawing_groups_with_errors'], 1)
        self.assertEqual(report['unrun_questions_in_failed_drawings'], 1)
        self.assertEqual(report['failed_requests_with_unknown_provider_usage'], 1)
        self.assertFalse(report['provider_usage_complete'])
        self.assertEqual(report['all_selected']['usage']['model_calls'], 0)
        check.close()
        resumed = self.checkpoint(cases, resume=True)
        bulk.Evaluation(cases, catalog, resumed, ask, concurrency=4).run()
        self.assertEqual(len(requests), 1)

    def test_concurrent_failures_stop_with_at_most_three_plus_in_flight_requests(self):
        cases = [case(str(i), path=f'data/cubicasa5k/{i}.png') for i in range(198)]
        check = self.checkpoint(cases)
        barrier, lock, requests = threading.Barrier(4), threading.Lock(), []
        def ask(payload):
            with lock:
                requests.append(payload)
                number = len(requests)
            if number <= 4:
                barrier.wait(timeout=5)
            raise bulk.ApiError('http_503')
        catalog = {c['path']: {'id': c['id']} for c in cases}
        run = bulk.Evaluation(cases, catalog, check, ask, concurrency=4)
        self.assertEqual(run.run(), 'three_consecutive_failures')
        self.assertGreaterEqual(len(requests), 4)
        self.assertLessEqual(len(requests), 3 + 4 - 1)
        self.assertEqual(run.unknown_failures, len(requests))
        self.assertEqual(len(check.rows), len(requests))
        self.assertTrue(all(r['error'] == 'http_503' for r in check.rows.values()))

    def test_budget_stop_retains_unrun_questions_in_full_denominator(self):
        cases = [case('first'), case('second', path='data/cubicasa5k/b.png')]
        check = self.checkpoint(cases)
        run = bulk.Evaluation(cases, {c['path']: {'id': c['id']} for c in cases}, check,
                              lambda payload: response(calls=1), max_model_calls=1, concurrency=1)
        reason = run.run()
        self.assertEqual(reason, 'client_observed_model_budget')
        report = bulk.summarize(cases, check.rows, self.identity, reason)
        self.assertEqual(report['completed_questions'], 1)
        self.assertEqual(report['unrun_questions'], 1)
        self.assertEqual(report['all_selected']['numeric_correct'], 1)
        self.assertEqual(report['all_selected']['numeric_cases'], 2)
        self.assertEqual(report['completed_only']['numeric_cases'], 1)

    def test_unique_aggregation_uses_fixed_english_preference_and_reports_disagreement(self):
        cases = [case('fi', question='Kuinka monta ikkunaa pohjapiirustuksessa on?', language='fi'), case('en')]
        rows = {c['id']: bulk.result_row(c, response(3 if c['id'] == 'fi' else 7)) for c in cases}
        report = bulk.summarize(cases, rows, self.identity)
        self.assertEqual(report['unique_normalized']['numeric_cases'], 1)
        self.assertEqual(report['unique_normalized']['numeric_correct'], 0)
        self.assertEqual(report['duplicate_groups_with_response_disagreement'], 1)

    def test_manifest_hash_and_duplicate_selection_are_checked(self):
        path = Path(self.temp.name) / 'dev.json'
        cases = [case('first')]
        path.write_text(json.dumps({'cases': cases, 'cases_sha256': bulk.benchmark.canonical_hash(cases)}))
        self.assertEqual(len(bulk.load_cases(path, 'cubicasa5k')[1]), 1)
        with self.assertRaises(ValueError):
            bulk.load_cases(path, 'other')
        cases[0]['expected'] = 888
        path.write_text(json.dumps({'cases': cases, 'cases_sha256': 'wrong'}))
        with self.assertRaises(ValueError):
            bulk.load_cases(path, 'cubicasa5k')

    def test_summary_cannot_overwrite_checkpoint_or_its_metadata(self):
        for summary in (self.path, Path(str(self.path) + '.meta.json'), self.path.with_suffix('.json')):
            output = self.path if summary.suffix != '.json' or summary.name.endswith('meta.json') else summary.with_suffix('.md')
            with self.subTest(summary=summary), patch.object(bulk, 'Client', side_effect=AssertionError('No network expected')):
                with self.assertRaises(SystemExit):
                    bulk.main(['--manifest', '/missing/dev.json', '--source', 'cubicasa5k', '--mode', 'native',
                               '--code-revision', 'abcdef1', '--max-model-calls', '0',
                               '--output', str(output), '--summary', str(summary)])


if __name__ == '__main__':
    unittest.main()

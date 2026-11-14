import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('trace_batch_answers', Path(__file__).resolve().parents[1] / 'ops/batch_answers.py')
batch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = batch
spec.loader.exec_module(batch)


class FakeClient:
    def __init__(self, documents=None):
        self.catalog = documents or [{'id': 'floor', 'path': 'data/project/floor.pdf'}]
        self.asks, self.uploads = [], []

    def documents(self):
        return self.catalog

    def ask(self, payload):
        self.asks.append(payload)
        if payload['question'] == 'fail please':
            raise batch.BatchError('http_error', 'Trace API returned HTTP 503; request was not retried.')
        return {'id': 'answer', 'answer': '2', 'value': 2, 'unit': 'count', 'method': 'native_fixture',
                'status': 'supported', 'evidence': [{'id': 'door1'}, {'id': 'door2'}], 'usage': {'model_calls': 0}}

    def upload(self, path):
        self.uploads.append(path)
        return {'id': 'uploaded', 'path': 'uploads/generated-' + path.name}


class BatchAnswers(unittest.TestCase):
    def test_exact_path_and_ambiguous_basename_do_not_select_another_source(self):
        docs = [{'id': 'a', 'path': 'data/a/floor.pdf'}, {'id': 'b', 'path': 'data/b/floor.pdf'}]
        self.assertEqual(batch.resolve_document('data/b/floor.pdf', docs)['id'], 'b')
        with self.assertRaises(batch.BatchError):
            batch.resolve_document('floor.pdf', docs)
        self.assertIsNone(batch.resolve_document('data/c/floor.pdf', docs[:1]))

    def test_catalog_pagination_deduplicates_identifiers(self):
        client = batch.Client('http://127.0.0.1:8787', environ={})
        replies = [{'documents': [{'id': 'a', 'path': 'a.pdf'}], 'total': 3},
                   {'documents': [{'id': 'a', 'path': 'a.pdf'}, {'id': 'b', 'path': 'b.pdf'}], 'total': 3}]
        with patch.object(client, 'api', side_effect=replies) as api:
            self.assertEqual([doc['id'] for doc in client.documents()], ['a', 'b'])
        self.assertIn('offset=1', api.call_args_list[1].args[0])

    def test_gold_labels_and_per_row_mode_never_reach_the_server(self):
        client = FakeClient()
        row = {'path': 'data/project/floor.pdf', 'question': 'How many doors?', 'expected': 99,
               'gold': 'hidden', 'answer': 99, 'type': 'count', 'unit': 'count', 'mode': 'vision'}
        result = list(batch.process_rows([(1, row, None)], client))[0]
        self.assertEqual(set(client.asks[0]), {'document_id', 'question', 'page', 'scope', 'mode'})
        self.assertEqual(client.asks[0]['mode'], 'native')
        self.assertEqual(result['value'], 2)
        self.assertNotIn('expected', result)
        self.assertNotIn('gold', result)

    def test_row_errors_and_api_failure_do_not_abort_later_questions(self):
        client = FakeClient()
        rows = [(1, {'path': 'floor.pdf', 'question': 'How many?', 'page': 0}, None),
                (2, {'path': 'floor.pdf', 'question': 'fail please'}, None),
                (3, {'path': 'floor.pdf', 'question': 'How many?', 'scope': []}, None),
                (4, {'path': 'floor.pdf', 'question': 'How many?', 'scope': 'page', 'page': '2'}, None)]
        output = list(batch.process_rows(rows, client))
        self.assertEqual([row['status'] for row in output], ['error', 'error', 'error', 'supported'])
        self.assertEqual(len(client.asks), 2)  # failed POST is not retried
        self.assertEqual(client.asks[-1]['page'], 2)

    def test_malformed_json_line_is_reported_and_csv_optional_columns_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'questions.jsonl'
            path.write_text('{broken\n' + json.dumps({'path': 'floor.pdf', 'question': 'How many?'}) + '\n')
            output = list(batch.process_rows(batch.input_rows(path), FakeClient()))
            self.assertEqual([row['status'] for row in output], ['error', 'supported'])
            path = Path(tmp) / 'questions.csv'
            path.write_text('path,question,page,scope,expected\nfloor.pdf,How many?,2,page,99\n')
            client = FakeClient()
            self.assertEqual(list(batch.process_rows(batch.input_rows(path), client))[0]['status'], 'supported')
            self.assertEqual(client.asks[0]['scope'], 'page')

    def test_upload_is_explicit_bounded_and_reused_for_repeated_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'root'
            root.mkdir()
            (root / 'new.pdf').write_bytes(b'%PDF-example')
            outside = Path(tmp) / 'outside.pdf'
            outside.write_bytes(b'not allowed')
            (root / 'escape.pdf').symlink_to(outside)
            rows = [(1, {'path': 'new.pdf', 'question': 'How many?'}, None),
                    (2, {'path': 'new.pdf', 'question': 'How many windows?'}, None),
                    (3, {'path': 'escape.pdf', 'question': 'How many?'}, None)]
            client = FakeClient()
            output = list(batch.process_rows(rows, client, input_root=root.resolve(), upload_unmatched=True))
            self.assertEqual([row['status'] for row in output], ['supported', 'supported', 'error'])
            self.assertEqual(len(client.uploads), 1)
            self.assertEqual(output[-1]['error']['kind'], 'outside_input_root')
            with self.assertRaises(batch.BatchError):
                batch.normalized_path('../outside.pdf')

    def test_paid_modes_require_opt_in_before_any_api_call(self):
        client = FakeClient()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            batch.main(['--input', 'questions.jsonl', '--output', 'answers.jsonl', '--mode', 'auto'], client=client)
        self.assertEqual(exc.exception.code, 2)
        self.assertEqual(client.asks, [])

    def test_url_and_credentials_are_not_accepted_in_arguments_or_redirects(self):
        for url in ('file:///tmp/data', 'https://name:secret@example.test', 'https://example.test?token=secret'):
            with self.assertRaises(ValueError):
                batch.Client(url, environ={})
        with self.assertRaises(ValueError):
            batch.Client('http://example.test', environ={'STOA_ACCESS_TOKEN': 'secret'})
        client = batch.Client('https://example.test', environ={'STOA_ACCESS_USERNAME': 'user', 'STOA_ACCESS_PASSWORD': 'secret', 'STOA_ACCESS_TOKEN': 'token'})
        self.assertIn('Authorization', client.headers)
        self.assertEqual(client.headers['X-Trace-Token'], 'token')
        self.assertIsNone(batch.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.test'))

    def test_main_output_contains_answers_not_labels_and_nonzero_for_row_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'in.jsonl', Path(tmp) / 'out.jsonl'
            source.write_text(json.dumps({'path': 'floor.pdf', 'question': 'How many?', 'expected': 99}) + '\n' + '{}\n')
            with contextlib.redirect_stderr(io.StringIO()) as err:
                code = batch.main(['--input', str(source), '--output', str(output)], client=FakeClient())
            rows = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(code, 1)
            self.assertEqual(rows[0]['value'], 2)
            self.assertNotIn('expected', output.read_text())
            self.assertEqual(rows[1]['status'], 'error')
            self.assertNotIn('secret', err.getvalue())


if __name__ == '__main__':
    unittest.main()

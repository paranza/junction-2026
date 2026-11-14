"""Read-only catalog checks use fixed URLs and never expose provider credentials."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ops'))
import check_gemini


class GeminiCatalogTests(unittest.TestCase):
    def test_lists_current_configured_model_with_header_and_no_inference(self):
        body = {'models': [{'name': 'models/gemini-4-carbon', 'inputTokenLimit': 1048576,
                            'outputTokenLimit': 65536, 'thinking': True,
                            'supportedGenerationMethods': ['generateContent']} ]}
        with patch.object(check_gemini, 'request_json', return_value=body) as request:
            result = check_gemini.check_catalog({'GEMINI_API_KEY': 'private-test-key', 'STOA_MODEL': 'gemini-4-carbon'})
        self.assertTrue(result['selected_model_listed'])
        self.assertEqual(result['inference']['status'], 'not_requested')
        self.assertEqual(request.call_args.args[0], check_gemini.MODELS_ENDPOINT + '?pageSize=1000')
        self.assertEqual(request.call_args.kwargs['headers'], {'x-goog-api-key': 'private-test-key'})
        self.assertNotIn('private-test-key', json.dumps(result))
        self.assertNotIn('key=', request.call_args.args[0])
        self.assertEqual(request.call_args.kwargs['retries'], 0)

    def test_pagination_and_base_model_alias_are_supported(self):
        pages = [{'models': [{'name': 'models/gemini-4-argon'}], 'nextPageToken': 'a/+&b'},
                 {'models': [{'name': 'models/gemini-4-carbon-001', 'baseModelId': 'gemini-4-carbon'}]}]
        with patch.object(check_gemini, 'request_json', side_effect=pages) as request:
            result = check_gemini.check_catalog({'GEMINI_API_KEY': 'test', 'STOA_MODEL': 'models/gemini-4-carbon'})
        self.assertTrue(result['selected_model_listed'])
        self.assertEqual(result['models_count'], 2)
        self.assertIn('pageToken=a%2F%2B%26b', request.call_args.args[0])

    def test_missing_key_does_not_request_and_blank_key_disables_alias(self):
        with patch.object(check_gemini, 'request_json') as request:
            result = check_gemini.check_catalog({'GEMINI_API_KEY': '', 'GOOGLE_API_KEY': 'alias-key'})
        self.assertEqual(result['status'], 'missing_credentials')
        request.assert_not_called()

    def test_absent_model_is_reported_without_inventing_access(self):
        with patch.object(check_gemini, 'request_json', return_value={'models': []}):
            result = check_gemini.check_catalog({'GEMINI_API_KEY': 'test', 'STOA_MODEL': 'gemini-4-carbon'})
        self.assertFalse(result['selected_model_listed'])
        self.assertEqual(result['status'], 'ok')

    def test_malformed_response_or_repeated_page_token_is_rejected(self):
        for body in ({'models': 'bad'}, {'models': [1]}, {'models': [], 'nextPageToken': 1},
                     {'models': [], 'nextPageToken': 'same-token'}):
            with self.subTest(body=body), patch.object(check_gemini, 'request_json', return_value=body):
                with self.assertRaises(check_gemini.HealthError):
                    check_gemini.check_catalog({'GEMINI_API_KEY': 'test'})

    def test_cli_export_precedence_and_error_body_are_secret_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            env = Path(directory) / 'gemini.env'
            env.write_text('GEMINI_API_KEY=file-key\nSTOA_MODEL=gemini-4-carbon\n')
            output = io.StringIO()
            with patch.dict(os.environ, {'GEMINI_API_KEY': 'exported-key'}, clear=True), \
                    patch.object(check_gemini, 'request_json', side_effect=check_gemini.HealthError('permission_denied', 403)) as request, \
                    contextlib.redirect_stdout(output):
                code = check_gemini.main(['--env-file', str(env)])
            self.assertEqual(code, 1)
            self.assertEqual(request.call_args.kwargs['headers'], {'x-goog-api-key': 'exported-key'})
            self.assertNotIn('exported-key', output.getvalue())
            self.assertNotIn('file-key', output.getvalue())
            self.assertEqual(json.loads(output.getvalue())['http_status'], 403)


if __name__ == '__main__':
    unittest.main()

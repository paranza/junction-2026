"""Gemini wire format, failure and allowance checks using mocked HTTP only."""
import base64
import json
import os
import unittest
from unittest.mock import patch

import httpx

from server import gemini_provider as gemini, llm


class GeminiProviderTests(unittest.TestCase):
    def test_visual_fallback_policy_is_request_local_and_budgeted(self):
        _,post=self.client()
        with patch.dict(os.environ,{'STOA_GEMINI_MAX_OUTPUT_TOKENS':'24000','STOA_GEMINI_THINKING_LEVEL':'medium'}),llm.usage_scope():
            result=llm._request([{'type':'input_text','text':'Read the source'}],model='gemini-4-argon',max_tokens=65536,
                visual_policy={'image_resolution':'ultra_high','thinking_level':'high','max_output_tokens':65536})
            self.assertEqual(post.call_args.kwargs['json']['generation_config']['max_output_tokens'],65536)
            self.assertEqual(post.call_args.kwargs['json']['generation_config']['thinking_level'],'high')
            self.assertEqual(result['_model'],'gemini-4-argon')
            self.assertEqual(llm.usage_snapshot()['model_calls'],1)
            base=gemini.prepare_request([{'type':'input_text','text':'Next request'}],'source',{},65536,'gemini-4-carbon')
            self.assertEqual(base['generation_config']['max_output_tokens'],24000)
            self.assertEqual(base['generation_config']['thinking_level'],'medium')
            self.assertEqual(os.environ['STOA_GEMINI_MAX_OUTPUT_TOKENS'],'24000')
        self.assertEqual(self.reserve.call_count,1)
    def test_invalid_visual_fallback_policy_reserves_no_attempt(self):
        with self.assertRaises(llm.ModelError):
            llm._request([],model='gemini-4-argon',visual_policy={'max_output_tokens':999999})
        self.reserve.assert_not_called()
    def setUp(self):
        self.patches = [patch.object(llm, 'PROVIDER', 'gemini'),
                        patch.dict(os.environ, {'STOA_GEMINI_IMAGE_RESOLUTION': 'high',
                                                'STOA_GEMINI_THINKING_LEVEL': 'high',
                                                'STOA_GEMMA_THINKING_LEVEL': 'high',
                                                'STOA_GEMINI_TIMEOUT_SECONDS': '240'}),
                        patch.object(llm, 'KEY', 'private-test-key'),
                        patch.object(llm, 'MODEL', 'gemini-4-carbon'),
                        patch.object(llm, 'MAX_CALLS', 50),
                        patch.object(llm.store, 'reserve_model_request', return_value=True),
                        patch.object(llm.store, 'record_event')]
        started = [item.start() for item in self.patches]
        os.environ.pop('STOA_GEMINI_MAX_OUTPUT_TOKENS', None)
        self.reserve, self.event = started[-2:]
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def response(self, result=None, status='completed', usage=True):
        body = {'status': status, 'steps': [
            {'type': 'thought', 'summary': [{'type': 'text', 'text': '{"answer":"not the result"}'}]},
            {'type': 'model_output', 'content': [{'type': 'text', 'text': json.dumps(result or {'answer': '4 doors'})}]}]}
        if usage:
            body['usage'] = {'total_input_tokens': 120, 'total_output_tokens': 20,
                             'total_thought_tokens': 80, 'total_cached_tokens': 30}
        return body

    def client(self, body=None, code=200):
        client_patch = patch.object(gemini.httpx, 'Client')
        factory = client_patch.start()
        self.addCleanup(client_patch.stop)
        post = factory.return_value.__enter__.return_value.post
        post.return_value = httpx.Response(code, json=body if body is not None else self.response())
        return factory, post

    def test_inline_image_schema_and_stateless_current_api(self):
        factory, post = self.client()
        data = base64.b64encode(b'fixture-image').decode()
        content = [{'type': 'input_text', 'text': 'Count visible doors'},
                   {'type': 'input_image', 'image_url': 'data:image/png;base64,' + data, 'detail': 'high'}]
        with llm.usage_scope():
            result = llm._request(content)
            usage = llm.usage_snapshot()
        self.assertEqual(result['answer'], '4 doors')
        self.assertEqual(post.call_args.args, (gemini.ENDPOINT,))
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs['headers'], {'x-goog-api-key': 'private-test-key', 'Api-Revision': '2026-05-20'})
        payload = kwargs['json']
        self.assertEqual(payload['input'][1], {'type': 'image', 'mime_type': 'image/png', 'data': data,
                                             'resolution': 'high'})
        self.assertEqual(payload['system_instruction'], llm.SYSTEM)
        self.assertEqual(payload['response_format'], {'type': 'text', 'mime_type': 'application/json', 'schema': llm.SCHEMA})
        self.assertFalse(payload['store'])
        self.assertEqual(payload['generation_config']['thinking_level'], 'high')
        self.assertEqual(payload['generation_config']['max_output_tokens'], 10000)
        self.assertFalse(factory.call_args.kwargs['follow_redirects'])
        self.reserve.assert_called_once_with(50, {'provider': 'gemini', 'model': 'gemini-4-carbon', 'images': 1})
        self.assertEqual(usage['model_calls'], 1)
        self.assertEqual(usage['input_tokens'], 120)
        self.assertEqual(usage['output_tokens'], 100)  # Includes billed thought tokens.
        self.assertEqual(usage['cached_input_tokens'], 30)
        self.assertNotIn('private-test-key', str(self.event.call_args))

    def test_translation_uses_same_provider_and_custom_schema(self):
        _, post = self.client(self.response({'question': 'How many doors in room "A.03"?'}))
        self.assertEqual(llm.translate_question('Quante porte nella stanza "A.03"?'), 'How many doors in room "A.03"?')
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['response_format']['schema']['required'], ['question'])
        self.assertEqual(payload['generation_config']['max_output_tokens'], 700)
        self.assertEqual(payload['generation_config']['thinking_level'], 'low')
        self.reserve.assert_called_once()

    def test_missing_selected_key_and_unknown_provider_do_not_reserve(self):
        _, post = self.client()
        with patch.object(llm, 'KEY', ''):
            self.assertFalse(llm.model_available())
            with self.assertRaisesRegex(llm.ModelError, 'GEMINI_API_KEY'):
                llm._request([])
        with patch.object(llm, 'PROVIDER', 'invalid'):
            self.assertFalse(llm.model_available())
            with self.assertRaisesRegex(llm.ModelError, 'STOA_PROVIDER'):
                llm._request([])
        self.reserve.assert_not_called()
        post.assert_not_called()

    def test_allowance_denied_makes_no_network_request(self):
        _, post = self.client()
        self.reserve.return_value = False
        with self.assertRaisesRegex(llm.ModelError, 'allowance'):
            llm._request([{'type': 'input_text', 'text': 'Doors?'}])
        self.reserve.assert_called_once()
        post.assert_not_called()

    def test_failed_http_attempt_is_counted_once_and_error_is_sanitized(self):
        for code in (400, 401, 403, 404, 429, 503):
            with self.subTest(code=code):
                _, post = self.client({'error': {'message': 'private-test-key; private floor plan'}}, code)
                self.reserve.reset_mock()
                with llm.usage_scope():
                    with self.assertRaises(llm.ModelError) as error:
                        llm._request([])
                    usage = llm.usage_snapshot()
                self.assertNotIn('private-test-key', str(error.exception))
                self.assertNotIn('private floor plan', str(error.exception))
                self.assertEqual(usage['model_calls'], 1)
                self.assertTrue(usage['usage_incomplete'])
                self.reserve.assert_called_once()
                post.assert_called_once()

    def test_transport_failure_is_sanitized_and_never_retried(self):
        _, post = self.client()
        post.side_effect = httpx.ConnectError('private-test-key')
        with self.assertRaisesRegex(llm.ModelError, 'could not be reached') as error:
            llm._request([])
        self.assertNotIn('private-test-key', str(error.exception))
        post.assert_called_once()
        self.reserve.assert_called_once()

    def test_incomplete_blocked_and_continuation_results_are_rejected_with_usage(self):
        for status in ('incomplete', 'failed', 'requires_continuation', 'in_progress'):
            with self.subTest(status=status):
                self.client(self.response(status=status))
                with llm.usage_scope():
                    with self.assertRaisesRegex(llm.ModelError, 'did not finish'):
                        llm._request([])
                    usage = llm.usage_snapshot()
                self.assertEqual(usage['output_tokens'], 100)
                self.assertNotIn('usage_incomplete', usage)

    def test_malformed_or_empty_completed_output_is_rejected(self):
        for body in ([1], {'status': 'completed', 'steps': []}, self.response(['not', 'an', 'object'])):
            with self.subTest(body=body):
                self.client(body)
                with self.assertRaisesRegex(llm.ModelError, 'unreadable'):
                    llm._request([])

    def test_invalid_json_response_is_rejected(self):
        _, post = self.client()
        post.return_value = httpx.Response(200, text='<html>gateway error</html>')
        with self.assertRaisesRegex(llm.ModelError, 'unreadable'):
            llm._request([])
        self.reserve.assert_called_once()

    def test_remote_image_urls_and_invalid_inline_data_do_not_consume_allowance(self):
        _, post = self.client()
        for image in ('https://example.com/drawing.png', 'data:image/png;base64,!', 'data:image/png;base64,a'):
            with self.subTest(image=image), self.assertRaises(llm.ModelError):
                llm._request([{'type': 'input_image', 'image_url': image}])
        self.reserve.assert_not_called()
        post.assert_not_called()

    def test_unknown_token_usage_does_not_appear_free(self):
        self.client(self.response(usage=False))
        with llm.usage_scope(), patch.dict('os.environ', {'STOA_INPUT_USD_PER_MILLION': '1', 'STOA_OUTPUT_USD_PER_MILLION': '2'}):
            llm._request([])
            usage = llm.usage_snapshot()
        self.assertTrue(usage['usage_incomplete'])
        self.assertIsNone(usage['cost_estimate_usd'])

    def test_cached_tokens_cannot_exceed_total_and_malformed_counts_remain_unknown(self):
        for malformed in ({'total_cached_tokens': 121}, {'total_thought_tokens': -1}, {'total_output_tokens': '20'}):
            body = self.response()
            body['usage'].update(malformed)
            self.assertIsNone(gemini.normalize_response(body)['usage'])

    def test_provider_signature_separates_provider_model_and_revision_without_keys(self):
        signature = llm.provider_signature()
        self.assertIn('gemini:gemini-4-carbon:', signature)
        self.assertIn(gemini.API_REVISION, signature)
        self.assertNotIn(llm.KEY, signature)
        with patch.object(llm, 'PROVIDER', 'openai'):
            self.assertNotEqual(signature, llm.provider_signature())
        with patch.object(llm, 'MODEL', 'gemini-4-argon'):
            self.assertNotEqual(signature, llm.provider_signature())

    def test_image_resolution_defaults_to_ultra_high_and_is_sent_on_every_image(self):
        data = base64.b64encode(b'fixture-image').decode()
        content = [{'type': 'input_text', 'text': 'Count doors'},
                   {'type': 'input_image', 'image_url': 'data:image/png;base64,' + data},
                   {'type': 'input_image', 'image_url': 'data:image/jpeg;base64,' + data}]
        with patch.dict(os.environ, {}, clear=True):
            payload = gemini.prepare_request(content, llm.SYSTEM, llm.SCHEMA, 10000, llm.MODEL)
            self.assertEqual(gemini.image_resolution(), 'ultra_high')
            self.assertIn('image_resolution=ultra_high', llm.provider_signature())
        self.assertEqual([part['resolution'] for part in payload['input'] if part['type'] == 'image'], ['ultra_high', 'ultra_high'])
        self.assertNotIn('resolution', payload['input'][0])

    def test_each_supported_image_resolution_changes_wire_payload_and_cache_signature(self):
        data = base64.b64encode(b'fixture-image').decode()
        signatures = set()
        for resolution in ('low', 'medium', 'high', 'ultra_high'):
            with self.subTest(resolution=resolution), patch.dict(os.environ, {'STOA_GEMINI_IMAGE_RESOLUTION': resolution}):
                _, post = self.client()
                llm._request([{'type': 'input_image', 'image_url': 'data:image/png;base64,' + data}])
                image = post.call_args.kwargs['json']['input'][0]
                self.assertEqual(image['resolution'], resolution)
                signature = llm.provider_signature()
                self.assertIn('image_resolution=' + resolution, signature)
                signatures.add(signature)
        self.assertEqual(len(signatures), 4)

    def test_invalid_image_resolution_is_sanitized_before_allowance_or_network(self):
        _, post = self.client()
        for value in ('', 'automatic', 'private-test-key\ninjected=1'):
            with self.subTest(value=value), patch.dict(os.environ, {'STOA_GEMINI_IMAGE_RESOLUTION': value}):
                # Cache-key generation must remain safe for native questions.
                self.assertIn('image_resolution=invalid', llm.provider_signature())
                self.assertNotIn('private-test-key', llm.provider_signature())
                with self.assertRaisesRegex(llm.ModelError, 'STOA_GEMINI_IMAGE_RESOLUTION') as error:
                    llm._request([{'type': 'input_text', 'text': 'Doors?'}])
                self.assertNotIn('private-test-key', str(error.exception))
        self.reserve.assert_not_called()
        post.assert_not_called()

    def test_openai_signature_is_unaffected_by_gemini_image_resolution(self):
        with patch.object(llm, 'PROVIDER', 'openai'):
            original = llm.provider_signature()
            with patch.dict(os.environ, {'STOA_GEMINI_IMAGE_RESOLUTION': 'ultra_high'}):
                self.assertEqual(llm.provider_signature(), original)

    def test_visual_thinking_policy_changes_wire_and_cache_but_bounded_text_stays_low(self):
        signatures = set()
        for level in ('low', 'medium', 'high'):
            with self.subTest(level=level), patch.dict(os.environ, {'STOA_GEMINI_THINKING_LEVEL': level}):
                _, post = self.client()
                llm._request([], max_tokens=14000)
                self.assertEqual(post.call_args.kwargs['json']['generation_config']['thinking_level'], level)
                self.assertIn('thinking_level=' + level, llm.provider_signature())
                signatures.add(llm.provider_signature())
                bounded = gemini.prepare_request([], llm.SYSTEM, llm.SCHEMA, 700, llm.MODEL)
                self.assertEqual(bounded['generation_config']['thinking_level'], 'low')
        self.assertEqual(len(signatures), 3)

    def test_visual_output_override_is_explicit_bounded_and_does_not_expand_translation(self):
        default = llm.provider_signature()
        self.assertIn('max_output_tokens=caller', default)
        for cap in (1000, 24000, 32768):
            with self.subTest(cap=cap), patch.dict(os.environ, {'STOA_GEMINI_MAX_OUTPUT_TOKENS': str(cap)}):
                _, post = self.client()
                llm._request([], max_tokens=14000)
                self.assertEqual(post.call_args.kwargs['json']['generation_config']['max_output_tokens'], cap)
                self.assertIn('max_output_tokens=' + str(cap), llm.provider_signature())
                self.assertNotEqual(default, llm.provider_signature())
                bounded = gemini.prepare_request([], llm.SYSTEM, llm.SCHEMA, 700, llm.MODEL)
                self.assertEqual(bounded['generation_config']['max_output_tokens'], 700)

    def test_transport_timeout_defaults_to_600_seconds(self):
        with patch.dict(os.environ):
            os.environ.pop('STOA_GEMINI_TIMEOUT_SECONDS', None)
            self.assertEqual(gemini.timeout_seconds(), 600)
            self.assertIn('timeout_seconds=600', llm.provider_signature())

    def test_transport_timeout_is_configurable_and_part_of_cache_policy(self):
        baseline = llm.provider_signature()
        self.assertIn('timeout_seconds=240', baseline)
        with patch.dict(os.environ, {'STOA_GEMINI_TIMEOUT_SECONDS': '600'}):
            factory, _ = self.client()
            llm._request([])
            timeout = factory.call_args.kwargs['timeout']
            self.assertEqual(timeout.read, 600)
            self.assertEqual(timeout.connect, 15)
            self.assertIn('timeout_seconds=600', llm.provider_signature())
            self.assertNotEqual(baseline, llm.provider_signature())

    def test_invalid_generation_policy_is_sanitized_before_budget_or_network(self):
        _, post = self.client()
        invalid = {'STOA_GEMINI_THINKING_LEVEL': ('', 'minimal', 'xhigh', 'secret\ninjected=1'),
                   'STOA_GEMINI_MAX_OUTPUT_TOKENS': ('', '999', '32769', '24000.5', 'secret\ninjected=1'),
                   'STOA_GEMINI_TIMEOUT_SECONDS': ('', '59', '601', 'nan', 'secret\ninjected=1')}
        for name, values in invalid.items():
            for value in values:
                with self.subTest(setting=name, value=value), patch.dict(os.environ, {name: value}):
                    signature = llm.provider_signature()
                    self.assertIn('invalid', signature)
                    self.assertNotIn('secret', signature)
                    with self.assertRaisesRegex(llm.ModelError, name) as error:
                        llm._request([], max_tokens=14000)
                    self.assertNotIn('secret', str(error.exception))
        self.reserve.assert_not_called()
        post.assert_not_called()

    def test_gemma_has_separate_supported_thinking_policy_and_shares_explicit_output_timeout(self):
        model = 'gemma-4-31b-it'
        baseline = gemini.config_signature(model)
        with patch.dict(os.environ, {'STOA_GEMINI_THINKING_LEVEL': 'medium'}):
            self.assertEqual(baseline, gemini.config_signature(model))
            visual = gemini.prepare_request([], llm.SYSTEM, llm.SCHEMA, 12000, model)
            self.assertEqual(visual['generation_config']['thinking_level'], 'high')
        with patch.dict(os.environ, {'STOA_GEMMA_THINKING_LEVEL': 'minimal',
                                    'STOA_GEMINI_MAX_OUTPUT_TOKENS': '24000',
                                    'STOA_GEMINI_TIMEOUT_SECONDS': '600'}):
            visual = gemini.prepare_request([], llm.SYSTEM, llm.SCHEMA, 12000, model)
            self.assertEqual(visual['generation_config']['thinking_level'], 'minimal')
            self.assertEqual(visual['generation_config']['max_output_tokens'], 24000)
            bounded = gemini.prepare_request([], llm.SYSTEM, llm.SCHEMA, 700, model)
            self.assertEqual(bounded['generation_config']['thinking_level'], 'minimal')
            self.assertEqual(bounded['generation_config']['max_output_tokens'], 700)
            signature = gemini.config_signature(model)
            self.assertIn('thinking_level=minimal', signature)
            self.assertIn('max_output_tokens=24000', signature)
            self.assertIn('timeout_seconds=600', signature)
        with patch.dict(os.environ, {'STOA_GEMMA_THINKING_LEVEL': 'low'}):
            self.assertIn('thinking_level=invalid', gemini.config_signature(model))
            with self.assertRaisesRegex(gemini.ProviderError, 'STOA_GEMMA_THINKING_LEVEL'):
                gemini.prepare_request([], llm.SYSTEM, llm.SCHEMA, 12000, model)

    def test_openai_transport_remains_available_without_gemini_calls(self):
        _, post = self.client({'status': 'completed', 'usage': {'input_tokens': 10, 'output_tokens': 5},
                               'output': [{'content': [{'type': 'output_text', 'text': '{"answer":"native context"}'}]}]})
        with patch.object(llm, 'PROVIDER', 'openai'), patch.object(gemini, 'request') as gemini_request:
            result = llm._request([])
        self.assertEqual(result['answer'], 'native context')
        self.assertEqual(post.call_args.args[0], 'https://api.openai.com/v1/responses')
        self.assertEqual(post.call_args.kwargs['headers'], {'Authorization': 'Bearer private-test-key'})
        gemini_request.assert_not_called()
        self.reserve.assert_called_once()


if __name__ == '__main__':
    unittest.main()

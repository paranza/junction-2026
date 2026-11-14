"""Optional Gemma review: mocked provider only, no keys or source references."""
import concurrent.futures
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from PIL import Image

from server import gemini_provider, inventory, llm, visual_audit


def completed(payload, key):
    return {'status': 'completed',
            'usage': {'input_tokens': 100, 'output_tokens': 20,
                      'input_tokens_details': {'cached_tokens': 0}},
            'output': [{'content': [{'type': 'output_text',
                                    'text': json.dumps({'model_seen': payload['model']})}]}]}


class GemmaRequestRouting(unittest.TestCase):
    def setUp(self):
        patches = [patch.object(llm, 'PROVIDER', 'gemini'),
                   patch.object(llm, 'MODEL', 'gemini-4-carbon'),
                   patch.object(llm, 'KEY', 'mock-google-credential'),
                   patch.object(llm, 'MAX_CALLS', 50),
                   patch.dict(os.environ, {'STOA_GEMINI_IMAGE_RESOLUTION': 'high',
                                           'STOA_GEMMA_THINKING_LEVEL': 'high'}),
                   patch.object(llm.store, 'reserve_model_request', return_value=True),
                   patch.object(llm.store, 'record_event'),
                   patch.object(gemini_provider, 'request', side_effect=completed)]
        values = [item.start() for item in patches]
        self.reserve, self.event, self.request = values[-3:]
        self.addCleanup(lambda: [item.stop() for item in reversed(patches)])

    def test_override_uses_actual_model_in_wire_budget_events_and_usage(self):
        with llm.usage_scope():
            result = llm._request([], model='gemma-4-31b-it')
            usage = llm.usage_snapshot()
        self.assertEqual(result['model_seen'], 'gemma-4-31b-it')
        self.assertEqual(result['_model'], 'gemma-4-31b-it')
        self.assertEqual(result['_provider'], 'gemini')
        self.assertEqual(llm.MODEL, 'gemini-4-carbon')
        self.reserve.assert_called_once_with(50, {'provider': 'gemini', 'model': 'gemma-4-31b-it', 'images': 0})
        self.assertEqual(self.event.call_args.args[1]['model'], 'gemma-4-31b-it')
        self.assertEqual(usage['models'], ['gemini/gemma-4-31b-it'])
        self.assertEqual(usage['model_calls'], 1)
        self.assertEqual(self.request.call_args.args[1], 'mock-google-credential')
        self.assertNotIn('mock-google-credential', str(self.event.call_args))

    def test_invalid_or_cross_provider_override_never_reserves_or_sends_a_key(self):
        for model in ('gpt-6-astra', 'gemma-invalid', 'credential\ninjected=value', ''):
            with self.subTest(model=model), self.assertRaises(llm.ModelError) as error:
                llm._request([], model=model)
            self.assertNotIn('credential', str(error.exception))
        with patch.object(llm, 'PROVIDER', 'openai'), patch.object(llm, 'MODEL', 'gpt-6-astra'):
            with self.assertRaises(llm.ModelError):
                llm._request([], model='gemma-4-31b-it')
        self.reserve.assert_not_called()
        self.request.assert_not_called()

    def test_mixed_model_usage_does_not_apply_the_base_models_prices(self):
        with llm.usage_scope(), patch.dict(os.environ, {
            'STOA_PRICE_MODEL': 'gemini/gemini-4-carbon',
            'STOA_INPUT_USD_PER_MILLION': '1', 'STOA_OUTPUT_USD_PER_MILLION': '2',
        }):
            llm._request([])
            llm._request([], model='gemma-4-31b-it')
            usage = llm.usage_snapshot()
        self.assertEqual(usage['model_calls'], 2)
        self.assertEqual(usage['input_tokens'], 200)
        self.assertEqual(usage['output_tokens'], 40)
        self.assertEqual(usage['models'], ['gemini/gemini-4-carbon', 'gemini/gemma-4-31b-it'])
        self.assertEqual(usage['cost_estimate_usd'], .00014)
        self.assertEqual(usage['cost_basis'], 'model_rates')
        self.assertEqual(self.reserve.call_count, 2)

    def test_parallel_model_selection_is_local_and_usage_scopes_do_not_mix(self):
        barrier = threading.Barrier(2)

        def respond(payload, key):
            barrier.wait(timeout=3)
            self.assertEqual(llm.MODEL, 'gemini-4-carbon')
            return completed(payload, key)

        def run(model):
            with llm.usage_scope():
                answer = llm._request([], model=model)
                return answer['model_seen'], llm.usage_snapshot()['models']

        self.request.side_effect = respond
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, ('gemini-4-carbon', 'gemma-4-31b-it')))
        self.assertEqual(results, [('gemini-4-carbon', ['gemini/gemini-4-carbon']),
                                   ('gemma-4-31b-it', ['gemini/gemma-4-31b-it'])])
        self.assertEqual(self.reserve.call_count, 2)

    def test_gemma_uses_supported_thinking_and_the_same_strict_schema(self):
        for model in sorted(gemini_provider.GEMMA_MODELS):
            for tokens, thinking in ((700, 'minimal'), (12000, 'high')):
                payload = gemini_provider.prepare_request([], llm.SYSTEM, visual_audit.SCHEMA, tokens, model)
                self.assertEqual(payload['generation_config']['thinking_level'], thinking)
                self.assertEqual(payload['response_format']['schema'], visual_audit.SCHEMA)
                self.assertFalse(payload['response_format']['schema']['additionalProperties'])
                self.assertFalse(payload['store'])
        with self.assertRaises(gemini_provider.ProviderError):
            gemini_provider.prepare_request([], llm.SYSTEM, llm.SCHEMA, 12000, 'gemma-unsupported')


class GemmaVisualReview(unittest.TestCase):
    def setUp(self):
        self.initial = {'operation': 'count', 'value': 5, 'unit': 'count', 'category': 'door',
                        'method': 'visual_inventory', 'model': 'gemini-4-carbon', 'evidence': [],
                        'warnings': [], 'coverage': {'inspected_pages': [1]}}
        self.document = {'page_count': 1, 'document_id': 'test-drawing', 'source_sha256': 'fixture-hash'}
        self.images = [{'page': 1, 'region': [0, 0, 1, 1], 'kind': 'overview',
                        'image': Image.new('RGB', (100, 100), 'white')}]
        self.response = {'usable_plan': True, 'complete_scope': True, 'warnings': [],
                         'objects': [{'image_index': 0, 'bbox': [.1, .1, .2, .2],
                                      'label': 'Door', 'category': 'door', 'ambiguous': False}]}
        patches = [patch.object(llm, 'PROVIDER', 'gemini'), patch.object(llm, 'MODEL', 'gemini-4-carbon'),
                   patch.dict(os.environ, {'STOA_VISUAL_AUDIT_MODEL': 'gemma-4-31b-it'})]
        for item in patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(patches)])

    def audit(self, response=None, error=None):
        with patch.object(visual_audit.rendering, 'image_inputs', return_value=self.images) as render, \
             patch.object(llm, '_request', return_value=response or self.response, side_effect=error) as request:
            result = visual_audit.audit_visual_count('How many doors?', self.initial, self.document, Path('fixture.png'))
        return result, request, render

    def test_different_model_review_keeps_source_checks_and_records_its_role(self):
        result, request, _ = self.audit()
        self.assertEqual(result['value'], 1)
        self.assertEqual(result['original_detection']['value'], 5)
        self.assertEqual(request.call_args.kwargs['model'], 'gemma-4-31b-it')
        audit = result['count_audit']
        self.assertEqual(audit['auditor_model'], 'gemma-4-31b-it')
        self.assertEqual(audit['auditor_provider'], 'gemini')
        self.assertEqual(audit['initial_model'], 'gemini-4-carbon')
        self.assertEqual(audit['method'], 'different_model_second_pass')
        self.assertFalse(audit['same_model'])
        self.assertFalse(audit['independent_verification'])
        self.assertEqual(result['status'], 'needs_review')
        self.assertFalse(result['evidence'][0]['source_verified'])
        self.assertIn(visual_audit.CROSS_MODEL_WARNING, result['warnings'])

    def test_gemma_ambiguity_still_withholds_numeric_count(self):
        response = {**self.response, 'objects': [{**self.response['objects'][0], 'category': 'unknown'}]}
        result, _, _ = self.audit(response)
        self.assertIsNone(result['value'])
        self.assertEqual(result['count_audit']['status'], 'incomplete')
        self.assertEqual(result['count_audit']['ambiguous_objects'], 1)

    def test_unavailable_gemma_preserves_provisional_original(self):
        result, _, _ = self.audit(error=llm.ModelError('Model service unavailable.'))
        self.assertEqual(result['value'], 5)
        self.assertEqual(result['evidence'], self.initial['evidence'])
        self.assertEqual(result['count_audit']['auditor_model'], 'gemma-4-31b-it')
        self.assertEqual(result['count_audit']['status'], 'unavailable')
        self.assertFalse(result['count_audit']['independent_verification'])

    def test_invalid_policy_never_renders_or_calls_the_model_and_is_sanitized(self):
        with patch.dict(os.environ, {'STOA_VISUAL_AUDIT_MODEL': 'private-credential\ninjected=1'}):
            result, request, render = self.audit()
            signature = visual_audit.config_signature()
        self.assertEqual(result['value'], 5)
        self.assertEqual(result['count_audit']['status'], 'unavailable')
        self.assertEqual(signature['model'], 'invalid')
        self.assertNotIn('private-credential', json.dumps(result))
        request.assert_not_called()
        render.assert_not_called()

    def test_auditor_changes_answer_policy_but_preserves_base_inventory_key(self):
        first = visual_audit.config_signature()
        inventory_key = inventory._key(self.document, 1)
        base_signature = llm.provider_signature()
        with patch.dict(os.environ, {'STOA_VISUAL_AUDIT_MODEL': 'gemma-4-26b-a4b-it'}):
            self.assertNotEqual(first, visual_audit.config_signature())
            self.assertEqual(inventory_key, inventory._key(self.document, 1))
            self.assertEqual(base_signature, llm.provider_signature())
        with patch.dict(os.environ, {'STOA_VISUAL_AUDIT_MODEL': ''}):
            self.assertEqual(visual_audit.audit_model(), llm.MODEL)
            result, request, _ = self.audit()
            self.assertNotIn('model', request.call_args.kwargs)
            self.assertTrue(result['count_audit']['same_model'])
            self.assertIn(visual_audit.REVIEW_WARNING, result['warnings'])


class GroundingSchema(unittest.TestCase):
    def test_gemma_coordinates_and_image_references_are_bounded_without_global_mutation(self):
        schema = visual_audit._response_schema([{'page': 1}], 'gemma-4-31b-it')
        fields = schema['properties']['objects']['items']['properties']
        self.assertEqual(fields['image_index']['enum'], [0])
        self.assertEqual(fields['bbox']['items']['minimum'], 0)
        self.assertEqual(fields['bbox']['items']['maximum'], 1)
        other = visual_audit._response_schema([{'page': 1}, {'page': 2}], 'gemma-4-31b-it')
        self.assertEqual(other['properties']['objects']['items']['properties']['image_index']['enum'], [0, 1])
        self.assertNotIn('enum', visual_audit.SCHEMA['properties']['objects']['items']['properties']['image_index'])
        self.assertIs(visual_audit._response_schema([{'page': 1}], 'gemini-4-carbon'), visual_audit.SCHEMA)


if __name__ == '__main__':
    unittest.main()

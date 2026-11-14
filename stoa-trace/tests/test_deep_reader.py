"""Safety and scope of the complex-sheet agent, without paid requests."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image
from server import deep_reader, llm


class DimensionalProgram(unittest.TestCase):
    def test_recomputes_mixed_units_and_min_max(self):
        operands = {'e0': {'value': 6, 'unit': 'm'}, 'e1': {'value': 10, 'unit': 'ft'}}
        value, used = deep_reader.calculate('e0 * e1', operands, 'm²')
        self.assertAlmostEqual(value, 18.288)
        self.assertEqual(used, {'e0', 'e1'})
        value, _ = deep_reader.calculate('max(e0, e1)', operands, 'mm')
        self.assertAlmostEqual(value, 6000)

    def test_rejects_code_constants_wrong_dimensions_and_missing_operands(self):
        operands = {'e0': {'value': 5, 'unit': 'm'}, 'e1': {'value': 0, 'unit': 'ft'}}
        for expression, unit in [('e0+e1', 'm²'), ('e0/e1', 'm'), ('e0+999', 'm'),
                                  ('__import__("os").system("echo unsafe")', 'm'),
                                  ('e9', 'm'), ('e0**1000000', 'm')]:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                deep_reader.calculate(expression, operands, unit)


class SourceInspection(unittest.TestCase):
    def setUp(self):
        self.document = {'page_count': 1, 'pages': [{'page': 1, 'width': 6000, 'height': 4000, 'words': []}], 'objects': []}
        self.inputs = [{'page': 1, 'region': [0, 0, 1, 1], 'image': Image.new('RGB', (32, 32)), 'kind': 'overview'}]

    def evidence(self, quote, value, unit, box=None, **kwargs):
        return {'image_index': 0, 'object_id': None, 'label': 'Source annotation',
                'quoted_text': quote, 'value': value, 'unit': unit, 'bbox': box or [.1, .1, .2, .2],
                'unit_basis_index': None, **kwargs}

    def raw(self, evidence, **kwargs):
        return {'operation': 'area', 'unit': 'm²', 'value': 99999, 'expression': 'e0',
                'complete': True, 'answer': '99999 is a model assertion', 'scope': 'page', 'warnings': [],
                'evidence': evidence, **kwargs}

    def finish(self, raw, question='What is the area?', **kwargs):
        return deep_reader.finalize(raw, self.inputs, self.document, question, [0, 0, 1, 1], [], **kwargs)

    def test_ignores_model_math_and_preserves_visual_review(self):
        raw = self.raw([self.evidence('Area 85 SF', 85, 'SF')])
        result = self.finish(raw)
        self.assertAlmostEqual(result['value'], 7.8967584)
        self.assertNotIn('99999', result['answer'])
        self.assertFalse(result['evidence'][0]['source_verified'])
        self.assertEqual(result['status'], 'needs_review')

    def test_composite_area_from_typed_dimensions(self):
        raw = self.raw([self.evidence('Width 6 m', 6, 'm'),
                        self.evidence('Depth 10 ft', 10, 'ft', [.3, .1, .4, .2])], expression='e0 * e1')
        self.assertAlmostEqual(self.finish(raw)['value'], 18.288)

    def test_max_identifies_the_winning_annotation(self):
        raw = self.raw([self.evidence('22 m²', 22, 'm²', label='Office'),
                        self.evidence('400 SF', 400, 'SF', [.3, .1, .4, .2], label='Gallery')], expression='max(e0,e1)')
        result = self.finish(raw, 'Which room has the largest area?')
        self.assertAlmostEqual(result['value'], 37.161216)
        self.assertIn('Gallery', result['answer'])

    def test_explicit_unit_note_can_follow_the_bare_dimension(self):
        raw = self.raw([self.evidence('225 SLAB', 225, 'mm', unit_basis_index=1),
                        self.evidence('ALL DIMENSIONS IN MM', None, None, [.4, .4, .5, .5])], operation='length', unit='mm')
        result = self.finish(raw, 'What is the slab thickness?')
        self.assertEqual(result['value'], 225)
        self.assertFalse(result['evidence'][0]['source_verified'])

    def test_located_table_header_can_qualify_a_bare_numeric_cell(self):
        raw=self.raw([self.evidence('140',140,'ft',[.4,.5,.45,.53],unit_basis_index=1),
                      self.evidence('HEAD (FT.)',None,None,[.4,.42,.45,.46])],operation='length',unit='m')
        result=self.finish(raw,'What is the specified head?')
        self.assertAlmostEqual(result['value'],42.672)
        self.assertFalse(result['evidence'][0]['source_verified'])
        raw['evidence'][1]['bbox']=[.7,.42,.75,.46]
        self.assertIsNone(self.finish(raw,'What is the specified head?')['value'])

    def test_named_area_scope_does_not_change_a_diameter_to_square_units(self):
        self.assertEqual(llm.requested_quantity('What is the pipe diameter in Area A?'),'length')
        self.assertEqual(llm.requested_quantity('What is the area of room A?'),'area')
        self.assertEqual(llm.requested_quantity('How many doors in Area B?'),'count')

    def test_feet_only_scale_marks_are_typed_without_truncating_combined_dimensions(self):
        from server.verification import _text_candidates,convert_quantity
        self.assertEqual([r['value'] for r in _text_candidates("0' 4' 8'",'length')],[0,4,8])
        values=[convert_quantity(r['value'],r['unit'],'ft') for r in _text_candidates("12' - 1 1/2\"",'length')]
        self.assertIn(12.125,values)
        self.assertNotIn(12,values)

    def test_missing_or_wrong_quotes_and_units_do_not_supply_operands(self):
        for item in [self.evidence('85 SF', 900, 'SF'), self.evidence('SLAB', 225, 'mm'),
                     self.evidence('225 mm', 225, 'mm')]:
            result = self.finish(self.raw([item]))
            self.assertIsNone(result['value'])
            self.assertNotIn('99999', result['answer'])

    def test_duplicate_source_observation_cannot_double_an_area(self):
        item = self.evidence('Area 22 m²', 22, 'm²')
        result = self.finish(self.raw([item, item], expression='e0+e1'))
        self.assertIsNone(result['value'])
        self.assertEqual(len(result['evidence']), 1)

    def test_detail_boxes_map_back_and_respect_selected_scope(self):
        self.inputs[0]['region'] = [.5, .5, 1, 1]
        item = self.evidence('22 m²', 22, 'm²', [.2, .2, .4, .4])
        result = self.finish(self.raw([item]))
        self.assertEqual(result['evidence'][0]['bbox'], [.6, .6, .7, .7])
        outside = deep_reader.finalize(self.raw([item]), self.inputs, self.document, 'What is the area?', [0, 0, .4, .4], [])
        self.assertIsNone(outside['value'])

    def test_unknown_answer_type_cannot_smuggle_a_numeric_result(self):
        result = self.finish(self.raw([], operation='text'))
        self.assertIsNone(result['value'])
        self.assertNotIn('99999', result['answer'])

    def test_actual_abstention_keeps_its_missing_source_explanation(self):
        raw = self.raw([], operation='unknown', value=None, complete=False,
                       answer='Vertical pipe runs and the referenced continuation sheets are missing.')
        result = self.finish(raw, 'What is the total pipe length?')
        self.assertIsNone(result['value'])
        self.assertIn('continuation sheets', result['answer'])

    def test_invalid_count_citations_cannot_turn_into_an_exact_zero(self):
        raw = self.raw([self.evidence('', None, None, image_index=99)], operation='count', unit='count')
        result = self.finish(raw, 'How many doors?')
        self.assertIsNone(result['value'])

    def test_agent_inspects_original_regions_before_answering(self):
        item = self.evidence('Area 22 m²', 22, 'm²', image_index=1)
        decisions = [{'action': 'inspect', 'regions': [[.1, .1, .5, .5]], 'reason': 'Read the labels', 'result': None},
                     {'action': 'answer', 'regions': [], 'reason': 'Read source', 'result': self.raw([item])}]
        with patch.dict(os.environ, {'STOA_COMPLEX_READER': 'auto'}), patch.object(llm, 'PROVIDER', 'gemini'), \
             patch.object(llm, '_request', side_effect=decisions) as request, \
             patch('server.rendering.render_region', return_value=Image.new('RGB', (32, 32))) as render:
            result = deep_reader.answer('What is the printed area?', self.document, Path('unknown.png'))
        self.assertEqual(result['value'], 22)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(render.call_args_list[1].args, (Path('unknown.png'), 1, [.1, .1, .5, .5], 3200))

    def test_round_budget_never_creates_a_partial_numeric_answer(self):
        decisions = [{'action': 'inspect', 'regions': [[.1*i, .1, .1*i+.1, .2]], 'reason': 'Need detail', 'result': None} for i in range(1, 4)]
        with patch.dict(os.environ, {'STOA_COMPLEX_READER': 'auto'}), patch.object(llm, 'PROVIDER', 'gemini'), \
             patch.object(llm, '_request', side_effect=decisions) as request, \
             patch('server.rendering.render_region', return_value=Image.new('RGB', (32, 32))):
            result = deep_reader.answer('What is the area?', self.document, Path('unknown.png'))
        self.assertEqual(request.call_count, 3)
        self.assertIsNone(result['value'])

    def test_exhausted_crop_budget_requests_an_answer_from_existing_views(self):
        item=self.evidence('',None,None,label='Door',image_index=1)
        decisions=[{'action':'inspect','regions':[[.01,.01,.08,.08],[.12,.12,.18,.18],[.2,.2,.28,.28]],'reason':'Inspect details'},
                   {'action':'answer','result':self.raw([item],operation='count',unit='count',expression=None)}]
        with patch.dict(os.environ,{'STOA_COMPLEX_READER':'auto'}),patch.object(llm,'PROVIDER','gemini'),\
             patch.object(llm,'_request',side_effect=decisions) as request,\
             patch('server.rendering.render_region',return_value=Image.new('RGB',(32,32))):
            result=deep_reader.answer('How many doors?',self.document,Path('unknown.png'))
        self.assertEqual(result['value'],1)
        self.assertNotIn('inspect',request.call_args.kwargs['schema']['properties']['action']['enum'])

    def test_global_counts_start_with_complete_source_tiles(self):
        item = self.evidence('', None, None, label='Door', image_index=1)
        final = {'action': 'answer', 'regions': [], 'reason': 'Counted across the sheet',
                 'result': self.raw([item, item], operation='count', unit='count', expression=None)}
        with patch.dict(os.environ, {'STOA_COMPLEX_READER': 'auto'}), patch.object(llm, 'PROVIDER', 'gemini'), \
             patch.object(llm, '_request', return_value=final), \
             patch('server.rendering.render_region', return_value=Image.new('RGB', (32, 32))) as render:
            result = deep_reader.answer('How many doors?', self.document, Path('unknown.png'))
        self.assertEqual(render.call_count, 7)
        self.assertEqual(result['value'], 1)

    def test_followup_uses_locators_without_trusting_previous_quantities(self):
        item = self.evidence('', None, None, label='Door', image_index=1)
        final = {'action': 'answer', 'regions': [], 'reason': 'Inspected the referenced source',
                 'result': self.raw([item], operation='count', unit='count', expression=None)}
        previous = {'question': 'Locate the tagged equipment', 'value': 99999,
                    'evidence': [{'label': 'Equipment A', 'page': 1, 'bbox': [.1, .1, .2, .2], 'value': 99999}]}
        with patch.dict(os.environ, {'STOA_COMPLEX_READER': 'auto'}), patch.object(llm, 'PROVIDER', 'gemini'), \
             patch.object(llm, '_request', return_value=final) as request, \
             patch('server.rendering.render_region', return_value=Image.new('RGB', (32, 32))):
            result = deep_reader.answer('How many of those?', self.document, Path('unknown.png'), previous=previous)
        text = '\n'.join(part.get('text', '') for part in request.call_args.args[0])
        self.assertIn('Equipment A', text)
        self.assertNotIn('99999', text)
        self.assertEqual(result['value'], 1)


if __name__ == '__main__':
    unittest.main()

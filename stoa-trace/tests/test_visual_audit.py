"""Second-pass count contracts with novel images and mocked model responses."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image

from server import llm, visual_audit


def image(page=1, region=None):
    return {'page': page, 'region': region or [0, 0, 1, 1], 'kind': 'original',
            'image': Image.new('RGB', (80, 60), 'white')}


def obj(box=None, index=0, label='Door', ambiguous=False):
    return {'image_index': index, 'bbox': box or [.1, .1, .2, .2], 'label': label, 'ambiguous': ambiguous}


class VisualCountAudit(unittest.TestCase):
    def setUp(self):
        self.document = {'page_count': 1, 'document_id': 'new-upload', 'source_sha256': 'a-new-source-hash'}
        self.initial = {'operation': 'count', 'value': 99, 'unit': 'count', 'method': 'vision', 'status': 'visual',
                        'evidence': [{'id': 'initial-1', 'page': 1, 'bbox': [.1, .1, .2, .2], 'label': 'Door'}],
                        'warnings': [], 'coverage': {'inspected_pages': [1]}}

    def audit(self, objects=None, images=None, **kwargs):
        response = {'usable_plan': True, 'complete_scope': True, 'objects': objects or [], 'warnings': []}
        response.update(kwargs.pop('response', {}))
        document = kwargs.pop('document', self.document)
        result = kwargs.pop('result', self.initial)
        with patch.object(visual_audit.rendering, 'image_inputs', return_value=images or [image()]) as render, \
             patch.object(llm, '_request', return_value=response) as request:
            answer = visual_audit.audit_visual_count('How many doors are shown?', result, document, Path('new-upload.png'), **kwargs)
        return answer, request, render

    def test_native_and_non_count_paths_do_not_request_a_review(self):
        for result in ({**self.initial, 'method': 'native_cad_symbol_inventory'}, {**self.initial, 'operation': 'area'}):
            with patch.object(llm, '_request', side_effect=AssertionError('No model needed')):
                self.assertIs(visual_audit.audit_visual_count('Question', result, self.document, Path('new.png')), result)

    def test_count_comes_from_located_objects_and_original_is_immutable(self):
        original = copy.deepcopy(self.initial)
        answer, request, _ = self.audit([obj(), obj([.5, .5, .6, .6])])
        self.assertEqual(answer['value'], 2)
        self.assertEqual(answer['original_detection']['value'], 99)
        self.assertEqual(self.initial, original)
        self.assertEqual(answer['status'], 'needs_review')
        self.assertFalse(answer['count_audit']['independent_verification'])
        self.assertTrue(all(not e['source_verified'] for e in answer['evidence']))
        payload = json.loads(request.call_args.args[0][0]['text'])
        self.assertEqual(payload['candidate_proposals'][0]['id'], 'initial-1')
        self.assertNotIn('value', payload)
        again, _, _ = self.audit([obj(), obj([.5, .5, .6, .6])])
        self.assertEqual([e['id'] for e in answer['evidence']], [e['id'] for e in again['evidence']])
        self.assertEqual(request.call_count, 1)

    def test_crop_dedup_keeps_small_adjacent_objects_and_separate_pages(self):
        document = {**self.document, 'page_count': 2}
        initial = {**self.initial, 'coverage': {'inspected_pages': [1, 2]}}
        images = [image(), image(region=[0, 0, .5, .5]), image(page=2)]
        objects = [obj([.1, .1, .3, .3]), obj([.22, .22, .58, .58], index=1),
                   obj([.31, .1, .4, .3]), obj([.1, .1, .3, .3], index=2)]
        answer, _, _ = self.audit(objects, images, document=document, result=initial)
        self.assertEqual(answer['value'], 3)
        self.assertEqual(answer['count_audit']['duplicates_removed'], 1)
        self.assertEqual([e['page'] for e in answer['evidence']], [1, 1, 2])

    def test_different_target_kinds_are_not_merged(self):
        answer, _, _ = self.audit([obj(label='Door'), obj(label='Window')])
        self.assertEqual(answer['value'], 2)

    def test_generic_labels_reuse_the_initial_target_when_deduplicating(self):
        answer, _, _ = self.audit([obj(label='Door'), obj(label='D1')])
        self.assertEqual(answer['value'], 1)

    def test_selected_region_maps_image_boxes_and_uses_the_selected_page(self):
        document = {**self.document, 'page_count': 3}
        initial = {**self.initial, 'coverage': {'inspected_pages': [2]}}
        answer, _, render = self.audit([obj([.25, .25, .5, .5])], [image(page=2, region=[.2, .2, .6, .6])],
            document=document, result=initial, page=2, scope='document', region=[.2, .2, .6, .6])
        self.assertEqual(answer['value'], 1)
        self.assertEqual(answer['evidence'][0]['page'], 2)
        for actual, expected in zip(answer['evidence'][0]['bbox'], [.3, .3, .4, .4]):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(render.call_args.args[1], [2])

    def test_boundary_objects_are_excluded_by_entire_box_inclusion(self):
        answer, _, _ = self.audit([obj([.1, .1, .4, .4]), obj([.4, .4, .5, .5])],
            region=[.25, .25, .75, .75])
        self.assertEqual(answer['value'], 1)
        self.assertEqual(answer['count_audit']['scope_filtered_objects'], 1)

    def test_invalid_objects_withhold_total_but_keep_valid_candidates(self):
        bad = [obj(index=-1), obj([.8, .8, .2, .2]), obj([float('nan'), 0, 1, 1]), obj(index=True)]
        answer, _, _ = self.audit([obj(), *bad])
        self.assertIsNone(answer['value'])
        self.assertEqual(len(answer['evidence']), 1)
        self.assertEqual(answer['count_audit']['invalid_objects'], 4)

    def test_ambiguity_cannot_disappear_when_duplicate_boxes_merge(self):
        answer, _, _ = self.audit([obj(), obj(ambiguous=True)])
        self.assertIsNone(answer['value'])
        self.assertEqual(len(answer['evidence']), 1)
        self.assertTrue(answer['evidence'][0]['ambiguous'])

    def test_zero_requires_usable_complete_valid_scope(self):
        answer, _, _ = self.audit([])
        self.assertEqual(answer['value'], 0)
        for fields in ({'usable_plan': False}, {'complete_scope': False}, {'objects': 'invalid'}):
            with self.subTest(fields=fields):
                answer, _, _ = self.audit(response=fields)
                self.assertIsNone(answer['value'])

    def test_partial_or_oversized_document_scope_never_calls_a_model(self):
        for document in ({**self.document, 'page_count': 2}, {**self.document, 'page_count': 10**9}):
            with self.subTest(count=document['page_count']):
                answer, request, render = self.audit(document=document)
                self.assertIsNone(answer['value'])
                self.assertEqual(answer['original_detection']['value'], 99)
                self.assertEqual(answer['count_audit']['status'], 'incomplete_scope')
                request.assert_not_called()
                render.assert_not_called()

    def test_wrong_page_source_images_are_rejected(self):
        answer, request, _ = self.audit(images=[image(page=2)])
        self.assertIsNone(answer['value'])
        request.assert_not_called()

    def test_a_page_id_without_full_image_coverage_does_not_establish_scope(self):
        answer, request, _ = self.audit(images=[image(region=[.1, .1, .9, .9])])
        self.assertIsNone(answer['value'])
        request.assert_not_called()
        covered = [image(region=[0, 0, .5, 1]), image(region=[.5, 0, 1, 1])]
        answer, request, _ = self.audit([], covered)
        self.assertEqual(answer['value'], 0)
        self.assertEqual(request.call_count, 1)

    def test_model_failure_preserves_first_detection_for_review(self):
        with patch.object(visual_audit.rendering, 'image_inputs', return_value=[image()]), \
             patch.object(llm, '_request', side_effect=llm.ModelError('The request allowance was reached.')):
            answer = visual_audit.audit_visual_count('How many doors?', self.initial, self.document, Path('new.png'))
        self.assertEqual(answer['value'], 99)
        self.assertEqual(answer['evidence'], self.initial['evidence'])
        self.assertEqual(answer['status'], 'needs_review')
        self.assertEqual(answer['count_audit']['status'], 'unavailable')
        self.assertTrue(any('allowance' in w for w in answer['warnings']))


if __name__ == '__main__':
    unittest.main()

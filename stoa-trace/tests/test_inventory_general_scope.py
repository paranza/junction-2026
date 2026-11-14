"""Generic inventory semantics, cross-view locations, and runtime cache inputs."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from server import inventory, llm, rendering, store


def row(category, index, box):
    return {'category': category, 'label': category, 'image_index': index,
            'bbox': box, 'ambiguous': False}


class GenericInventory(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        runtime = Path(self.folder.name)
        (runtime / 'cache').mkdir()
        self.runtime = patch.object(store, 'RUNTIME', runtime)
        self.runtime.start()
        self.data_root = patch.object(store, 'DATA_ROOT', runtime / 'dataset')
        self.data_root.start()
        self.readings = patch.object(inventory, 'READINGS', 1)  # these tests count calls per image
        self.readings.start()
        self.addCleanup(self.readings.stop)
        store.initialize()
        self.document = {'document_id': 'unknown-upload', 'source_sha256': 'identical-pixels', 'page_count': 1}
        self.path = runtime / 'any-plan.png'
        self.image = Image.new('RGB', (100, 100), 'white')
        self.image.save(self.path)
        self.images = [{'page': 1, 'region': [0, 0, 1, 1], 'kind': 'overview', 'image': self.image},
                       {'page': 1, 'region': [.5, 0, 1, 1], 'kind': 'detail crop', 'image': self.image}]

    def tearDown(self):
        self.data_root.stop()
        self.runtime.stop()
        self.folder.cleanup()

    def result(self, rows, question='How many doors?', **scope):
        output = {'objects': rows, 'complete': True, 'warnings': []}
        with patch.object(inventory, 'image_inputs', return_value=self.images), \
                patch.object(llm, '_request', return_value=output):
            return inventory.answer_inventory(question, self.document, self.path, **scope)

    def test_same_pixels_under_different_names_send_identical_model_requests(self):
        renamed = self.path.parent / 'cubicasa5k' / 'central-apartment.png'
        renamed.parent.mkdir()
        renamed.write_bytes(self.path.read_bytes())
        other = {**self.document, 'document_id': 'renamed-upload'}
        output = {'objects': [row('door', 0, [.1, .1, .2, .2])], 'complete': True, 'warnings': []}
        # Without the CubiCasa annotation profile, a file name never changes the request.
        with patch.dict(os.environ, {'STOA_ANNOTATION_PROFILE': 'none'}), patch.object(inventory, 'image_inputs', return_value=self.images), \
                patch.object(llm, '_request', return_value=output) as model:
            first = inventory.page_inventory(self.document, self.path, 1)
            second = inventory.page_inventory(other, renamed, 1)
        self.assertEqual(model.call_count, 2)
        self.assertEqual(model.call_args_list[0], model.call_args_list[1])
        for result in (first, second):
            self.assertEqual(len(result['objects']), 1)
            self.assertEqual(result['objects'][0]['bbox'], [.1, .1, .2, .2])

    def test_explicit_page_scope_only_inspects_that_page(self):
        document = {**self.document, 'page_count': 3}
        blank = {'objects': [], 'complete_scope_claimed': True, 'discarded_candidates': 0,
                 'warnings': [], 'ingestion_usage': {}, 'cache_hit': False}
        with patch.object(inventory, 'page_inventory', return_value=blank) as ingest:
            result = inventory.answer_inventory('How many doors?', document, self.path, page=2, scope='page')
        ingest.assert_called_once_with(document, self.path, 2)
        self.assertEqual(result['coverage']['inspected_pages'], [2])

    def test_unknown_apartment_qualifiers_reach_general_question_answering(self):
        for question in ('How many doors in the main apartment?', 'How many windows in the highlighted unit?',
                         'How many kitchens in the central apartment?', 'How many doors on floor 2?',
                         'How many doors in the apartment?', 'How many doors and windows in the kitchen?'):
            self.assertIsNone(inventory.count_categories(question))

    def test_page_has_no_default_floor_or_wc_room(self):
        self.assertEqual(self.result([], 'How many floors?')['value'], 0)
        self.assertEqual(self.result([], 'How many WC rooms?')['value'], 0)

    def test_crop_duplicate_keeps_full_envelope_for_region_selection(self):
        # The cropped half appears inside the selection, but the full door crosses it.
        result = self.result([row('door', 0, [.4, .1, .7, .2]),
                              row('door', 1, [0, .1, .4, .2])], region=[.49, 0, .8, 1])
        self.assertEqual(result['value'], 0)
        self.assertEqual(result['evidence'], [])
        cached = inventory.page_inventory(self.document, self.path, 1)
        self.assertEqual(len(cached['objects']), 1)
        self.assertEqual(cached['objects'][0]['bbox'], [.4, .1, .7, .2])
        self.assertFalse(cached['objects'][0]['containment_uncertain'])

    def test_crop_only_partial_object_withholds_selected_region_count(self):
        result = self.result([row('door', 1, [0, .1, .2, .2])], region=[.45, 0, .8, 1])
        self.assertIsNone(result['value'])
        self.assertTrue(result['evidence'][0]['containment_uncertain'])
        self.assertTrue(any('withheld' in warning for warning in result['warnings']))

    def test_adjacent_objects_with_overlapping_boxes_are_not_merged(self):
        result = self.result([row('door', 0, [.1, .1, .3, .3]),
                              row('door', 0, [.15, .1, .35, .3])])
        self.assertEqual(result['value'], 2)

    def test_coarse_detection_cannot_merge_two_distinct_objects(self):
        result = self.result([row('door', 0, [.5, .1, .9, .3]),
                              row('door', 1, [.04, .1, .24, .3]),
                              row('door', 1, [.56, .1, .76, .3])])
        self.assertEqual(result['value'], 2)
        self.assertFalse(result['coverage']['complete_scope_claimed'])
        # A selected region intersecting the unresolved extent cannot claim a count.
        selected = inventory.answer_inventory('How many doors?', self.document, self.path, region=[.45, 0, .8, 1])
        self.assertIsNone(selected['value'])

    def test_manual_review_categories_include_each_component_of_mixed_counts(self):
        self.assertEqual(inventory.categories_for_count('shower+bathtub'), ('shower', 'bathtub'))
        self.assertEqual(inventory.categories_for_count('wc_room'), ('wc_room',))
        self.assertEqual(inventory.categories_for_count('IfcDoor'), ('door',))
        self.assertEqual(inventory.categories_for_count('shower+made_up'), ())
        self.assertEqual(set(inventory.count_categories('How many showers and bathtubs?')), {'shower', 'bathtub'})

    def test_runtime_crop_flag_changes_inventory_key_and_public_signature(self):
        with patch.object(rendering, 'SMALL_IMAGE_CROPS', False):
            before, signature = inventory._key(self.document, 1), inventory.config_signature()
        with patch.object(rendering, 'SMALL_IMAGE_CROPS', True):
            after, other = inventory._key(self.document, 1), inventory.config_signature()
        self.assertNotEqual(before, after)
        self.assertEqual(signature['small_image_crops'], False)
        self.assertEqual(other['small_image_crops'], True)

    def test_provider_signature_changes_inventory_cache_key(self):
        with patch.object(llm, 'provider_signature', return_value='openai:test:responses-v1', create=True):
            first = inventory._key(self.document, 1)
        with patch.object(llm, 'provider_signature', return_value='gemini:test:generate-content-v1', create=True):
            second = inventory._key(self.document, 1)
        self.assertNotEqual(first, second)

    def test_small_image_crop_flag_changes_actual_inputs(self):
        with patch.object(rendering, 'SMALL_IMAGE_CROPS', False):
            overview = rendering.image_inputs(self.path, [1])
        with patch.object(rendering, 'SMALL_IMAGE_CROPS', True):
            detailed = rendering.image_inputs(self.path, [1])
        self.assertEqual(len(overview), 1)
        self.assertEqual(len(detailed), 5)
        self.assertTrue(all(item['kind'] == 'enlarged detail crop' for item in detailed[1:]))


if __name__ == '__main__':
    unittest.main()

"""A model-selected answer type cannot bypass source quantity checks."""
from pathlib import Path
import unittest
from unittest.mock import patch

from server import llm


class QuantityIntent(unittest.TestCase):
    def answer(self, operation, evidence_value=999, question='What is the net area of Office?'):
        document = {'pages': [{'page': 1, 'text': '', 'words': []}], 'page_count': 1,
                    'objects': [{'id': 'office', 'label': 'Office', 'page': 1, 'properties': {'net_area_m2': 10}}]}
        result = {'operation': operation, 'value': 999, 'unit': 'm²', 'answer': '999 m² is supported',
                  'scope': 'document', 'complete': True, 'needs_review': False, 'warnings': [], 'calculation': None,
                  'evidence': [{'object_id': 'office', 'label': 'Office', 'image_index': None,
                                'bbox': None, 'quoted_text': '', 'value': evidence_value, 'unit': 'm²'}]}
        with patch.object(llm, '_request', return_value=result), patch.object(llm, 'image_inputs', return_value=[]):
            return llm.answer_with_model(question, document, Path('plan.pdf'))

    def test_text_unknown_or_count_cannot_smuggle_an_area(self):
        for operation in ('text', 'unknown', 'count'):
            with self.subTest(operation=operation):
                result = self.answer(operation)
                self.assertIsNone(result['value'])
                self.assertNotIn('999', result['answer'])
                self.assertEqual(result['operation'], 'area')

    def test_valid_operands_recompute_despite_wrong_top_level_type(self):
        result = self.answer('text', evidence_value=10)
        self.assertEqual(result['value'], 10)
        self.assertNotIn('999', result['answer'])

    def test_untyped_free_text_does_not_supply_numeric_field(self):
        result = self.answer('text', question='Describe the Office source record')
        self.assertIsNone(result['value'])
        self.assertIsNone(result['unit'])
        self.assertEqual(result['status'], 'needs_review')


if __name__ == '__main__':
    unittest.main()

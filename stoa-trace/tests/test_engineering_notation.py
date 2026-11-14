"""Cross-drawing notation checks; no provider calls or reference lookups."""
import unittest

from server.verification import _text_candidates, convert_quantity, ground_native_evidence
from server.app import _guard_visual_measurements


class EngineeringNotation(unittest.TestCase):
    def test_unit_aliases_are_dimension_checked(self):
        self.assertAlmostEqual(convert_quantity(8, 'inches', 'mm'), 203.2)
        self.assertAlmostEqual(convert_quantity(6, 'feet', 'metres'), 1.8288)
        self.assertAlmostEqual(convert_quantity(250, 'square feet', 'm²'), 23.22576)
        self.assertIsNone(convert_quantity(8, 'inches', 'm²'))

    def test_printed_prime_dimensions_and_fractions(self):
        for quote, expected in [('16" HEADER', 16), ('9″ DIA', 9), ("6'-8\" CLEAR", 80),
                                ('1 1/2" PIPE', 1.5), ('3/4" PIPE', .75)]:
            with self.subTest(quote=quote):
                candidates = list(_text_candidates(quote, 'length'))
                self.assertEqual(len(candidates), 1)
                self.assertEqual(candidates[0]['value'], expected)
        self.assertEqual(list(_text_candidates('1/0" PIPE', 'length')), [])

    def test_locale_numbers_do_not_truncate_or_change_decimal_commas(self):
        for quote, expected in [('12,345 SF', 12345), ('1,234.56 SF', 1234.56),
                                ('1.234,56 m²', 1234.56), ('38,75 m²', 38.75),
                                ('38,750 m²', 38.750)]:
            with self.subTest(quote=quote):
                candidates = list(_text_candidates(quote, 'area'))
                self.assertEqual(len(candidates), 1)
                self.assertAlmostEqual(candidates[0]['value'], expected)

    def test_native_quote_cannot_be_laundered_by_a_matching_value(self):
        assertion = {'quoted_text': '16" HEADER', 'value': 16, 'unit': 'inches'}
        result, _ = ground_native_evidence({'text': '16" HEADER'}, assertion, 'length')
        self.assertEqual(result['value'], 16)
        self.assertTrue(result['source_verified'])
        wrong, _ = ground_native_evidence({'text': '8" HEADER'}, assertion, 'length')
        self.assertIsNone(wrong['value'])

    def result(self, quote='225 SLAB, D16 @ 250', value=225, unit='mm'):
        return {'operation': 'length', 'value': value, 'unit': unit, 'answer': 'Provisional reading',
                'evidence': [{'value': value, 'unit': unit, 'quoted_text': quote, 'source_verified': False}],
                'warnings': [], 'status': 'visual', 'calculation': 'quoted dimension'}

    def test_explicit_drawing_unit_declaration_remains_provisional(self):
        result = _guard_visual_measurements(self.result(), 'What is the slab thickness? Dimensions on this drawing are millimetres.')
        self.assertEqual(result['value'], 225)
        self.assertEqual(result['status'], 'needs_review')
        self.assertFalse(result['evidence'][0]['source_verified'])
        self.assertEqual(result['measurement_basis'], 'quoted_value_user_declared_drawing_units')

    def test_output_units_assumptions_conflicts_and_missing_literals_are_rejected(self):
        for question in ('What is the thickness? Answer in mm.',
                         'What is the thickness? Assume mm.',
                         'Dimensions are mm. Dimensions are inches.'):
            self.assertIsNone(_guard_visual_measurements(self.result(), question)['value'])
        for result in (self.result(value=999), self.result(quote='225 inches'), self.result(quote='D225')):
            self.assertIsNone(_guard_visual_measurements(result, 'Dimensions are mm. What is the thickness?')['value'])


if __name__ == '__main__':
    unittest.main()

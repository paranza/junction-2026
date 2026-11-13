"""Source identity cannot turn a model assertion into a source measurement."""
import unittest

from server.verification import ground_native_evidence, convert_quantity


class Grounding(unittest.TestCase):
    def setUp(self):
        self.room = {'id': 'room-1', 'label': 'Office', 'properties': {'net_area_m2': 10, 'gross_area_m2': 12}}

    def check(self, value, unit='m²', quote='', question='What is the net area?'):
        return ground_native_evidence(self.room, {'value': value, 'unit': unit, 'quoted_text': quote}, 'area', question)

    def test_existing_id_does_not_validate_fabricated_value(self):
        item, warnings = self.check(999)
        self.assertIsNone(item['value'])
        self.assertFalse(item['verification']['quantity'])
        self.assertTrue(warnings)
        self.assertEqual(item['properties']['net_area_m2'], 10)

    def test_exact_typed_value_has_inspectable_property_path(self):
        item, warnings = self.check(10)
        self.assertEqual(item['value'], 10)
        self.assertEqual(item['verification']['property_path'], 'properties.net_area_m2')
        self.assertTrue(item['source_verified'])
        self.assertFalse(item['verification']['semantic_selection_verified'])
        self.assertFalse(warnings)

    def test_gross_cannot_borrow_net_or_untyped_area(self):
        item, _ = self.check(10, question='What is the gross area?')
        self.assertIsNone(item['value'])
        item, _ = self.check(12, question='What is the gross area?')
        self.assertEqual(item['value'], 12)

    def test_compatible_units_are_checked_and_converted(self):
        item, _ = self.check(10000000, unit='mm²')
        self.assertEqual(item['value'], 10000000)
        self.assertAlmostEqual(convert_quantity(1, 'ft²', 'm²'), .09290304)
        self.assertIsNone(convert_quantity(10, 'm', 'm²'))

    def test_invalid_quote_rejects_even_a_matching_operand(self):
        item, warnings = self.check(10, quote='Office has 10 square metres')
        self.assertIsNone(item['value'])
        self.assertEqual(item['quoted_text'], '')
        self.assertFalse(item['verification']['quote'])
        self.assertTrue(warnings)

    def test_native_text_quote_and_scalar_support(self):
        item, warnings = ground_native_evidence({'id': 'label-1', 'text': 'Workshop 24.5 m²'},
            {'value': 24.5, 'unit': 'm²', 'quoted_text': '24.5 m²'}, 'area')
        self.assertEqual(item['value'], 24.5)
        self.assertEqual(item['verification']['property_path'], 'native_text')
        self.assertFalse(warnings)

    def test_identity_does_not_prove_a_count_selection(self):
        item, _ = ground_native_evidence(self.room, {'value': 999, 'unit': 'count'}, 'count')
        self.assertIsNone(item['value'])
        self.assertFalse(item['source_verified'])
        self.assertTrue(item['verification']['identity'])

    def test_nonfinite_negative_and_wrong_dimension_rejected(self):
        for value, unit in [(float('nan'), 'm²'), (float('inf'), 'm²'), (-1, 'm²'), (True, 'm²'), (10, 'm')]:
            with self.subTest(value=value, unit=unit):
                item, _ = self.check(value, unit)
                self.assertIsNone(item['value'])


if __name__ == '__main__':
    unittest.main()

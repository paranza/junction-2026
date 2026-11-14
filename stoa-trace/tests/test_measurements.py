"""Measurements need real source dimensions or explicit page calibration."""
import copy
import math
import unittest

from server.measurements import (MeasurementError, calibrated_length,
                                 calibrated_polygon_area, length_in_metres, rectangle_area)


SQUARE = [[0, 0], [1, 0], [1, 1], [0, 1]]


class CalibratedGeometry(unittest.TestCase):
    def setUp(self):
        self.calibration = {'page': 1, 'points': [[0, 0], [1, 0]], 'value': 10, 'unit': 'm',
                            'document_id': 'new-upload'}
        self.context = {'page': 1, 'image_width': 2000, 'image_height': 1000,
                        'document_id': 'new-upload'}

    def area(self, polygon=SQUARE, calibration=None, **context):
        return calibrated_polygon_area(polygon, self.calibration if calibration is None else calibration,
                                       **{**self.context, **context})

    def test_aspect_ratio_and_provenance(self):
        before = copy.deepcopy(self.calibration)
        result = self.area()
        self.assertAlmostEqual(result['value'], 50)
        self.assertEqual(result['unit'], 'm²')
        self.assertEqual(result['confidence_basis'], 'user_calibration')
        self.assertFalse(result['source_verified'])
        self.assertTrue(result['requires_review'])
        self.assertEqual(result['provenance']['calibration']['length_pixels'], 2000)
        self.assertEqual(result['provenance']['metres_per_pixel'], .005)
        self.assertEqual(self.calibration, before)

    def test_diagonal_calibration_uses_both_axes(self):
        calibration = {**self.calibration, 'points': [[0, 0], [1, 1]], 'value': math.sqrt(5)}
        self.assertAlmostEqual(self.area(calibration=calibration)['value'], 2)

    def test_linear_and_squared_unit_conversions(self):
        for value, unit, expected in [(1000, 'mm', 1), (100, 'cm', 1), (10, 'ft', 3.048),
                                      (12, 'in', .3048), (1, 'feet', .3048)]:
            self.assertAlmostEqual(length_in_metres(value, unit), expected)
        calibration = {**self.calibration, 'value': 10, 'unit': 'ft'}
        result = self.area(calibration=calibration, image_height=2000, output_unit='ft²')
        self.assertAlmostEqual(result['value'], 100)

    def test_length_measurement_and_output_units(self):
        result = calibrated_length([[0, 0], [.5, 0]], self.calibration,
                                   output_unit='cm', **self.context)
        self.assertAlmostEqual(result['value'], 500)
        self.assertEqual(result['unit'], 'cm')

    def test_concave_and_closed_polygons(self):
        triangle = [[0, 0], [1, 0], [0, 1], [0, 0]]
        self.assertAlmostEqual(self.area(triangle)['value'], 25)
        concave = [[0, 0], [1, 0], [1, .5], [.5, .5], [.5, 1], [0, 1]]
        self.assertAlmostEqual(self.area(concave)['value'], 37.5)

    def test_scale_is_required_and_no_default_is_used(self):
        for calibration in (None, {}, {'page': 1, 'points': [[0, 0], [1, 0]]},
                            {**self.calibration, 'value': 0},
                            {**self.calibration, 'points': [[.5, .5], [.5, .5]]}):
            with self.subTest(calibration=calibration), self.assertRaises(MeasurementError):
                calibrated_polygon_area(SQUARE, calibration, **self.context)

    def test_page_and_document_scope_cannot_be_substituted(self):
        for context in ({'page': 2}, {'page': True}, {'page': 1.0}, {'document_id': 'other'}):
            with self.subTest(context=context), self.assertRaises(MeasurementError):
                self.area(**context)
        with self.assertRaises(MeasurementError):
            self.area(calibration={k: v for k, v in self.calibration.items() if k != 'document_id'})

    def test_self_intersection_touches_duplicates_and_degeneracy_rejected(self):
        invalid = [[[.1, .1], [.9, .9], [.1, .8], [.8, .1]],
                   [[0, 0], [1, 0], [.5, 0], [1, 1], [0, 1]],
                   [[0, 0], [1, 0], [1, 0], [0, 1]],
                   [[0, 0], [.5, .5], [1, 1]], [[0, 0], [1, 1]],
                   [[0, 0], [1, 0], [1.1, 1]], [[0, 0], [1, 0], [-.1, 1]]]
        for polygon in invalid:
            with self.subTest(polygon=polygon), self.assertRaises(MeasurementError):
                self.area(polygon)

    def test_invalid_number_and_dimension_units_rejected(self):
        for value in (float('nan'), float('inf'), True, -2):
            with self.subTest(value=value), self.assertRaises(MeasurementError):
                self.area(calibration={**self.calibration, 'value': value})
        for context in ({'image_width': 0}, {'image_height': float('inf')}, {'image_width': True}):
            with self.subTest(context=context), self.assertRaises(MeasurementError):
                self.area(**context)
        for unit in ('m²', 'pixels', '', None):
            with self.subTest(unit=unit), self.assertRaises(MeasurementError):
                self.area(calibration={**self.calibration, 'unit': unit})
        with self.assertRaises(MeasurementError):
            self.area(output_unit='m')
        with self.assertRaises(MeasurementError):
            calibrated_length([[0, 0], [0, 0]], self.calibration, **self.context)


class VerifiedRectangle(unittest.TestCase):
    def setUp(self):
        self.width = {'id': 'source-width', 'value': 1000, 'unit': 'mm',
                      'source_verified': True, 'page': 1, 'document_id': 'new-upload'}
        self.height = {'id': 'source-height', 'value': 200, 'unit': 'cm',
                       'source_verified': True, 'page': 1, 'document_id': 'new-upload'}

    def area(self, width=None, height=None, **options):
        return rectangle_area(self.width if width is None else width,
                              self.height if height is None else height,
                              **{'rectangle_confirmed': True, **options})

    def test_rectangle_uses_distinct_verified_source_lengths(self):
        result = self.area(page=1, document_id='new-upload')
        self.assertAlmostEqual(result['value'], 2)
        self.assertEqual(result['confidence_basis'], 'verified_source_dimensions')
        self.assertTrue(result['provenance']['operand_quantities_verified'])
        self.assertFalse(result['source_verified'])
        self.assertTrue(result['requires_review'])

    def test_unverified_dimensions_and_unconfirmed_shape_rejected(self):
        for width in ({**self.width, 'source_verified': False},
                      {**self.width, 'source_verified': 'true'},
                      {**self.width, 'id': ''}, {**self.width, 'unit': 'm²'},
                      {**self.width, 'id': self.height['id']}):
            with self.subTest(width=width), self.assertRaises(MeasurementError):
                self.area(width=width)
        for confirmation in (False, None, 1, 'true'):
            with self.subTest(confirmation=confirmation), self.assertRaises(MeasurementError):
                self.area(rectangle_confirmed=confirmation)

    def test_scope_and_nonfinite_results_rejected(self):
        for height in ({**self.height, 'page': 2},
                       {**self.height, 'document_id': 'other'},
                       {**self.height, 'value': float('nan')},
                       {**self.height, 'page': None}):
            with self.subTest(height=height), self.assertRaises(MeasurementError):
                self.area(height=height)
        with self.assertRaises(MeasurementError):
            self.area(page=2)
        with self.assertRaises(MeasurementError):
            self.area(document_id='other')
        with self.assertRaises(MeasurementError):
            self.area(width={**self.width, 'value': 1e308, 'unit': 'm'},
                      height={**self.height, 'value': 1e308, 'unit': 'm'})


if __name__ == '__main__':
    unittest.main()

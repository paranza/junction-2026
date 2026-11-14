"""Geometry measurements with an explicit scale or verified dimensions.

No filename, drawing style, image DPI or typical object size supplies a scale.
Coordinates are normalized to the same page. Image width and height are both
used, so a diagonal calibration and a non-square image retain their true aspect.

The returned quantities describe the supplied polygon/segment or rectangle.
They do not establish that it is the right room, or that its area is net/gross.
User calibration is a review judgment, never native-source verification.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


class MeasurementError(ValueError):
    """The supplied geometry or source basis cannot establish a measurement."""


_LENGTH_UNITS = {
    'm': ('m', 1.0), 'meter': ('m', 1.0), 'meters': ('m', 1.0),
    'metre': ('m', 1.0), 'metres': ('m', 1.0),
    'cm': ('cm', 0.01), 'centimeter': ('cm', 0.01), 'centimeters': ('cm', 0.01),
    'centimetre': ('cm', 0.01), 'centimetres': ('cm', 0.01),
    'mm': ('mm', 0.001), 'millimeter': ('mm', 0.001), 'millimeters': ('mm', 0.001),
    'millimetre': ('mm', 0.001), 'millimetres': ('mm', 0.001),
    'ft': ('ft', 0.3048), 'foot': ('ft', 0.3048), 'feet': ('ft', 0.3048),
    "'": ('ft', 0.3048), '′': ('ft', 0.3048),
    'in': ('in', 0.0254), 'inch': ('in', 0.0254), 'inches': ('in', 0.0254),
    '"': ('in', 0.0254), '″': ('in', 0.0254),
}
_AREA_UNITS = {'m2': ('m²', 1.0), 'cm2': ('cm²', 0.0001),
               'mm2': ('mm²', 0.000001), 'ft2': ('ft²', 0.09290304),
               'in2': ('in²', 0.00064516), 'sqm': ('m²', 1.0),
               'sqft': ('ft²', 0.09290304)}
_MAX_POLYGON_POINTS = 512


def _number(value, label, *, positive=True):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise MeasurementError(f'{label} must be a finite number.')
    if value < 0 or (positive and value == 0):
        raise MeasurementError(f'{label} must be positive.')
    return float(value)


def _page(value):
    if type(value) is not int or value < 1:
        raise MeasurementError('Page must be a positive integer.')
    return value


def _unit(value, dimension):
    if not isinstance(value, str):
        raise MeasurementError(f'An explicit {dimension} unit is required.')
    key = value.casefold().strip().replace(' ', '').replace('^', '').replace('²', '2')
    units = _LENGTH_UNITS if dimension == 'length' else _AREA_UNITS
    if key not in units:
        raise MeasurementError(f'Unsupported or incompatible {dimension} unit.')
    return units[key]


def length_in_metres(value, unit):
    """Convert an explicitly unit-bearing positive length to metres."""
    _, factor = _unit(unit, 'length')
    converted = _number(value, 'Length') * factor
    return _number(converted, 'Converted length')


def _points(value, *, count=None, polygon=False):
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise MeasurementError('Normalized points must be a sequence of [x, y] pairs.')
    if count is not None and len(value) != count:
        raise MeasurementError(f'Exactly {count} points are required.')
    if polygon and not 3 <= len(value) <= _MAX_POLYGON_POINTS + 1:
        raise MeasurementError(f'A polygon needs 3 to {_MAX_POLYGON_POINTS} vertices.')
    result = []
    for point in value:
        if not isinstance(point, Sequence) or isinstance(point, (str, bytes)) or len(point) != 2:
            raise MeasurementError('Each normalized point must contain x and y.')
        x, y = (_number(v, 'Coordinate', positive=False) for v in point)
        if x > 1 or y > 1:
            raise MeasurementError('Normalized coordinates must be between zero and one.')
        result.append((x, y))
    if polygon and len(result) > 1 and result[0] == result[-1]:
        result.pop()
    if polygon and (len(result) < 3 or len(result) > _MAX_POLYGON_POINTS
                    or len(set(result)) != len(result)):
        raise MeasurementError('Polygon vertices must be distinct, apart from an optional closing point.')
    return result


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a, b, point):
    eps = 1e-12
    return (abs(_cross(a, b, point)) <= eps
            and min(a[0], b[0]) - eps <= point[0] <= max(a[0], b[0]) + eps
            and min(a[1], b[1]) - eps <= point[1] <= max(a[1], b[1]) + eps)


def _intersect(a, b, c, d):
    ca, cb, cc, cd = _cross(a, b, c), _cross(a, b, d), _cross(c, d, a), _cross(c, d, b)
    if ((ca > 0 > cb or cb > 0 > ca) and (cc > 0 > cd or cd > 0 > cc)):
        return True
    return (_on_segment(a, b, c) or _on_segment(a, b, d)
            or _on_segment(c, d, a) or _on_segment(c, d, b))


def _polygon_area(points):
    n = len(points)
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if _intersect(a, b, points[j], points[(j + 1) % n]):
                raise MeasurementError('The polygon intersects or touches itself.')
    area = abs(math.fsum(points[i][0] * points[(i + 1) % n][1]
                         - points[(i + 1) % n][0] * points[i][1] for i in range(n))) / 2
    if area <= 1e-12:
        raise MeasurementError('The polygon has no usable area.')
    return area


def _scale(calibration, *, page, image_width, image_height, document_id):
    page = _page(page)
    width, height = _number(image_width, 'Image width'), _number(image_height, 'Image height')
    if not isinstance(calibration, Mapping):
        raise MeasurementError('An explicit calibration is required; there is no default scale.')
    if _page(calibration.get('page')) != page:
        raise MeasurementError('Calibration and target must be on the same page.')
    if document_id is not None and (not isinstance(document_id, str) or not document_id
                                    or calibration.get('document_id') != document_id):
        raise MeasurementError('Calibration and target must belong to the same document.')
    points = _points(calibration.get('points'), count=2)
    pixels = math.hypot((points[1][0] - points[0][0]) * width,
                        (points[1][1] - points[0][1]) * height)
    if not math.isfinite(pixels) or pixels <= 1e-9:
        raise MeasurementError('Calibration endpoints must define a nonzero pixel length.')
    known_value = _number(calibration.get('value'), 'Calibration length')
    known_unit, _ = _unit(calibration.get('unit'), 'length')
    metres = length_in_metres(known_value, known_unit)
    per_pixel = _number(metres / pixels, 'Calibration scale')
    provenance = {'page': page, 'image_width': width, 'image_height': height,
                  'calibration': {'page': page, 'points': [list(p) for p in points],
                                  'value': known_value, 'unit': known_unit,
                                  'length_metres': metres, 'length_pixels': pixels},
                  'metres_per_pixel': per_pixel}
    if document_id is not None:
        provenance['document_id'] = document_id
        provenance['calibration']['document_id'] = document_id
    return width, height, per_pixel, provenance


def _result(value, unit, method, provenance, *, basis='user_calibration'):
    return {'value': _number(value, 'Measured quantity'), 'unit': unit, 'method': method,
            'confidence_basis': basis, 'source_verified': False, 'requires_review': True,
            'provenance': provenance,
            'warnings': ['The supplied geometry and scale establish arithmetic, not room selection, net/gross semantics or engineering correctness.']}


def calibrated_polygon_area(polygon, calibration, *, page, image_width, image_height,
                            document_id=None, output_unit='m²'):
    """Measure a simple page polygon from a user-provided real-world length.

    Calibration contains ``page``, normalized ``points`` (two endpoints),
    ``value`` and a length ``unit``. When document_id is supplied, calibration
    must carry that exact document_id too. No scale is inferred from image DPI.
    """
    width, height, scale, provenance = _scale(calibration, page=page, image_width=image_width,
                                             image_height=image_height, document_id=document_id)
    points = _points(polygon, polygon=True)
    pixel_area = _number(_polygon_area(points) * width * height, 'Pixel area')
    area_metres = _number(pixel_area * scale * scale, 'Calibrated area')
    unit, factor = _unit(output_unit, 'area')
    provenance.update(polygon=[list(p) for p in points], area_pixels=pixel_area,
                      formula='polygon_area_pixels * metres_per_pixel ** 2')
    return _result(area_metres / factor, unit, 'calibrated_polygon_area', provenance)


def calibrated_length(points, calibration, *, page, image_width, image_height,
                      document_id=None, output_unit='m'):
    """Measure a segment using calibration on the same page and image basis."""
    width, height, scale, provenance = _scale(calibration, page=page, image_width=image_width,
                                             image_height=image_height, document_id=document_id)
    target = _points(points, count=2)
    pixel_length = _number(math.hypot((target[1][0] - target[0][0]) * width,
                                     (target[1][1] - target[0][1]) * height), 'Target pixel length')
    unit, factor = _unit(output_unit, 'length')
    provenance.update(points=[list(p) for p in target], length_pixels=pixel_length,
                      formula='segment_length_pixels * metres_per_pixel')
    return _result(pixel_length * scale / factor, unit, 'calibrated_length', provenance)


def rectangle_area(width_operand, height_operand, *, rectangle_confirmed=False,
                   page=None, document_id=None, output_unit='m²'):
    """Compute rectangular area from two previously verified source lengths.

    Callers must establish the rectangle semantics and each operand using
    trusted source validation. Never copy ``source_verified`` or rectangle
    confirmation directly from a model/client assertion. Each operand needs
    ``id``, ``value``, a length ``unit`` and literal ``source_verified=True``.
    Optional page/document metadata must agree; supplied target metadata is
    required on both operands. This helper does not infer shape or net area.
    """
    if rectangle_confirmed is not True:
        raise MeasurementError('Rectangle geometry must be independently confirmed.')
    operands = []
    for label, operand in (('Width', width_operand), ('Height', height_operand)):
        if (not isinstance(operand, Mapping) or operand.get('source_verified') is not True
                or not isinstance(operand.get('id'), str) or not operand['id'].strip()):
            raise MeasurementError(f'{label} must be a verified, identified source length.')
        metres = length_in_metres(operand.get('value'), operand.get('unit'))
        operands.append({'id': operand['id'], 'value': _number(operand['value'], label),
                         'unit': _unit(operand['unit'], 'length')[0], 'metres': metres,
                         'page': operand.get('page'), 'document_id': operand.get('document_id')})
    if operands[0]['id'] == operands[1]['id']:
        raise MeasurementError('Width and height require distinct source operands.')
    for field, expected in (('page', page), ('document_id', document_id)):
        values = [operand[field] for operand in operands]
        if any(value is not None for value in values) and values[0] != values[1]:
            raise MeasurementError(f'Both dimensions must refer to the same {field}.')
        if expected is not None and any(value != expected for value in values):
            raise MeasurementError(f'Both dimensions must match the target {field}.')
    if page is not None:
        _page(page)
    for operand in operands:
        if operand['page'] is not None:
            _page(operand['page'])
    unit, factor = _unit(output_unit, 'area')
    provenance = {'operands': operands, 'rectangle_confirmed_by_caller': True,
                  'formula': 'width_metres * height_metres', 'operand_quantities_verified': True}
    if page is not None:
        provenance['page'] = page
    if document_id is not None:
        provenance['document_id'] = document_id
    return _result(operands[0]['metres'] * operands[1]['metres'] / factor, unit,
                   'verified_rectangle_dimensions', provenance, basis='verified_source_dimensions')

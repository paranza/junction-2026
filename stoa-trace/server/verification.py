"""Ground model assertions in native records before using them as operands.

Object identity, exact text and numeric support are separate checks. These
checks establish provenance, not that the model selected the right object.
"""
from __future__ import annotations

import math
import re
import unicodedata


def normalized(text):
    return " ".join(unicodedata.normalize('NFKC', str(text or '')).casefold().split())


_UNITS = {
    'm': ('length', 1.0), 'metre': ('length', 1.0), 'meter': ('length', 1.0),
    'mm': ('length', .001), 'cm': ('length', .01), 'ft': ('length', .3048),
    'in': ('length', .0254), 'm2': ('area', 1.0), 'sqm': ('area', 1.0),
    'mm2': ('area', 1e-6), 'cm2': ('area', 1e-4), 'ft2': ('area', .09290304),
    'sqft': ('area', .09290304), 'sf': ('area', .09290304),
    'm3': ('volume', 1.0), 'mm3': ('volume', 1e-9), 'cm3': ('volume', 1e-6),
    'ft3': ('volume', .028316846592), 'l': ('volume', .001),
    'count': ('count', 1.0),
}


def unit_spec(unit):
    key = normalized(unit).replace(' ', '').replace('^', '').replace('²', '2').replace('³', '3')
    return _UNITS.get(key)


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def convert_quantity(value, source_unit, target_unit):
    source, target = unit_spec(source_unit), unit_spec(target_unit)
    if not finite_number(value) or not source or not target or source[0] != target[0]:
        return None
    return value * source[1] / target[1]


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in {'source_path', 'native_source_path', 'guid', 'id', 'cad_handle'}:
                yield from _strings(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _strings(item)


def source_text(record):
    """Only source content, never JSON key names or the model's assertion."""
    return '\n'.join(_strings({key: record.get(key) for key in ('text', 'label', 'properties')}))


def _requested_role(question, operation):
    q = normalized(question)
    if re.search(r'\bgross\b|\bbrutto', q):
        return 'gross'
    if re.search(r'\bnet\b|\bnetto', q):
        return 'net'
    return None


def _typed_candidates(properties, operation, prefix='properties'):
    for key, value in properties.items():
        path = prefix + '.' + str(key)
        if isinstance(value, dict):
            # Explicit quantity records can carry their own units and source path.
            scalar = value.get('value')
            unit = value.get('unit')
            spec = unit_spec(unit)
            if finite_number(scalar) and spec and spec[0] == operation:
                yield {'value': scalar, 'unit': unit, 'property_path': path,
                       'role': 'gross' if 'gross' in key.lower() else 'net' if 'net' in key.lower() else None}
            else:
                yield from _typed_candidates(value, operation, path)
            continue
        if not finite_number(value):
            continue
        match = re.fullmatch(r'(?P<name>[a-z_]+)_(?P<unit>m2|m3|ft2|ft3|mm2|mm3|cm2|cm3|mm|cm|ft|m)', str(key))
        if not match:
            continue
        name, unit = match.group('name'), match.group('unit')
        spec = unit_spec(unit)
        if not spec or spec[0] != operation:
            continue
        if operation == 'area' and 'area' not in name:
            continue
        if operation == 'volume' and 'volume' not in name:
            continue
        if operation == 'length' and not any(word in name for word in ('length', 'width', 'height', 'perimeter')):
            continue
        yield {'value': value, 'unit': unit, 'property_path': path,
               'role': 'gross' if 'gross' in name else 'net' if 'net' in name else None}


_SCALAR = re.compile(r'(?<![\w.])([0-9]+(?:[.,][0-9]+)?)\s*(m[²³23]|ft[²³23]|sq\.?\s*ft|sf|sqm|mm|cm|metres?|meters?|ft|in|m)\b', re.I)


def _text_candidates(text, operation):
    for match in _SCALAR.finditer(text):
        unit = re.sub(r'[.\s]', '', match.group(2).lower())
        if unit in {'metres', 'meters'}:
            unit = 'm'
        spec = unit_spec(unit)
        if spec and spec[0] == operation:
            yield {'value': float(match.group(1).replace(',', '.')), 'unit': unit,
                   'property_path': 'native_text', 'role': None}


def ground_native_evidence(linked, assertion, operation, question=''):
    """Return a native record plus checked assertion fields and warnings.

No asserted value is copied into a source record. A numeric value survives only
if a compatible typed property (or an exact quoted native scalar) supports it.
Unsupported values stay null, so callers cannot silently sum them.
"""
    grounded = {**linked, 'label': linked.get('label') or assertion.get('label') or 'Source object',
                'evidence_kind': 'native', 'value': None, 'unit': None,
                'quoted_text': '', 'source_verified': False}
    warnings = []
    text = source_text(linked)
    quote = str(assertion.get('quoted_text') or '').strip()
    quote_ok = bool(quote) and normalized(quote) in normalized(text)
    if quote_ok:
        grounded['quoted_text'] = quote
    elif quote:
        warnings.append('A quoted excerpt did not match the cited native record and was discarded.')
    checks = {'identity': True, 'quote': quote_ok if quote else None, 'quantity': None,
              'property_path': None, 'semantic_selection_verified': False}
    grounded['verification'] = checks
    if operation not in {'area', 'length', 'volume'}:
        grounded['source_verified'] = quote_ok
        return grounded, warnings
    value, unit = assertion.get('value'), assertion.get('unit')
    spec = unit_spec(unit)
    if not finite_number(value) or not spec or spec[0] != operation:
        checks['quantity'] = False
        warnings.append('The cited quantity has no supported finite value and compatible unit.')
        return grounded, warnings
    # A false quote cannot be laundered by a coincidentally matching number.
    if quote and not quote_ok:
        checks['quantity'] = False
        return grounded, warnings
    role = _requested_role(question, operation)
    candidates = list(_typed_candidates(linked.get('properties') or {}, operation))
    if role:
        candidates = [item for item in candidates if item['role'] == role]
    if quote_ok and role is None:
        candidates += list(_text_candidates(quote, operation))
    matches = []
    for item in candidates:
        converted = convert_quantity(item['value'], item['unit'], unit)
        if converted is not None and math.isclose(converted, value, rel_tol=1e-8, abs_tol=1e-8):
            matches.append((item, converted))
    if not matches:
        checks['quantity'] = False
        warnings.append('The model quantity did not match a compatible quantity in the cited source record.')
        return grounded, warnings
    selected, converted = matches[0]
    grounded.update(value=converted, unit=unit, source_verified=True)
    checks.update(quantity=True, property_path=selected['property_path'])
    return grounded, warnings

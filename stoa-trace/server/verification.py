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
    key = {'inches': 'in', 'inch': 'in', 'feet': 'ft', 'foot': 'ft',
           'metres': 'm', 'meters': 'm', 'millimetres': 'mm', 'millimeters': 'mm',
           'centimetres': 'cm', 'centimeters': 'cm', 'squarefeet': 'ft2',
           'squaremetres': 'm2', 'squaremeters': 'm2', 'sq.ft': 'ft2'}.get(key, key)
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
        if operation == 'length' and not any(word in name for word in ('length', 'width', 'height', 'perimeter','thickness')):
            continue
        yield {'value': value, 'unit': unit, 'property_path': path,
               'role': 'gross' if 'gross' in name else 'net' if 'net' in name else None}


_NUMBER = r'[0-9]+(?:[.,][0-9]+)*'
_SCALAR = re.compile(r'(?<![\w.,/])(' + _NUMBER + r')\s*(m[²³23]|ft[²³23]|sq\.?\s*ft|sf|sqm|mm|cm|metres?|meters?|millimetres?|millimeters?|centimetres?|centimeters?|feet|foot|inches|inch|ft|in|m)\b', re.I)
_IMPERIAL = re.compile(r'''(?<![\w./])(?:(\d+)\s*['′]\s*(?:-\s*)?)?(\d+(?:\.\d+)?(?:\s+\d+/\d+)?|\d+/\d+)\s*["″]''')


def printed_number(token, unit):
    """Parse explicit engineering numbers without guessing ambiguous metric groups."""
    if ',' in token and '.' in token:
        # The final separator is decimal; the other must form groups of three.
        decimal, grouping = (',', '.') if token.rfind(',') > token.rfind('.') else ('.', ',')
        integer, fraction = token.rsplit(decimal, 1)
        if not re.fullmatch(r'\d{1,3}(?:' + re.escape(grouping) + r'\d{3})+', integer):
            return None
        token = integer.replace(grouping, '') + '.' + fraction
    elif ',' in token:
        spec = unit_spec(unit)
        imperial = spec and spec[1] in {.3048, .0254, .09290304, .028316846592}
        if re.fullmatch(r'\d{1,3}(?:,\d{3})+', token) and imperial:
            token = token.replace(',', '')
        elif token.count(',') == 1:
            token = token.replace(',', '.')
        else:
            return None
    try:
        value = float(token)
    except ValueError:
        return None
    return value if finite_number(value) else None


def _text_candidates(text, operation):
    if operation == 'length':
        compound_spans = []
        for match in _IMPERIAL.finditer(text):
            compound_spans.append(match.span())
            try:
                parts = match.group(2).split()
                last = parts[-1]
                if '/' in last:
                    numerator, denominator = map(int, last.split('/'))
                    inches = numerator / denominator + (float(parts[0]) if len(parts) == 2 else 0)
                else:
                    inches = float(last)
                value = 12 * int(match.group(1) or 0) + inches
            except (ValueError, ZeroDivisionError):
                continue
            yield {'value': value, 'unit': 'in', 'property_path': 'native_text', 'role': None}
        # Graphic scales and many imperial dimensions show feet alone. Do not
        # reinterpret the feet component of a combined feet-and-inches value.
        for match in re.finditer(r'(?<![\w.,])(' + _NUMBER + r')\s*[\'′’]', text):
            if any(start <= match.start() < end for start,end in compound_spans):continue
            value=printed_number(match.group(1),'ft')
            if value is not None:
                yield {'value':value,'unit':'ft','property_path':'native_text','role':None}
    for match in _SCALAR.finditer(text):
        unit = re.sub(r'[.\s]', '', match.group(2).lower())
        if unit in {'metres', 'meters'}:
            unit = 'm'
        spec = unit_spec(unit)
        value = printed_number(match.group(1), unit)
        if spec and spec[0] == operation and value is not None:
            yield {'value': value, 'unit': unit,
                   'property_path': 'native_text', 'role': None}


def user_declared_dimension(assertion, question, operation):
    """A declared drawing unit can qualify a bare length, never verify its OCR.

    Output preferences such as 'answer in mm' do not declare source units.
    Multiple/conflicting declarations and quotes with other explicit lengths
    require source review instead of guessing a convention.
    """
    if operation != 'length':
        return False
    declarations = re.findall(
        r'\bdimensions?\s+(?:(?:on|in)\s+(?:this|the)\s+(?:drawing|plan)\s+)?'
        r'(?:are|is|shown\s+in|in)\s+(?:in\s+)?'
        r'(millimetres?|millimeters?|centimetres?|centimeters?|metres?|meters?|mm|cm|m|inches|feet)\b',
        question, re.I)
    specs = {unit_spec(unit) for unit in declarations}
    if len(specs) != 1 or None in specs:
        return False
    quote = str(assertion.get('quoted_text') or '')
    if not quote or list(_text_candidates(quote, 'length')):
        return False
    source_unit = declarations[0]
    for match in re.finditer(r'(?<![\w.,/])' + _NUMBER + r'(?![\w.,/])', quote):
        value = printed_number(match.group(), source_unit)
        converted = convert_quantity(value, source_unit, assertion.get('unit'))
        if converted is not None and finite_number(assertion.get('value')) and math.isclose(
                converted, assertion['value'], rel_tol=1e-8, abs_tol=1e-8):
            return True
    return False


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


def ground_visual_evidence(candidate, document, operation, question=''):
    """Check image assertions against native text in the actual cited region.

An image with no native text stays a provisional visual reading. If native text
is present, a mismatching quote/value cannot be labelled source-supported.
"""
    grounded = {**candidate, 'evidence_kind': 'visual', 'source_verified': False}
    page = next((p for p in document.get('pages', []) if p.get('page') == candidate.get('page')), {})
    words = page.get('words') or []
    box = candidate.get('bbox')
    quote = str(candidate.get('quoted_text') or '').strip()
    grounded['verification'] = {'identity': False, 'quote': None, 'quantity': None,
                                'property_path': None, 'semantic_selection_verified': False}
    if not words or not box or len(box) != 4:
        return grounded, []
    def inside(word):
        b = word.get('bbox') or []
        return (len(b) == 4 and all(type(v) in (int, float) and math.isfinite(v) for v in b)
                and b[0] >= box[0] - .002 and b[1] >= box[1] - .002
                and b[2] <= box[2] + .002 and b[3] <= box[3] + .002)
    local_text = ' '.join(str(w.get('text') or '') for w in words if inside(w))
    quote_ok = bool(quote) and normalized(quote) in normalized(local_text)
    grounded['verification']['quote'] = quote_ok
    if not quote_ok:
        grounded['quoted_text'] = ''
        if operation in {'area', 'length', 'volume'}:
            grounded['value'] = None
        return grounded, ['A visual excerpt could not be matched to native text inside its cited region.']
    if operation not in {'area', 'length', 'volume'}:
        grounded['source_verified'] = True
        return grounded, []
    # Explicit net/gross wording must itself appear in the cited text.
    role = _requested_role(question, operation)
    if role and role not in normalized(quote):
        grounded['value'] = None
        grounded['verification']['quantity'] = False
        return grounded, ['The cited text does not establish the requested net/gross quantity role.']
    checked, warnings = ground_native_evidence({'id': 'native-region-text', 'text': local_text},
                                               candidate, operation, question='')
    grounded['value'], grounded['unit'] = checked['value'], checked['unit']
    grounded['verification']['quantity'] = checked['verification']['quantity']
    grounded['verification']['property_path'] = 'native_text_in_cited_region'
    grounded['source_verified'] = checked['source_verified']
    return grounded, warnings

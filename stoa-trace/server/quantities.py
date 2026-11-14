"""Strict schedule quantities, including decimal commas and fractional imperial lengths."""
from __future__ import annotations

import math
import re
from fractions import Fraction

from .verification import convert_quantity, unit_spec


def _decimal(text):
    text = text.replace('\u00a0','').replace('\u202f','').replace(' ','')
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.','').replace(',','.')
        else:
            text = text.replace(',','')
    elif ',' in text:
        if re.fullmatch(r'[+-]?\d{1,3}(?:,\d{3})+',text):
            text = text.replace(',','')
        else:
            text = text.replace(',','.')
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)',text):
        return None
    number = float(text)
    return number if math.isfinite(number) else None


def _fraction(text):
    match = re.fullmatch(r'(?:(\d+)\s+)?(\d+)/(\d+)',text.strip())
    if match:
        whole,a,b = match.groups()
        if int(b)==0 or int(a)>=int(b):
            return None
        return int(whole or 0)+float(Fraction(int(a),int(b)))
    return _decimal(text)


def header_unit(header):
    text = str(header or '').casefold().replace('²','2').replace('³','3')
    for unit,pattern in [('ft2',r'\b(?:sf|sq\.?\s*ft|ft2)\b'),('m2',r'\b(?:sqm|m2)\b'),
                         ('ft3',r'\b(?:cf|ft3)\b'),('m3',r'\bm3\b'),
                         ('mm',r'\bmm\b'),('cm',r'\bcm\b'),('ft',r'\b(?:ft|feet)\b'),
                         ('in',r'\b(?:inches|inch)\b'),('m',r'\b(?:metres|meters|m)\b')]:
        if re.search(pattern,text):
            return unit
    if re.search(r'\b(count|qty|quantity|quantities|number)\b',text):
        return 'count'
    return None


def parse(text, header=''):
    """Return a value and explicit/inherited unit; no number is extracted from prose."""
    s = str(text or '').strip().replace('′',"'").replace('″','"').replace('’',"'").replace('−','-')
    # Feet-and-inches use a separator dash, never a negative inch term.
    feet = re.fullmatch(r"(\d+(?:\.\d+)?)\s*'\s*(?:-\s*)?([\d ./]+)?\s*(?:\x22)?",s)
    inches = re.fullmatch(r'([\d ./]+)\s*\x22',s)
    if feet or inches:
        if feet:
            a,b = feet.groups()
            inch = _fraction((b or '0').strip())
            if inch is None or inch >= 12:
                return None
            value = float(a)*.3048+inch*.0254
        else:
            value = _fraction(inches.group(1))
            if value is None:
                return None
            value *= .0254
        inherited = header_unit(header)
        if inherited and unit_spec(inherited)[0] != 'length':
            return None
        return {'value':value,'unit':'m'}
    match = re.fullmatch(r'([+-]?[\d.,\s]+(?:/\d+)?)\s*(m[²³23]|mm[²³23]?|cm[²³23]?|ft[²³23]?|sq\.?\s*ft|sf|sqm|in|m|count)?',s,re.I)
    if not match:
        return None
    raw,unit = match.groups()
    value = _fraction(raw.strip()) if '/' in raw else _decimal(raw)
    if value is None or value < 0:
        return None
    explicit = (unit or '').casefold().replace('²','2').replace('³','3').replace(' ','').replace('.','')
    explicit = {'sqft':'ft2','sf':'ft2','sqm':'m2'}.get(explicit,explicit)
    inherited = header_unit(header)
    if not explicit and not inherited and re.search(r'\b(width|height|length|depth|thickness|area|volume)\b', str(header), re.I):
        return None
    unit = explicit or inherited or 'count'
    if not unit_spec(unit) or inherited and unit_spec(inherited)[0] != unit_spec(unit)[0]:
        return None
    if unit == 'count' and not float(value).is_integer():
        return None
    return {'value':value,'unit':unit}


def compatible_terms(rows,column,header,output_unit=None):
    values = []
    target = output_unit
    for row in rows:
        if column >= len(row.get('cells',[])):
            return None
        item = parse(row['cells'][column],header)
        if item is None:
            return None
        target = target or item['unit']
        value = convert_quantity(item['value'],item['unit'],target)
        if value is None:
            return None
        values.append(value)
    # An empty sum is zero only when the column defines its dimension.
    target = target or header_unit(header)
    if target is None:
        return None
    return values,target

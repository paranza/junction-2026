"""Token-cost estimates before credits; unknown usage never becomes free inference.

Published rates checked 2026-11-14:
https://aistudio.google.com/docs/pricing#gemini-4-carbon
https://aistudio.google.com/docs/pricing#gemma-4
Carbon's listed promotional rates expire on 2026-12-01. Gemma's hosted free
tier is an estimate of provider token charges, not a promise about an invoice.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import os

_SOURCE = 'https://aistudio.google.com/docs/pricing'
_LISTED = {
    'gemini/gemini-4-carbon': (2.0, .1, 10.0),
    'gemini/gemma-4-31b-it': (0.0, 0.0, 0.0),
    'gemini/gemma-4-26b-a4b-it': (0.0, 0.0, 0.0),
}
_START = datetime(2026, 11, 14, tzinfo=timezone.utc)
_END = datetime(2026, 12, 1, tzinfo=timezone.utc)
TOKEN_FIELDS = ('input_tokens', 'output_tokens', 'cached_input_tokens')


def rates_for(model, at=None):
    """An explicit exact-model override takes precedence over dated list prices."""
    if os.environ.get('STOA_PRICE_MODEL') == model:
        try:
            input_rate = float(os.environ['STOA_INPUT_USD_PER_MILLION'])
            output_rate = float(os.environ['STOA_OUTPUT_USD_PER_MILLION'])
            cached_rate = float(os.environ.get('STOA_CACHED_INPUT_USD_PER_MILLION', input_rate))
            if all(math.isfinite(v) and v >= 0 for v in (input_rate, cached_rate, output_rate)):
                return {'input': input_rate, 'cached_input': cached_rate, 'output': output_rate,
                        'basis': 'configured_rates', 'source': None}
        except (KeyError, TypeError, ValueError):
            pass
        return None  # A broken explicit override must not silently select another price.
    at = at or datetime.now(timezone.utc)
    if isinstance(at, (int, float)):
        at = datetime.fromtimestamp(at, timezone.utc)
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    if model not in _LISTED or not _START <= at < _END:
        return None
    input_rate, cached_rate, output_rate = _LISTED[model]
    return {'input': input_rate, 'cached_input': cached_rate, 'output': output_rate,
            'basis': 'published_rates', 'source': _SOURCE, 'verified_on': '2026-11-14',
            'valid_until': '2026-12-01T00:00:00Z'}


def normalize_usage(usage):
    if not isinstance(usage, dict):
        return None
    details = usage.get('input_tokens_details') or {}
    if not isinstance(details, dict):
        return None
    values = {'input_tokens': usage.get('input_tokens'), 'output_tokens': usage.get('output_tokens'),
              'cached_input_tokens': details.get('cached_tokens', usage.get('cached_input_tokens', 0))}
    if any(type(v) is not int or v < 0 for v in values.values()):
        return None
    if values['cached_input_tokens'] > values['input_tokens']:
        return None
    return values


def summarize_calls(calls, *, cache_hit=False):
    """Each item describes one reserved attempt, with None for unreported usage."""
    total = {'model_calls': len(calls), **dict.fromkeys(TOKEN_FIELDS, 0), 'models': [],
             'cost_known_usd': 0.0, 'unknown_usage_calls': 0, 'cost_unavailable_calls': 0,
             'cache_hit': bool(cache_hit), 'pricing_note': 'Estimated provider token cost before credits; hosting and storage excluded.'}
    by_model = {}
    bases = set()
    for call in calls:
        model = str(call.get('model') or 'unknown')
        if model not in total['models']:
            total['models'].append(model)
        group = by_model.setdefault(model, {'model': model, 'model_calls': 0,
                                          **dict.fromkeys(TOKEN_FIELDS, 0), 'cost_known_usd': 0.0,
                                          'unknown_usage_calls': 0, 'cost_unavailable_calls': 0})
        group['model_calls'] += 1
        usage = normalize_usage(call.get('usage'))
        if usage is None:
            total['unknown_usage_calls'] += 1
            group['unknown_usage_calls'] += 1
        else:
            for key in TOKEN_FIELDS:
                total[key] += usage[key]
                group[key] += usage[key]
        rates = rates_for(model, call.get('created')) if usage is not None else None
        if rates is None:
            total['cost_unavailable_calls'] += 1
            group['cost_unavailable_calls'] += 1
            continue
        value = ((usage['input_tokens'] - usage['cached_input_tokens']) * rates['input']
                 + usage['cached_input_tokens'] * rates['cached_input']
                 + usage['output_tokens'] * rates['output']) / 1_000_000
        total['cost_known_usd'] += value
        group['cost_known_usd'] += value
        group['pricing'] = rates
        bases.add(rates['basis'])
    for group in by_model.values():
        group['cost_known_usd'] = round(group['cost_known_usd'], 8)
        group['cost_estimate_usd'] = None if group['cost_unavailable_calls'] else group['cost_known_usd']
    total['model_usage'] = list(by_model.values())
    total['cost_known_usd'] = round(total['cost_known_usd'], 8)
    total['cost_estimate_usd'] = None if total['cost_unavailable_calls'] else total['cost_known_usd']
    total['cost_basis'] = ('native' if not calls else 'unconfigured' if not bases
                           else next(iter(bases)) if len(bases) == 1 else 'model_rates')
    if total['unknown_usage_calls']:
        total['usage_incomplete'] = True
    return total

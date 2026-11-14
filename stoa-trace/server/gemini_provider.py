"""Stateless Gemini Interactions transport for Trace's shared evidence interface.

REST shape checked against Google's current documentation on 2026-11-14:
https://aistudio.google.com/api-reference/interactions-api/create-interaction
https://aistudio.google.com/docs/structured-output
https://aistudio.google.com/docs/image-understanding
https://aistudio.google.com/docs/media-resolution
https://aistudio.google.com/docs/thinking#token-limits
https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api

Budget reservation and usage accounting belong to llm._request, once per attempt.
This transport never retries or accepts a configurable destination for secrets.
"""
from __future__ import annotations

import base64
import binascii
import os
import re

import httpx

ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/interactions'
API_REVISION = '2026-05-20'
REVISION = 'gemini-interactions-v3'
GEMMA_REVISION = 'gemma-interactions-v2'
DEFAULT_MODEL = 'gemini-4-argon'
GEMMA_MODELS = frozenset({'gemma-4-31b-it', 'gemma-4-26b-a4b-it'})
IMAGE_RESOLUTIONS = frozenset({'low', 'medium', 'high', 'ultra_high'})
_IMAGE = re.compile(r'data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=]+)\Z')


class ProviderError(Exception):
    """Public-safe provider error without request data or credential contents."""


def image_resolution():
    resolution = os.environ.get('STOA_GEMINI_IMAGE_RESOLUTION', 'ultra_high').strip().lower()
    if resolution not in IMAGE_RESOLUTIONS:
        raise ProviderError('STOA_GEMINI_IMAGE_RESOLUTION must be low, medium, high or ultra_high.')
    return resolution


def _integer_setting(name, default, minimum, maximum):
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip()
    if (len(value) > len(str(maximum)) or not re.fullmatch(r'[0-9]+', value)
            or not minimum <= int(value) <= maximum):
        raise ProviderError(f'{name} must be an integer from {minimum} to {maximum}.')
    return int(value)


def timeout_seconds():
    return _integer_setting('STOA_GEMINI_TIMEOUT_SECONDS', 240, 60, 600)


def visual_thinking_level(model=None):
    gemma = model in GEMMA_MODELS
    name = 'STOA_GEMMA_THINKING_LEVEL' if gemma else 'STOA_GEMINI_THINKING_LEVEL'
    choices = {'minimal', 'high'} if gemma else {'low', 'medium', 'high'}
    level = os.environ.get(name, 'high').strip().lower()
    if level not in choices:
        raise ProviderError(name + ' must be ' + ', '.join(sorted(choices)) + '.')
    return level


def visual_output_limit():
    # The API cap includes reasoning tokens. It is a hard cutoff rather than a
    # reasoning budget. Leave unset to preserve each caller's existing limit.
    return _integer_setting('STOA_GEMINI_MAX_OUTPUT_TOKENS', None, 1000, 32768)


def config_signature(model=None):
    """Keep visual caches separate without making invalid vision config break native tools."""
    revision = GEMMA_REVISION if model in GEMMA_MODELS else REVISION
    values = []
    for name, reader in (('image_resolution', image_resolution),
                         ('thinking_level', lambda: visual_thinking_level(model)),
                         ('max_output_tokens', visual_output_limit),
                         ('timeout_seconds', timeout_seconds)):
        try:
            value = reader()
        except ProviderError:
            value = 'invalid'
        values.append(f'{name}={"caller" if value is None else value}')
    return f'{revision}:{API_REVISION}:' + ':'.join(values)


def prepare_request(content, system, schema, max_tokens, model):
    # Validate before shared llm._request reserves a potentially billable attempt.
    resolution = image_resolution()
    visual_thinking = visual_thinking_level(model)
    output_override = visual_output_limit()
    timeout_seconds()
    if str(model).startswith('gemma-') and model not in GEMMA_MODELS:
        raise ProviderError('The configured Gemma model is not supported by this adapter.')
    inputs = []
    for part in content:
        if part.get('type') == 'input_text' and isinstance(part.get('text'), str):
            inputs.append({'type': 'text', 'text': part['text']})
        elif part.get('type') == 'input_image':
            match = _IMAGE.fullmatch(str(part.get('image_url', '')))
            if not match:
                raise ProviderError('Gemini requires a supported inline drawing image.')
            try:
                decoded = base64.b64decode(match[2], validate=True)
            except (ValueError, binascii.Error):
                raise ProviderError('The drawing image could not be encoded for Gemini.') from None
            if not decoded:
                raise ProviderError('The drawing image is empty.')
            inputs.append({'type': 'image', 'mime_type': match[1], 'data': match[2],
                           'resolution': resolution})
        else:
            raise ProviderError('This drawing input is not supported by Gemini.')
    bounded_thinking = 'minimal' if model in GEMMA_MODELS else 'low'
    thinking = bounded_thinking if max_tokens < 1000 else visual_thinking
    output_limit = max_tokens if max_tokens < 1000 or output_override is None else output_override
    return {'model': model, 'input': inputs, 'system_instruction': system, 'store': False,
            'response_format': {'type': 'text', 'mime_type': 'application/json', 'schema': schema},
            'generation_config': {'max_output_tokens': output_limit,
                                  'thinking_level': thinking,
                                  'thinking_summaries': 'none'}}


def _tokens(value):
    # Invalid/missing usage remains unknown, never an invented zero-cost response.
    return value if type(value) is int and value >= 0 else None


def normalize_response(body):
    """Map current Interactions steps/usage to the existing Responses-like shape."""
    if not isinstance(body, dict):
        raise ProviderError('Gemini returned an unreadable response.')
    raw_usage = body.get('usage')
    usage = None
    if isinstance(raw_usage, dict):
        input_tokens = _tokens(raw_usage.get('total_input_tokens'))
        output_tokens = _tokens(raw_usage.get('total_output_tokens'))
        thought_tokens = _tokens(raw_usage.get('total_thought_tokens'))
        cached_tokens = _tokens(raw_usage.get('total_cached_tokens'))
        if None not in (input_tokens, output_tokens, thought_tokens, cached_tokens) and cached_tokens <= input_tokens:
            usage = {'input_tokens': input_tokens, 'output_tokens': output_tokens + thought_tokens,
                     'input_tokens_details': {'cached_tokens': cached_tokens},
                     'output_tokens_details': {'reasoning_tokens': thought_tokens}}
    output = []
    steps = body.get('steps')
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict) or step.get('type') != 'model_output':
                continue
            parts = step.get('content')
            if isinstance(parts, list):
                output.append({'content': [{'type': 'output_text', 'text': part['text']}
                                          for part in parts if isinstance(part, dict)
                                          and part.get('type') == 'text' and isinstance(part.get('text'), str)]})
    return {'status': body.get('status'), 'usage': usage, 'output': output}


def request(payload, key):
    timeout = timeout_seconds()
    try:
        with httpx.Client(timeout=httpx.Timeout(timeout, connect=15), follow_redirects=False) as client:
            response = client.post(ENDPOINT, headers={'x-goog-api-key': key, 'Api-Revision': API_REVISION}, json=payload)
    except httpx.HTTPError:
        raise ProviderError('Gemini could not be reached. Please retry or use native tools.') from None
    if response.status_code != 200:
        reason = {400: 'Gemini rejected the drawing request or model configuration.',
                  401: 'Gemini authentication failed.',
                  403: 'The Gemini key or model is not enabled for this project.',
                  404: 'The configured Gemini model or API is unavailable.',
                  429: 'Gemini reached an account rate or credit limit.'}.get(
                      response.status_code, 'Gemini could not complete this request.')
        raise ProviderError(reason)
    try:
        body = response.json()
    except ValueError:
        raise ProviderError('Gemini returned an unreadable response.') from None
    return normalize_response(body)

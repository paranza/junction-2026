#!/usr/bin/env python3
"""Check the configured Gemini model against Google's catalog without inference.

Loads a private env file without shell evaluation. Exported settings take
precedence. Output contains availability metadata only, never credential values.
Catalog visibility does not establish inference access, available credit or
performance on drawings. No runtime database or model-attempt ledger is touched.

Official protocol checked on 2026-11-14:
https://aistudio.google.com/api-reference/models/list-models
https://aistudio.google.com/docs/api-key
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode

from check_connections import (DEFAULT_ENV, HealthError, create_ssl_context,
                               error_result, request_json)

DEFAULT_GEMINI_ENV = DEFAULT_ENV.with_name('gemini.env')
DEFAULT_MODEL = 'gemini-4-argon'
MODELS_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models'
CONFIG_KEYS = {'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'STOA_MODEL'}


def load_private_config(path):
    config = {}
    try:
        if path.exists():
            if path.stat().st_size > 128 * 1024:
                raise HealthError('env_file_too_large')
            for line in path.read_text(encoding='utf-8-sig').splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('export '):
                    line = line[7:].lstrip()
                name, separator, value = line.partition('=')
                name, value = name.strip(), value.strip()
                if not separator or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
                    raise HealthError('unsupported_env_file_syntax')
                if value.startswith(('"', "'")):
                    if len(value) < 2 or value[-1] != value[0]:
                        raise HealthError('unsupported_env_file_syntax')
                    value = value[1:-1]
                if name in CONFIG_KEYS:
                    config[name] = value
    except (OSError, UnicodeError):
        raise HealthError('env_file_unreadable') from None
    config.update({name: os.environ[name] for name in CONFIG_KEYS if name in os.environ})
    return config


def check_catalog(config, *, model=None, timeout=15.0, ssl_context=None):
    selected = model or config.get('STOA_MODEL') or DEFAULT_MODEL
    if selected.startswith('models/'):
        selected = selected[7:]
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', selected):
        raise HealthError('invalid_model_id')
    key = config.get('GEMINI_API_KEY', config.get('GOOGLE_API_KEY', ''))
    if not key or not key.strip():
        return {'status': 'missing_credentials', 'missing': ['GEMINI_API_KEY'],
                'inference': {'status': 'not_requested'}}
    if any(char in key for char in '\r\n'):
        raise HealthError('invalid_credential_format')
    selected_resource = 'models/' + selected
    token = None
    seen_tokens = set()
    count = 0
    match = None
    for _ in range(20):
        query = {'pageSize': 1000}
        if token:
            query['pageToken'] = token
        body = request_json(MODELS_ENDPOINT + '?' + urlencode(query),
                            headers={'x-goog-api-key': key}, timeout=timeout,
                            retries=0, ssl_context=ssl_context)
        if not isinstance(body, dict) or not isinstance(body.get('models'), list):
            raise HealthError('unexpected_models_response')
        for item in body['models']:
            if not isinstance(item, dict):
                raise HealthError('unexpected_models_response')
            count += 1
            if item.get('name') == selected_resource or item.get('baseModelId') == selected:
                match = item
        token = body.get('nextPageToken')
        if not token:
            break
        if not isinstance(token, str) or len(token) > 8192 or token in seen_tokens:
            raise HealthError('invalid_catalog_pagination')
        seen_tokens.add(token)
    else:
        raise HealthError('catalog_pagination_limit')
    result = {'status': 'ok', 'provider': 'gemini', 'model': selected,
              'models_count': count, 'selected_model_listed': match is not None,
              'inference': {'status': 'not_requested'}}
    if match is not None:
        result['model_metadata'] = {name: match[name] for name in ('inputTokenLimit', 'outputTokenLimit', 'thinking')
                                    if name in match and isinstance(match[name], (int, bool))}
        methods = match.get('supportedGenerationMethods')
        if isinstance(methods, list):
            result['model_metadata']['supportedGenerationMethods'] = [value for value in methods
                if isinstance(value, str) and re.fullmatch(r'[A-Za-z]{1,64}', value)]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=DEFAULT_GEMINI_ENV)
    parser.add_argument('--model', help='Check this model instead of STOA_MODEL')
    parser.add_argument('--timeout', type=float, default=15.0)
    args = parser.parse_args(argv)
    try:
        config = load_private_config(args.env_file.expanduser())
        result = check_catalog(config, model=args.model, timeout=args.timeout,
                               ssl_context=create_ssl_context())
    except HealthError as error:
        result = error_result(error)
    except Exception:
        # Never render arbitrary library errors which can contain request data.
        result = {'status': 'error', 'error': 'catalog_check_failed'}
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get('status') == 'ok' and result.get('selected_model_listed') else 1


if __name__ == '__main__':
    raise SystemExit(main())

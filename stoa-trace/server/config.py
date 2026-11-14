"""Load private provider settings without overriding an exported environment."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

PRIVATE_ROOT = Path.home() / '.config/stoa-junction-2026'
RUNTIME_KEYS = frozenset({
    'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'STOA_PROVIDER', 'STOA_MODEL',
    'STOA_MAX_MODEL_CALLS', 'STOA_INPUT_USD_PER_MILLION',
    'STOA_CACHED_INPUT_USD_PER_MILLION', 'STOA_OUTPUT_USD_PER_MILLION',
    'STOA_SMALL_IMAGE_CROPS',
})


def active_gemini_settings(values, selected_provider=None):
    """An empty preparation file must never switch a working provider."""
    if selected_provider is not None and selected_provider.strip().lower() != 'gemini':
        return {}
    key = values.get('GEMINI_API_KEY') or values.get('GOOGLE_API_KEY')
    if not key or str(values.get('STOA_PROVIDER', 'gemini')).strip().lower() != 'gemini':
        return {}
    settings = {name: str(value) for name, value in values.items()
                if name in RUNTIME_KEYS and value is not None}
    settings['STOA_PROVIDER'] = 'gemini'
    settings.setdefault('STOA_MODEL', 'gemini-4-carbon')
    return settings


def load_environment(project_root: Path, *, private_env: Path | None = PRIVATE_ROOT / 'secrets.env',
                     gemini_env: Path | None = PRIVATE_ROOT / 'gemini.env',
                     env_file: Path | None = None):
    if gemini_env is not None:
        settings = active_gemini_settings(dotenv_values(gemini_env), os.environ.get('STOA_PROVIDER'))
        for name, value in settings.items():
            os.environ.setdefault(name, value)
    if private_env is not None:
        load_dotenv(private_env, override=False)
    load_dotenv(env_file if env_file is not None else project_root / '.env', override=False)

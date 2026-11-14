#!/usr/bin/env python3
"""Start Metria using .env configuration before Uvicorn selects host and port.

Run ops/refresh_local.py first on a fresh checkout or after dependency/UI updates.
This helper never provisions services or makes model requests.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_ENV = Path.home() / '.config' / 'stoa-junction-2026' / 'secrets.env'


def launch_settings(project_root: Path = ROOT, env_file: Path | None = None,
                    private_env: Path | None = PRIVATE_ENV) -> dict:
    sys.path.insert(0, str(ROOT))
    from server.config import load_environment
    # Use the sidecar only for the ordinary private configuration location.
    kwargs = {} if private_env == PRIVATE_ENV else {'gemini_env': None}
    load_environment(project_root, private_env=private_env, env_file=env_file, **kwargs)
    host = os.environ.get('STOA_HOST', '127.0.0.1').strip()
    if not host or any(char.isspace() for char in host):
        raise ValueError('STOA_HOST must be a hostname or IP address without spaces.')
    try:
        port = int(os.environ.get('STOA_PORT', '8787'))
    except ValueError:
        raise ValueError('STOA_PORT must be an integer from 1 to 65535.') from None
    if not 1 <= port <= 65535:
        raise ValueError('STOA_PORT must be an integer from 1 to 65535.')
    return {'host': host, 'port': port}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, help='Use an alternative project .env file')
    parser.add_argument('--print-config', action='store_true', help='Print host/port only; do not start a server')
    args = parser.parse_args(argv)
    try:
        settings = launch_settings(env_file=args.env_file)
    except ImportError:
        print('Dependencies are missing. Run this Python interpreter with ops/refresh_local.py first.', file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.print_config:
        print(json.dumps(settings, sort_keys=True))
        return 0
    # Imports work regardless of the caller's working directory or OS layout.
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    import uvicorn
    uvicorn.run('server.app:app', host=settings['host'], port=settings['port'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

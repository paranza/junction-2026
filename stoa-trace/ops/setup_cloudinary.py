#!/usr/bin/env python3
"""Create the signed, authenticated evidence-page preset once.

Read credentials from private configuration. No key, signed URL or arbitrary
provider error is printed. This command uploads no source documents.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def setup():
    import cloudinary.api
    from cloudinary.exceptions import NotFound
    from server.cloudinary_media import PRESET, MediaError, _sdk, credentials

    cred = credentials()
    _sdk()  # Disable the pinned SDK's automatic retries and redirects.
    options = {**cred.options(), 'timeout': 30}
    wanted = {'type': 'authenticated', 'allowed_formats': ['png'],
              'overwrite': False, 'asset_folder': 'trace-evidence'}
    try:
        existing = cloudinary.api.upload_preset(PRESET, **options)
    except NotFound:
        cloudinary.api.create_upload_preset(name=PRESET, unsigned=False, **wanted, **options)
        return {'status': 'created', 'preset': PRESET, 'authenticated': True, 'unsigned': False}
    actual = existing.get('settings') or {}
    if existing.get('unsigned') is not False or any(actual.get(key) != value for key, value in wanted.items()):
        raise MediaError('An existing preset differs from the required protected-page settings.')
    return {'status': 'already_configured', 'preset': PRESET, 'authenticated': True, 'unsigned': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, help='Private Cloudinary settings file; values are never printed')
    args = parser.parse_args(argv)
    from server.config import load_environment
    load_environment(ROOT, cloudinary_env=args.env_file if args.env_file else Path.home() / '.config/stoa-junction-2026/cloudinary.env')
    try:
        print(json.dumps(setup(), sort_keys=True))
        return 0
    except Exception as exc:
        # SDK exception messages may include endpoint URLs or source details.
        print(json.dumps({'status': 'error', 'code': type(exc).__name__}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Install pinned Python dependencies and rebuild the frontend after updates.

Use the project's virtual-environment Python on macOS, Linux or Windows. This
helper does not create cloud resources, load API credentials or start servers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def refresh_commands(project_root: Path = ROOT) -> list[list[str]]:
    npm = shutil.which('npm')
    node = shutil.which('node')
    if not npm or not node:
        raise RuntimeError('Node.js 22 or newer and npm are required on PATH.')
    version = subprocess.check_output([node, '--version'], text=True).strip()
    try:
        major = int(version.lstrip('v').split('.')[0])
    except ValueError:
        raise RuntimeError('Could not determine the installed Node.js version.') from None
    if major < 22:
        raise RuntimeError('Node.js 22 or newer is required.')
    return [
        [sys.executable, '-m', 'pip', 'install', '-r', str(project_root / 'requirements.txt')],
        [npm, '--prefix', str(project_root / 'frontend'), 'ci'],
        [npm, '--prefix', str(project_root / 'frontend'), 'run', 'build'],
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Print planned commands without installing or building')
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        print('Python 3.11 or newer is required.', file=sys.stderr)
        return 2
    if sys.prefix == sys.base_prefix and not args.dry_run:
        print('Run this helper using the project virtual-environment Python.', file=sys.stderr)
        return 2
    try:
        commands = refresh_commands()
        if args.dry_run:
            print(json.dumps({'commands': commands}, indent=2))
            return 0
        for command in commands:
            subprocess.run(command, cwd=ROOT, check=True)
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        # No credential files or environment values are loaded by this helper.
        print(str(exc), file=sys.stderr)
        return 1
    print('Dependencies and frontend refreshed. Run this Python with ops/start_local.py.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

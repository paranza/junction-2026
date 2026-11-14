#!/usr/bin/env python3
"""Freeze a prospective drawing-group reservation for evaluation only.

This cannot undo prior dataset exposure. Selection uses group/source identities,
never answer values. Gold-bearing development/reserved manifests stay local;
the public membership record contains no questions or expected answers.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

from benchmark import canonical_hash, load_manifest
from grouped_manifest import drawing_group


HERE = Path(__file__).resolve().parent
EXPOSURE_NOTE = (
    "The preview was already used for full baseline evaluation and team EDA/tuning. "
    "This is a prospective quarantine from the freeze time, not an untouched test set."
)


def split_groups(cases, fraction, seed, excluded_groups=()):
    if not 0 < fraction < 1:
        raise ValueError('fraction must be strictly between zero and one')
    groups = defaultdict(list)
    for case in cases:
        source, group = drawing_group(case['path'])
        if case['group'] != group or case['source'] != source:
            raise ValueError('Case group/source does not match the shared grouping rule')
        groups[group].append(case)
    if len(groups) < 2:
        raise ValueError('At least two drawing groups are required')
    excluded = set(excluded_groups)
    eligible = sorted(set(groups) - excluded)
    target = max(1, min(len(groups) - 1, int(math.floor(len(groups) * fraction + .5))))
    if len(eligible) < target:
        raise ValueError('Not enough eligible groups for the requested reservation')
    by_source = defaultdict(list)
    for group in eligible:
        by_source[groups[group][0]['source']].append(group)
    # Largest-remainder allocation over eligible groups, independent of labels.
    ideals = {source: target * len(names) / len(eligible) for source, names in by_source.items()}
    allocation = {source: math.floor(value) for source, value in ideals.items()}
    order = sorted(ideals, key=lambda source: (-(ideals[source] - allocation[source]), source))
    for source in order[:target - sum(allocation.values())]:
        allocation[source] += 1
    reserved = set()
    for source, names in sorted(by_source.items()):
        ranked = sorted(names, key=lambda name: (hashlib.sha256((seed + '\n' + name).encode()).hexdigest(), name))
        reserved.update(ranked[:allocation[source]])
    development = [case for case in cases if case['group'] not in reserved]
    held = [case for case in cases if case['group'] in reserved]
    return development, held, groups, excluded & set(groups), allocation


def partition_manifest(original, cases, name, reserved_groups, seed, frozen_at):
    return {
        **original,
        'name': name,
        'frozen_at': frozen_at,
        'evaluation_only': True,
        'cases': cases,
        'cases_sha256': canonical_hash(cases),
        'selection': {
            **original.get('selection', {}),
            'case_count': len(cases),
            'english_only': False,
            'reservation_seed': seed,
            'reserved_groups': sorted(reserved_groups),
            'procedure': 'Prospective group reservation; preserve all questions/translations in each selected group.',
        },
        'evaluation_limits': list(original.get('evaluation_limits', [])) + [EXPOSURE_NOTE],
    }


def restore_split(original, record):
    if record.get('schema_version') != 1:
        raise ValueError('Unsupported membership record version')
    if original['cases_sha256'] != record['full_cases_sha256']:
        raise ValueError('Full manifest differs from the frozen membership input')
    if original['dataset']['questions_sha256'] != record['source_questions_sha256']:
        raise ValueError('Question source hash differs from the frozen membership input')
    reserved = set(record['reserved_group_membership'])
    if canonical_hash(sorted(reserved)) != record['membership_sha256']:
        raise ValueError('Membership hash does not match')
    if not reserved <= {case['group'] for case in original['cases']}:
        raise ValueError('Membership contains groups outside the full manifest')
    development = [case for case in original['cases'] if case['group'] not in reserved]
    held = [case for case in original['cases'] if case['group'] in reserved]
    if canonical_hash(development) != record['development_cases_sha256'] or canonical_hash(held) != record['reserved_cases_sha256']:
        raise ValueError('Restored split differs from the frozen split hashes')
    return development, held, reserved


def make_record(original, development, held, groups, excluded, allocation, *, seed, fraction, frozen_at, commit):
    reserved = {case['group'] for case in held}
    sources = sorted({case['source'] for case in original['cases']})
    return {
        'schema_version': 1,
        'name': 'Saturday prospective preview reservation',
        'frozen_at': frozen_at,
        'code_commit': commit,
        'evaluation_only': True,
        'exposure_note': EXPOSURE_NOTE,
        'release_policy': 'Do not score or debug reserved cases before Sunday 15 November 2026. Use only development cases for interim changes.',
        'seed': seed,
        'requested_group_fraction': fraction,
        'actual_group_fraction': len(reserved) / len(groups),
        'source_questions_sha256': original['dataset']['questions_sha256'],
        'full_cases_sha256': original['cases_sha256'],
        'development_cases_sha256': canonical_hash(development),
        'reserved_cases_sha256': canonical_hash(held),
        'counts': {
            'all_groups': len(groups), 'all_questions': len(original['cases']),
            'eligible_groups': len(groups) - len(excluded),
            'known_diagnostic_groups_kept_in_development': len(excluded),
            'reserved_groups': len(reserved), 'reserved_questions': len(held),
            'development_groups': len(groups) - len(reserved), 'development_questions': len(development),
        },
        'selection': 'Largest-remainder source allocation over eligible groups, then ascending SHA256(seed + newline + group). No answer values used.',
        'grouping_rule': 'Shared ops/grouped_manifest.py drawing_group: Swiss building; IFC model and matching plan exports; Opening Design project; other matching file stems.',
        'grouping_limits': 'Cross-source semantic duplicates or differently named exports may remain; this rule is not a dataset-wide duplicate audit.',
        'by_source': {
            source: {
                'all_groups': sum(cases[0]['source'] == source for cases in groups.values()),
                'reserved_groups': allocation.get(source, 0),
                'reserved_questions': sum(case['source'] == source for case in held),
                'development_questions': sum(case['source'] == source for case in development),
            } for source in sources
        },
        'reserved_group_membership': sorted(reserved),
        'known_diagnostic_groups_kept_in_development': sorted(excluded),
        'membership_sha256': canonical_hash(sorted(reserved)),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path, help='Local full evaluation manifest; contains gold labels')
    parser.add_argument('--dataset-root', help='Optional local source-label validation directory')
    parser.add_argument('--output-dir', required=True, type=Path, help='Ignored/local directory for gold-bearing split manifests')
    membership = parser.add_mutually_exclusive_group(required=True)
    membership.add_argument('--membership-output', type=Path, help='Create a public no-gold membership record')
    membership.add_argument('--membership-input', type=Path, help='Restore local manifests from an existing public membership record; never replace it')
    parser.add_argument('--exclude-manifest', action='append', default=[], type=Path)
    parser.add_argument('--seed', default='trace-saturday-reservation-20261114-v1')
    parser.add_argument('--fraction', type=float, default=.15)
    args = parser.parse_args(argv)
    outputs = [args.output_dir / 'development.json', args.output_dir / 'reserved.json']
    if args.membership_output:
        outputs.append(args.membership_output)
    if len({path.resolve() for path in outputs}) != len(outputs):
        parser.error('Output paths must be distinct')
    if any(path.exists() for path in outputs):
        parser.error('Refusing to replace a frozen split or membership record')
    try:
        original, _ = load_manifest(args.manifest, args.dataset_root)
        if args.membership_input:
            record = json.loads(args.membership_input.read_text())
            development, held, reserved = restore_split(original, record)
        else:
            exclusions = args.exclude_manifest or [HERE / 'benchmark-config.json', HERE / 'evaluation-grouped-100.json']
            excluded = {case['group'] for path in exclusions for case in json.loads(path.read_text())['cases']}
            development, held, groups, excluded, allocation = split_groups(original['cases'], args.fraction, args.seed, excluded)
            reserved = {case['group'] for case in held}
            frozen_at = datetime.now(timezone.utc).isoformat()
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HERE, text=True).strip()
            record = make_record(original, development, held, groups, excluded, allocation,
                                 seed=args.seed, fraction=args.fraction, frozen_at=frozen_at, commit=commit)
        values = [partition_manifest(original, development, 'Trace development questions', reserved, record['seed'], record['frozen_at']),
                  partition_manifest(original, held, 'Trace reserved questions; no scoring before Sunday', reserved, record['seed'], record['frozen_at'])]
        if args.membership_output:
            values.append(record)
        for path, value in zip(outputs, values):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8') as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write('\n')
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as exc:
        parser.exit(2, f'Freeze error: {exc}\n')
    print(json.dumps({'membership': str(args.membership_input or args.membership_output), **record['counts'], 'membership_sha256': record['membership_sha256']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Freeze an evaluation-only sample disjoint from diagnostic drawing groups.

Answers remain in this evaluator's manifests. Never import this module from
application code or use its output in prompts, extraction or retrieval.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from benchmark import canonical_hash, ENGLISH_PREFIX


HERE = Path(__file__).resolve().parent


def drawing_group(path):
    parts = Path(path).parts
    source = parts[1] if len(parts) > 2 and parts[0] == 'data' else 'unknown'
    stem = Path(path).stem
    if source == 'swiss_dwellings':
        match = re.match(r'(site\d+_bldg\d+)', stem)
        name = match.group(1) if match else stem
    elif source in {'ifc_models', 'ifc_bench'}:
        name = stem.split('_plan-', 1)[0]
    elif source == 'opening_design':
        name = parts[2] if len(parts) > 3 else stem
    else:
        name = stem
    return source, source + ':' + name


def language_hint(question):
    """A selection heuristic, not a language-recognition quality claim."""
    if ENGLISH_PREFIX.match(question):
        return 'en'
    patterns = {'de': r'^(Wie|Was|Welche|Welcher|Welches|Berechnen|Geben|Auf|Im)\b',
                'fr': r'^(Combien|Quelle|Quel|Quels|Quelles|Calculez|Dans|Sur)\b',
                'it': r'^(Quanti|Quante|Qual|Quale|Quali|Calcola|Calcolare|Nel|Nella)\b',
                'fi': r'^(Kuinka|Montako|Mikä|Mitkä|Laske|Paljonko)\b',
                'et': r'^(Mitu|Mis|Milline|Millised|Kui|Leia)\b',
                'sv': r'^(Hur|Vad|Vilken|Vilka|Beräkna)\b'}
    return next((language for language, pattern in patterns.items() if re.search(pattern, question, re.I)), 'unknown')


def select_cases(rows, excluded_groups, count, seed, max_per_group=3, languages=None):
    strata = defaultdict(list)
    for source_line, row in enumerate(rows, 1):
        source, group = drawing_group(row['path'])
        if group in excluded_groups:
            continue
        language = language_hint(row['question'])
        if languages and language not in languages:
            continue
        if row.get('type') not in {'count', 'area', 'length', 'volume', 'text'}:
            continue
        rank = hashlib.sha256((seed + '\n' + row['path'] + '\n' + row['question']).encode()).hexdigest()
        case = {'id': 'grouped-' + rank[:16], 'source_line': source_line,
                'path': row['path'], 'question': row['question'], 'expected': row['answer'],
                'unit': row.get('unit'), 'type': row['type'], 'source': source, 'group': group,
                'language_hint': language, 'suites': ['full'] + (['raster'] if source == 'cubicasa5k' else [])}
        strata[(source, row['type'], language)].append((rank, case))
    for bucket in strata.values():
        bucket.sort(key=lambda pair: pair[0], reverse=True)
    selected, group_counts, keys = [], Counter(), set()
    buckets = sorted(strata)
    while buckets and len(selected) < count:
        next_buckets = []
        for key in buckets:
            bucket = strata[key]
            while bucket:
                _, case = bucket.pop()
                identity = (case['path'], case['question'])
                if group_counts[case['group']] < max_per_group and identity not in keys:
                    selected.append(case)
                    group_counts[case['group']] += 1
                    keys.add(identity)
                    break
            if bucket:
                next_buckets.append(key)
            if len(selected) >= count:
                break
        buckets = next_buckets
    return selected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-root', type=Path, required=True)
    parser.add_argument('--exclude-manifest', type=Path, action='append', default=[])
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--max-per-group', type=int, default=3)
    parser.add_argument('--seed', default='trace-grouped-evaluation-v1')
    parser.add_argument('--languages', default='en', help='Comma-separated heuristic labels, or all')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.count < 1 or args.max_per_group < 1:
        parser.error('count and max-per-group must be positive')
    if args.output.exists():
        parser.error('Refusing to replace a frozen manifest; choose a new output path')
    source = args.dataset_root / 'questions.jsonl'
    raw = source.read_bytes()
    rows = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]
    exclusions = args.exclude_manifest or [HERE / 'benchmark-config.json']
    excluded_groups = {case['group'] for path in exclusions for case in json.loads(path.read_text())['cases']}
    languages = None if args.languages == 'all' else set(args.languages.split(','))
    cases = select_cases(rows, excluded_groups, args.count, args.seed, args.max_per_group, languages)
    if not cases:
        parser.error('No eligible questions remain after exclusions and language selection')
    template = json.loads((HERE / 'benchmark-config.json').read_text())
    manifest = {**template, 'name': 'Trace disjoint drawing-group evaluation',
                'frozen_at': datetime.now(timezone.utc).isoformat(), 'evaluation_only': True,
                'cases_sha256': canonical_hash(cases),
                'dataset': {'root': str(args.dataset_root.resolve()), 'questions_path': 'questions.jsonl',
                            'questions_sha256': hashlib.sha256(raw).hexdigest(), 'questions_count': len(rows)},
                'selection': {'case_count': len(cases), 'seed': args.seed, 'max_per_group': args.max_per_group,
                              'english_only': languages == {'en'}, 'language_hint_rule': 'Initial-word heuristic; not externally validated',
                              'excluded_groups': sorted(excluded_groups),
                              'strata': dict(Counter(f"{c['source']}/{c['type']}/{c['language_hint']}" for c in cases)),
                              'procedure': 'Deterministic source/type/language round-robin; grouped by building/model/project; no expected values used for selection.'},
                'cases': cases}
    manifest['evaluation_limits'] = template['evaluation_limits'] + [
        'This sample is disjoint from explicitly excluded diagnostic groups, not proof that a developer has never seen these drawings.',
        'Round-robin stratification oversamples rare types. Report per-source results; do not present this as a naturally weighted competition score.',
        'Preserve this manifest unchanged after scoring; use fresh excluded groups for an independent final holdout.']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'manifest': str(args.output), 'cases': len(cases), 'groups': len({c['group'] for c in cases}),
                      'excluded_groups': len(excluded_groups), 'cases_sha256': manifest['cases_sha256']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

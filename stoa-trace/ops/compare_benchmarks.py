#!/usr/bin/env python3
"""Compare two runs on exactly the same frozen questions and labels."""
import argparse
import json
from pathlib import Path


def compare(before, after):
    if before.get('manifest_sha256') != after.get('manifest_sha256'):
        raise ValueError('Runs must use the same frozen manifest')
    first = {r['id']: r for r in before.get('results', [])}
    second = {r['id']: r for r in after.get('results', [])}
    if not first or first.keys() != second.keys():
        raise ValueError('Runs must contain the same nonempty case IDs')
    changed = []
    for key, old in first.items():
        new = second[key]
        for field in ('path', 'question', 'expected', 'unit', 'type', 'group'):
            if old.get(field) != new.get(field):
                raise ValueError('Question, source or label changed: ' + key)
        if old['score']['outcome'] != new['score']['outcome']:
            changed.append({'id': key, 'source': old['source'], 'type': old['type'],
                            'before': old['score']['outcome'], 'after': new['score']['outcome']})
    return {'manifest_sha256': before['manifest_sha256'], 'cases': len(first),
            'before': before['summary'], 'after': after['summary'],
            'numeric_correct_delta': after['summary']['numeric_correct'] - before['summary']['numeric_correct'],
            'accuracy_percentage_point_delta': 100 * (after['summary']['accuracy_all'] - before['summary']['accuracy_all']),
            'changed_cases': changed,
            'limits': 'Same-case paired comparison. Source/type stratification is not a naturally weighted competition score. Native-mode results do not measure hosted vision accuracy.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    result = compare(json.loads(args.before.read_text()), json.loads(args.after.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    lines = ['# Paired native evaluation', '', '| Metric | Before | After |', '|---|---:|---:|']
    for label, key in [('Questions', 'cases'), ('Answered', 'answered'), ('Numeric questions', 'numeric_cases'),
                       ('Correct numeric answers', 'numeric_correct'), ('Answered numeric questions', 'numeric_answered')]:
        lines.append(f"| {label} | {result['before'][key]} | {result['after'][key]} |")
    lines.extend(['', f"Numeric accuracy including abstentions: {result['before']['accuracy_all']:.1%} → {result['after']['accuracy_all']:.1%}.",
                  f"Change: {result['accuracy_percentage_point_delta']:+.1f} percentage points.", '', result['limits'], ''])
    args.output.with_suffix('.md').write_text('\n'.join(lines))
    print(json.dumps({'comparison': str(args.output), 'numeric_correct_delta': result['numeric_correct_delta'],
                      'accuracy_percentage_point_delta': result['accuracy_percentage_point_delta']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

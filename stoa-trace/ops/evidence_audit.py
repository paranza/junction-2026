#!/usr/bin/env python3
"""Score evidence against explicitly human-reviewed object annotations.

Geometry validity alone is not evidence correctness. This evaluator scores only
cases a reviewer has marked reviewed; it never treats model regions as gold.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def valid_box(box):
    return (isinstance(box, list) and len(box) == 4
            and all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in box)
            and box[0] < box[2] and box[1] < box[3])


def iou(a, b):
    if not valid_box(a) or not valid_box(b):
        return 0
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - intersection
    return intersection / union if union else 0


def compatible_source(prediction, expected):
    for key in ('page', 'document_id', 'source_path', 'category'):
        if expected.get(key) is not None and prediction.get(key) != expected[key]:
            return False
    return True


def match_evidence(predicted, expected, threshold=.5):
    edges = []
    for pi, prediction in enumerate(predicted):
        for ei, gold in enumerate(expected):
            if not compatible_source(prediction, gold):
                continue
            identity = any(gold.get(key) and prediction.get(key) == gold[key] for key in ('guid', 'id'))
            overlap = iou(prediction.get('bbox'), gold.get('bbox'))
            located_gold = valid_box(gold.get('bbox'))
            # An exact ID does not excuse an incorrect projected highlight.
            if (located_gold and overlap >= threshold) or (not located_gold and identity):
                edges.append((2 if identity else overlap, pi, ei))
    used_predicted, used_expected = set(), set()
    for _, pi, ei in sorted(edges, reverse=True):
        if pi not in used_predicted and ei not in used_expected:
            used_predicted.add(pi)
            used_expected.add(ei)
    return {'true_positive': len(used_predicted), 'false_positive': len(predicted) - len(used_predicted),
            'false_negative': len(expected) - len(used_expected)}


def audit(report, annotations, threshold=.5):
    cases = {case['id']: case for case in report.get('results', [])}
    results, seen = [], set()
    for annotation in annotations.get('cases', []):
        case_id = annotation['case_id']
        if case_id in seen:
            raise ValueError('Duplicate human annotation case: ' + case_id)
        seen.add(case_id)
        if not annotation.get('reviewed'):
            continue
        if case_id not in cases:
            raise ValueError('Human annotation refers to a missing benchmark case: ' + case_id)
        if type(annotation.get('answer_supported')) is not bool:
            raise ValueError('Reviewed cases require an explicit answer_supported boolean')
        if not str(annotation.get('review_note') or '').strip():
            raise ValueError('Reviewed cases require a note explaining the source judgment')
        expected = annotation.get('expected_objects')
        if not isinstance(expected, list):
            raise ValueError('Reviewed cases require expected_objects, including an explicit empty list for zero')
        for item in expected:
            if not isinstance(item, dict) or not (item.get('id') or item.get('guid') or valid_box(item.get('bbox'))):
                raise ValueError('Expected objects need a source ID/GUID or a finite normalized box')
        prediction = [item for item in cases[case_id].get('response', {}).get('evidence', []) if not item.get('excluded')]
        results.append({'case_id': case_id, 'answer_supported': annotation['answer_supported'],
                        **match_evidence(prediction, expected, threshold), 'review_note': annotation['review_note']})
    tp, fp, fn = (sum(r[key] for r in results) for key in ('true_positive', 'false_positive', 'false_negative'))
    return {'reviewed_cases': len(results), 'total_benchmark_cases': len(cases),
            'unreviewed_cases': len(cases) - len(results), 'true_positive': tp, 'false_positive': fp, 'false_negative': fn,
            'precision': tp / (tp + fp) if tp + fp else None,
            'recall': tp / (tp + fn) if tp + fn else None,
            'answer_support_rate': sum(r['answer_supported'] for r in results) / len(results) if results else None,
            'iou_threshold': threshold, 'results': results,
            'limits': 'Metrics cover human-reviewed cases only. Human labels can be wrong; overlap does not validate unannotated claims or engineering safety.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--annotations', type=Path, required=True)
    parser.add_argument('--write-template', action='store_true')
    parser.add_argument('--iou', type=float, default=.5)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    report = json.loads(args.report.read_text())
    if args.write_template:
        if args.annotations.exists():
            parser.error('Refusing to overwrite existing human annotations')
        template = {'instructions': 'Inspect original drawings. Add independently identified source IDs or object boxes, then set reviewed=true, answer_supported and a review_note. Empty expected_objects means zero only after explicit review.',
                    'cases': [{'case_id': row['id'], 'path': row['path'], 'question': row['question'],
                               'reviewed': False, 'answer_supported': None, 'expected_objects': [], 'review_note': ''}
                              for row in report.get('results', [])]}
        args.annotations.parent.mkdir(parents=True, exist_ok=True)
        args.annotations.write_text(json.dumps(template, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'template': str(args.annotations), 'pending_cases': len(template['cases'])}))
        return 0
    if not 0 < args.iou <= 1:
        parser.error('--iou must be greater than zero and at most one')
    result = audit(report, json.loads(args.annotations.read_text()), args.iou)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
    print(encoded)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

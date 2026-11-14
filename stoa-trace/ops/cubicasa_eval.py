#!/usr/bin/env python3
"""Score Trace's visual inventory on CubiCasa plans, one model call per image.

Evaluation only: answer labels are read here to score and never reach Trace.
Without --allow-paid it only lists the selected images and the prior baseline.
Images whose name hashes to 0 mod 5 form the holdout; they are used only with
--holdout, so keep them for the final check.

    python ops/cubicasa_eval.py --dataset-root ~/stoa-data/junction-dataset-preview --images 40
    OPENAI_API_KEY=... python ops/cubicasa_eval.py --dataset-root ... --images 40 --allow-paid --max-calls 40
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent


def holdout(path):
    return int(hashlib.sha256(Path(path).stem.encode()).hexdigest(), 16) % 5 == 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dataset-root', type=Path, required=True)
    parser.add_argument('--images', type=int, default=40)
    parser.add_argument('--seed', default='cubicasa-dev-v1')
    parser.add_argument('--holdout', action='store_true', help='Score the holdout images instead of the dev images')
    parser.add_argument('--no-small-crops', action='store_true', help='Turn off the enlarged crops for small plans')
    parser.add_argument('--allow-paid', action='store_true', help='Make model calls (one per image, cached)')
    parser.add_argument('--max-calls', type=int, default=40, help='Hard cap on recorded model attempts in this run')
    parser.add_argument('--runtime', type=Path, help='Runtime folder for caches (default: a new temporary folder)')
    parser.add_argument('--workers', type=int, default=6, help='Images analysed in parallel')
    parser.add_argument('--output', type=Path, help='JSON report path')
    args = parser.parse_args(argv)
    root = args.dataset_root.expanduser().resolve()

    rows = [json.loads(line) for line in (root / 'questions.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    asked = collections.defaultdict(list)
    for row in rows:
        if row['path'].startswith('data/cubicasa5k/') and row['question'].startswith('How many'):
            asked[row['path']].append(row)
    pool = sorted((p for p in asked if holdout(p) == args.holdout),
                  key=lambda p: hashlib.sha256((args.seed + p).encode()).hexdigest())
    chosen = pool[:args.images]
    prior = collections.Counter((r['question'], r['answer']) for p in chosen for r in asked[p])
    mode = {q: max(((a, n) for (qq, a), n in prior.items() if qq == q), key=lambda x: x[1])[0] for q, _ in prior}
    prior_correct = sum(mode[r['question']] == r['answer'] for p in chosen for r in asked[p])
    total = sum(len(asked[p]) for p in chosen)
    print(json.dumps({'images': len(chosen), 'questions': total, 'split': 'holdout' if args.holdout else 'dev',
                      'prior_baseline': f'{prior_correct}/{total}'}))
    if not args.allow_paid:
        print('Dry run: no model calls. Add --allow-paid with a key to score the inventory.')
        return 0

    # Configure Trace before importing it.
    runtime = args.runtime or Path(tempfile.mkdtemp(prefix='trace-cubicasa-'))
    os.environ.update(STOA_DATA_ROOT=str(root), STOA_RUNTIME_DIR=str(runtime), STOA_MAX_MODEL_CALLS=str(args.max_calls))
    if args.no_small_crops:
        os.environ['STOA_SMALL_IMAGE_CROPS'] = '0'
    sys.path.insert(0, str(HERE.parent))
    from server import inventory, llm, store
    if not (llm.GEMINI_KEY if llm.VISION_PROVIDER == 'gemini' else llm.KEY):
        print('No key configured for the vision provider (OPENAI_API_KEY or GEMINI_API_KEY).', file=sys.stderr)
        return 2
    store.initialize()

    def score_image(path):
        source = root / path
        doc = store.register(source)
        data = store.extract(doc['id'])
        rows, spent = [], collections.Counter()
        for row in asked[path]:
            try:
                with llm.usage_scope():
                    answer = inventory.answer_inventory(row['question'], data, source)
            except llm.ModelError as exc:
                answer = {'value': None, 'error': str(exc)}
            value = answer.get('value') if answer else None
            if answer and not answer.get('inventory_cache_hit'):
                spent.update({k: v for k, v in (answer.get('ingestion_usage') or {}).items()
                              if isinstance(v, (int, float)) and not isinstance(v, bool)})
            rows.append({'path': path, 'question': row['question'], 'expected': row['answer'], 'value': value,
                         'correct': value is not None and value == row['answer'],
                         'category': (answer or {}).get('category'), 'error': (answer or {}).get('error')})
        print(f'{path}: {sum(r["correct"] for r in rows)}/{len(rows)}', file=sys.stderr, flush=True)
        return rows, spent

    from concurrent.futures import ThreadPoolExecutor
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        scored = list(pool.map(score_image, chosen))
    results = [r for rows, _ in scored for r in rows]
    usage = sum((spent for _, spent in scored), collections.Counter())
    failures = sum(bool(r['error']) for r in results)
    by_template = collections.defaultdict(lambda: [0, 0])
    for r in results:
        by_template[r['question']][0] += r['correct']
        by_template[r['question']][1] += 1

    correct = sum(r['correct'] for r in results)
    report = {'split': 'holdout' if args.holdout else 'dev', 'images': len(chosen), 'questions': len(results),
              'correct': correct, 'accuracy': round(correct / len(results), 4) if results else None,
              'prior_baseline': f'{prior_correct}/{total}', 'model': llm.vision_model(), 'small_image_crops': not args.no_small_crops,
              'model_errors': failures, 'usage': dict(usage), 'seconds': round(time.perf_counter() - started, 1),
              'by_template': {q: f'{c}/{n}' for q, (c, n) in sorted(by_template.items())}, 'results': results}
    output = args.output or runtime / 'cubicasa-eval.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}, ensure_ascii=False, indent=1))
    print('Report:', output)
    return 0


if __name__ == '__main__':
    sys.exit(main())

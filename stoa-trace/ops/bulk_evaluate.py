#!/usr/bin/env python3
"""Resumable, explicitly authorized bulk evaluation; labels remain local.

One worker handles each drawing's questions sequentially, so a cached visual
inventory can answer translated/category follow-ups without repeated inference.
No inference request is automatically retried. A request error abandons that
drawing, including on resume, to avoid retrying a failed shared inventory.
The server's persisted atomic
model-attempt cap remains the hard spending guard, including failed attempts.
"""
from __future__ import annotations

import argparse
import base64
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
from urllib import error, parse, request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import benchmark
from check_connections import create_ssl_context
from server.normalize import to_english
from server.inventory import count_categories

REVISION = 'bulk-evaluation-v2'


class ApiError(Exception):
    def __init__(self, code, *, fatal=False):
        super().__init__(code)
        self.fatal = fatal


class Client:
    def __init__(self, base_url, timeout=300, environ=None):
        env = os.environ if environ is None else environ
        url = parse.urlsplit(base_url)
        if (url.scheme not in {'http', 'https'} or not url.hostname or url.username
                or url.password or url.query or url.fragment):
            raise ValueError('Use an HTTP(S) base URL without credentials, query or fragment.')
        username, password, token = (env.get(k, '') for k in
                                      ('STOA_ACCESS_USERNAME', 'STOA_ACCESS_PASSWORD', 'STOA_ACCESS_TOKEN'))
        if bool(username) != bool(password):
            raise ValueError('Both Basic access settings are required.')
        if (username or token) and url.scheme != 'https' and url.hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise ValueError('Remote credentials require HTTPS.')
        self.base_url, self.timeout = base_url.rstrip('/'), timeout
        self.headers = {'Accept': 'application/json'}
        if username:
            self.headers['Authorization'] = 'Basic ' + base64.b64encode((username + ':' + password).encode()).decode()
        if token:
            self.headers['X-Trace-Token'] = token
        class NoRedirect(request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        self.opener = request.build_opener(NoRedirect(), request.HTTPSHandler(context=create_ssl_context()))

    def api(self, path, payload=None):
        headers = dict(self.headers)
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode()
            headers['Content-Type'] = 'application/json'
        req = request.Request(self.base_url + path, data=body, headers=headers)
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
                if len(raw) > 16 * 1024 * 1024:
                    raise ApiError('response_too_large')
                result = json.loads(raw)
        except error.HTTPError as exc:
            # Inspect a bounded body only to stop credential/configuration loops.
            # Neither the body nor raw network exceptions enter output/logs.
            detail = exc.read(8192).decode('utf-8', 'replace').lower()
            fatal = exc.code in {400, 401, 403, 404} or any(word in detail for word in
                ('authentication', 'credentials', 'allowance', 'configuration', 'not enabled', 'stoa_provider'))
            raise ApiError('http_' + str(exc.code), fatal=fatal) from None
        except (error.URLError, TimeoutError, OSError):
            raise ApiError('network_error') from None
        except (ValueError, UnicodeError):
            raise ApiError('invalid_json') from None
        if not isinstance(result, dict):
            raise ApiError('invalid_response')
        return result

    def documents(self):
        docs, offset = {}, 0
        for _ in range(1000):
            body = self.api('/api/documents?' + parse.urlencode({'limit': 500, 'offset': offset}))
            rows = body.get('documents')
            if not isinstance(rows, list):
                raise ApiError('invalid_document_catalog', fatal=True)
            for row in rows:
                if isinstance(row, dict) and row.get('path') and row.get('id'):
                    if row['path'] in docs and docs[row['path']]['id'] != row['id']:
                        raise ApiError('ambiguous_document_path', fatal=True)
                    docs[row['path']] = row
            offset += len(rows)
            if not rows or offset >= body.get('total', offset):
                return docs
        raise ApiError('catalog_page_limit', fatal=True)


def load_cases(path, source):
    manifest = json.loads(Path(path).read_text(encoding='utf-8'))
    cases = manifest.get('cases', [])
    if not cases or benchmark.canonical_hash(cases) != manifest.get('cases_sha256'):
        raise ValueError('Frozen manifest hash does not match.')
    ids, requests = set(), set()
    for case in cases:
        if not {'id', 'path', 'question', 'expected', 'unit', 'type', 'source'} <= set(case):
            raise ValueError('Manifest case is missing required fields.')
        identity = (case['path'], case['question'])
        if case['id'] in ids or identity in requests:
            raise ValueError('Duplicate manifest case or request.')
        ids.add(case['id']); requests.add(identity)
    selected = [c for c in cases if c['source'] == source]
    if not selected:
        raise ValueError('No cases match the explicitly selected source.')
    return manifest, selected


def unique_key(case):
    return case['path'], to_english(case['question'])


def identity_for(manifest, cases, health, args):
    return {'revision': REVISION, 'manifest_cases_sha256': manifest['cases_sha256'],
            'selected_cases_sha256': benchmark.canonical_hash(cases), 'source': args.source,
            'declared_application_commit': args.code_revision, 'base_url': args.base_url.rstrip('/'),
            'provider': health.get('provider'), 'model': health.get('model'),
            'server_provider_signature': health.get('provider_signature'),
            'server_inventory_signature': health.get('inventory_signature'),
            'server_solver_revision': health.get('solver_revision'),
            'mode': args.mode, 'verify_visual': args.verify_visual,
            'normalizer_sha256': hashlib.sha256((HERE.parent / 'server/normalize.py').read_bytes()).hexdigest(),
            'question_templates_sha256': hashlib.sha256((HERE.parent / 'server/question_templates.json').read_bytes()).hexdigest()}


class Checkpoint:
    def __init__(self, path, identity, cases, resume=False):
        self.path, self.lock_path = Path(path), Path(str(path) + '.lock')
        self.meta_path = Path(str(path) + '.meta.json')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rows = {}
        if (self.path.exists() or self.meta_path.exists()) and not resume:
            raise ValueError('Output exists. Use --resume with the identical frozen configuration.')
        if self.meta_path.exists():
            meta = json.loads(self.meta_path.read_text())
            if meta != identity:
                raise ValueError('Checkpoint configuration differs; use a new output file.')
        elif self.path.exists():
            raise ValueError('Checkpoint metadata is missing.')
        allowed = {c['id']: c for c in cases}
        if self.path.exists():
            for line in self.path.read_text(encoding='utf-8').splitlines():
                row = json.loads(line)
                case = allowed.get(row.get('id'))
                if not case or row['id'] in self.rows or row.get('path') != case['path'] or row.get('question') != case['question']:
                    raise ValueError('Checkpoint contains duplicate, foreign or changed cases.')
                self.rows[row['id']] = row
        try:
            self.lock_fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise ValueError('Checkpoint is locked. Check for another runner or a stale lock after a crash.') from None
        try:
            os.write(self.lock_fd, str(os.getpid()).encode())
            if not self.meta_path.exists():
                with self.meta_path.open('x', encoding='utf-8') as stream:
                    json.dump(identity, stream, indent=2, ensure_ascii=False)
            self.stream = self.path.open('a', encoding='utf-8')
        except Exception:
            os.close(self.lock_fd); self.lock_path.unlink(missing_ok=True)
            raise

    def append(self, row):
        if row['id'] in self.rows:
            raise ValueError('Refusing to append a duplicate case.')
        self.stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
        self.stream.flush()
        self.rows[row['id']] = row

    def close(self):
        self.stream.close(); os.close(self.lock_fd); self.lock_path.unlink(missing_ok=True)


def result_row(case, response=None, *, error_code=None, duration=0, attempted=True, tolerance=.02):
    response = response or {}
    row = {k: case.get(k) for k in ('id', 'path', 'question', 'source', 'type', 'unit', 'group', 'language_hint')}
    row.update(response=response, score=benchmark.score(case, response, tolerance),
               evidence_validation=benchmark.validate_evidence(response),
               client_duration_ms=duration, request_attempted=attempted)
    if error_code:
        row['error'] = error_code
    return row


class Evaluation:
    def __init__(self, cases, documents, checkpoint, ask, *, mode='auto', verify_visual=False, readings=1,
                 max_model_calls=250, concurrency=4, tolerance=.02):
        self.cases, self.documents, self.checkpoint, self.ask = cases, documents, checkpoint, ask
        self.mode, self.verify_visual = mode, verify_visual
        self.readings = readings  # model calls per cold page inventory
        self.limit, self.concurrency, self.tolerance = max_model_calls, concurrency, tolerance
        self.lock = threading.RLock()
        self.in_flight = self.failures = 0
        self.stopped_reason = None
        self.calls = sum(r.get('response', {}).get('usage', {}).get('model_calls', 0) for r in checkpoint.rows.values())
        self.unknown_failures = self.readings * sum(bool(r.get('error') and r.get('request_attempted')) for r in checkpoint.rows.values())
        # Different questions from one drawing can share the same uncached
        # model operation. Retrying another question after an API error would
        # therefore be an implicit paid retry of that failed inventory.
        self.failed_drawings = {r['path'] for r in checkpoint.rows.values() if r.get('error')}

    def run_group(self, cases):
        for case in cases:
            with self.lock:
                if case['id'] in self.checkpoint.rows:
                    continue
                if case['path'] in self.failed_drawings:
                    return
                if self.stopped_reason:
                    return
                # This is a conservative scheduling guard, not knowledge of
                # every provider attempt hidden inside a failed API request.
                reserve = self.readings + (1 if self.verify_visual else 0)
                if self.mode != 'native' and self.calls + self.unknown_failures + (self.in_flight + 1) * reserve > self.limit:
                    self.stopped_reason = 'client_observed_model_budget'
                    return
                self.in_flight += 1
            doc = self.documents.get(case['path'])
            fatal = False
            started = time.monotonic()
            try:
                if doc is None:
                    row = result_row(case, error_code='document_not_found', attempted=False, tolerance=self.tolerance)
                else:
                    # Gold values, reference units/types, source names, groups
                    # and language labels are evaluator-only and never sent.
                    payload = {'document_id': doc['id'], 'question': case['question'], 'page': 1,
                               'scope': 'document', 'mode': self.mode, 'verify_visual': self.verify_visual}
                    response = self.ask(payload)
                    if not isinstance(response, dict):
                        raise ApiError('invalid_response')
                    row = result_row(case, response, duration=round((time.monotonic()-started)*1000, 3), tolerance=self.tolerance)
            except ApiError as exc:
                fatal = exc.fatal
                row = result_row(case, error_code=str(exc), duration=round((time.monotonic()-started)*1000, 3), tolerance=self.tolerance)
            except Exception:
                fatal = True
                row = result_row(case, error_code='unexpected_evaluation_failure', duration=round((time.monotonic()-started)*1000, 3), tolerance=self.tolerance)
            with self.lock:
                self.in_flight -= 1
                self.calls += row.get('response', {}).get('usage', {}).get('model_calls', 0)
                self.unknown_failures += self.readings * bool(row.get('error') and row['request_attempted'])
                self.failures = self.failures + 1 if row.get('error') else 0
                if row.get('error'):
                    self.failed_drawings.add(case['path'])
                self.checkpoint.append(row)
                if fatal:
                    self.stopped_reason = 'fatal_api_or_configuration_failure'
                elif self.failures >= 3:
                    self.stopped_reason = 'three_consecutive_failures'
                if row.get('error'):
                    return

    def run(self):
        groups = defaultdict(list)
        for case in self.cases:
            groups[case['path']].append(case)
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            list(pool.map(self.run_group, groups.values()))
        return self.stopped_reason


def grouped(rows, key):
    values = defaultdict(list)
    for row in rows:
        values[key(row)].append(row)
    return {str(k): benchmark.aggregate(v) for k, v in sorted(values.items(), key=lambda item: str(item[0]))}


def summarize(cases, rows, identity, stopped_reason=None):
    all_rows = [rows.get(c['id']) or result_row(c, {'status': 'not_run'}, attempted=False) for c in cases]
    failed_drawings = {r['path'] for r in rows.values() if r.get('error')}
    unique = defaultdict(list)
    for case, row in zip(cases, all_rows):
        unique[unique_key(case)].append((case, row))
    representatives, disagreements = [], 0
    for pairs in unique.values():
        # A fixed language preference never selects the best-scoring answer.
        pairs.sort(key=lambda pair: (not bool(benchmark.ENGLISH_PREFIX.match(pair[0]['question'])), pair[0]['id']))
        representatives.append(pairs[0][1])
        signatures = {benchmark.canonical_hash({k: r['response'].get(k) for k in ('value', 'unit', 'status')})
                      for _, r in pairs if r['request_attempted'] and not r.get('error')}
        disagreements += len(signatures) > 1
    def category(row):
        return '+'.join(count_categories(to_english(row['question'])) or ()) or 'unclassified'
    return {'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(), 'identity': identity,
            'selected_questions': len(cases), 'completed_questions': len(rows), 'unrun_questions': len(cases)-len(rows),
            'drawing_groups': len({c['path'] for c in cases}), 'unique_normalized_requests': len(unique),
            'drawing_groups_with_errors': len(failed_drawings),
            'unrun_questions_in_failed_drawings': sum(c['id'] not in rows and c['path'] in failed_drawings for c in cases),
            'stopped_reason': stopped_reason, 'all_selected': benchmark.aggregate(all_rows),
            'completed_only': benchmark.aggregate(list(rows.values())),
            'unique_normalized': benchmark.aggregate(representatives),
            'duplicate_groups_with_response_disagreement': disagreements,
            'usage_scope_note': 'Use all_selected.usage for observed response usage. Failed requests can conceal additional calls/tokens. Unique representatives can omit initial inventory calls made for translated copies.',
            'by_category': grouped(all_rows, category), 'by_language': grouped(all_rows, lambda r: r.get('language_hint') or 'unknown'),
            'by_source': grouped(all_rows, lambda r: r['source']), 'by_type': grouped(all_rows, lambda r: r['type']),
            'failed_requests_with_unknown_provider_usage': sum(bool(r.get('error') and r.get('request_attempted')) for r in rows.values()),
            'provider_usage_complete': not any(r.get('error') and r.get('request_attempted') for r in rows.values()),
            'limitations': ['Unrun selected questions count as failures in all_selected; completed_only is separate.',
                           'Translated copies are not independent drawings; unique_normalized uses a fixed English preference.',
                           'Reference labels never enter inference requests. No reference boxes exist here, so localization accuracy is unmeasured.',
                           'The server atomic persisted model-attempt cap is the hard budget; failed requests can have unknown provider usage.',
                           'A failed drawing is abandoned without retry, including on resume. In-flight requests finish after the global stop.',
                           'Source/model/code and policies must remain frozen. Declared application commit must match the running server.']}


def write_summary(path, report):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    raw, unique = report['all_selected'], report['unique_normalized']
    lines = ['# Bulk evaluation', '', f"Completed {report['completed_questions']}/{report['selected_questions']} questions across {report['drawing_groups']} drawings.",
             f"Unrun: {report['unrun_questions']}. Stop reason: {report['stopped_reason'] or 'none'}.", '',
             '| Selection | Numeric correct / total | Numeric answered |', '| --- | --- | --- |',
             f"| All raw questions | {raw['numeric_correct']}/{raw['numeric_cases']} | {raw['numeric_answered']} |",
             f"| Unique normalized requests | {unique['numeric_correct']}/{unique['numeric_cases']} | {unique['numeric_answered']} |", '',
             f"Observed model calls: {raw['usage']['model_calls']}; errors: {raw['errors']}; failed requests with unknown usage: {report['failed_requests_with_unknown_provider_usage']}.", '',
             '## By category', '', '| Category | Numeric correct / total |', '| --- | --- |']
    lines += [f"| {name} | {stats['numeric_correct']}/{stats['numeric_cases']} |" for name, stats in report['by_category'].items()]
    lines += ['', *['- ' + line for line in report['limitations']], '']
    path.with_suffix('.md').write_text('\n'.join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--base-url', default='http://127.0.0.1:8787')
    parser.add_argument('--mode', choices=('native', 'auto', 'vision'), default='auto')
    parser.add_argument('--allow-paid', action='store_true')
    parser.add_argument('--verify-visual', action='store_true', help='Enable per-question second passes; much more inference.')
    parser.add_argument('--concurrency', type=int, default=4)
    parser.add_argument('--max-model-calls', type=int, required=True, help='Client scheduling guard; configure the server atomic cap too.')
    parser.add_argument('--code-revision', required=True, help='Actual frozen application commit running on the server.')
    parser.add_argument('--output', type=Path, required=True, help='Private raw JSONL checkpoint; never publish it as aggregate-only.')
    parser.add_argument('--summary', type=Path, required=True, help='Aggregate JSON report; .md companion is written.')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--timeout', type=float, default=900)  # longer than one 600 s Gemini request
    args = parser.parse_args(argv)
    if args.mode != 'native' and not args.allow_paid:
        parser.error('Automatic/vision bulk runs require --allow-paid.')
    if not 1 <= args.concurrency <= 16 or not 1 <= args.timeout <= 900 or args.max_model_calls < 0:
        parser.error('Use concurrency 1-16, timeout 1-900 and a nonnegative model-call guard.')
    if not re.fullmatch('[a-fA-F0-9]{7,40}', args.code_revision):
        parser.error('--code-revision must identify the frozen Git commit.')
    protected = {args.output.resolve(), Path(str(args.output) + '.meta.json').resolve(),
                 Path(str(args.output) + '.lock').resolve(), args.manifest.resolve()}
    if args.summary.resolve() in protected or args.summary.with_suffix('.md').resolve() in protected:
        parser.error('Manifest, checkpoint and summary paths must differ.')
    checkpoint = None
    try:
        manifest, cases = load_cases(args.manifest, args.source)
        client = Client(args.base_url, args.timeout)
        health, documents = client.api('/api/health'), client.documents()
        if args.mode != 'native' and not health.get('model_available'):
            raise ValueError('The selected server has no model configured.')
        identity = identity_for(manifest, cases, health, args)
        checkpoint = Checkpoint(args.output, identity, cases, args.resume)
        local = threading.local()
        def ask(payload):
            if not hasattr(local, 'client'):
                local.client = Client(args.base_url, args.timeout)
            return local.client.api('/api/ask', payload)
        readings = int((health.get('inventory_signature') or {}).get('readings', 1))
        evaluation = Evaluation(cases, documents, checkpoint, ask, mode=args.mode, verify_visual=args.verify_visual, readings=readings,
                                max_model_calls=args.max_model_calls, concurrency=args.concurrency,
                                tolerance=manifest.get('scoring', {}).get('measurement_relative_tolerance', .02))
        reason = evaluation.run()
        report = summarize(cases, checkpoint.rows, identity, reason)
        write_summary(args.summary, report)
        print(json.dumps({k: report[k] for k in ('selected_questions', 'completed_questions', 'unrun_questions', 'drawing_groups', 'stopped_reason')}))
        return 0 if report['unrun_questions'] == 0 and report['all_selected']['errors'] == 0 else 1
    except (ValueError, OSError, TypeError, KeyError, ApiError):
        print(json.dumps({'status': 'error', 'error': 'bulk_evaluation_configuration_or_api_failure'}), file=sys.stderr)
        return 2
    finally:
        if checkpoint is not None:
            checkpoint.close()


if __name__ == '__main__':
    raise SystemExit(main())

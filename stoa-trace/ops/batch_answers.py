#!/usr/bin/env python3
"""Answer JSONL/CSV path,question rows through the existing Trace API.

Example (native mode makes no model requests):
  python ops/batch_answers.py --input questions.jsonl --output answers.jsonl

Auto/vision require --allow-paid and retain the server's existing attempt cap.
Optional columns: page (positive integer), scope (document or page). Other
columns, including expected/gold/answer labels, are ignored and never submitted.
Paths match the server catalog exactly; a bare basename must be unambiguous.
--upload-unmatched requires an explicit --input-root and confines uploads to it.
Credentials come only from STOA_ACCESS_USERNAME/STOA_ACCESS_PASSWORD and/or
STOA_ACCESS_TOKEN in the environment, never command arguments or output.
No POST is automatically retried. Outputs are JSONL; exit 1 means row errors,
2 means configuration/output failure. Inspect statuses, not just process exit.
This interface is prepared conditionally; it is not an official Stoa contract.
"""
from __future__ import annotations

import argparse
import base64
import csv
from dataclasses import dataclass
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import sys
from urllib import error, parse, request
import uuid


FORMATS = {'.pdf', '.png', '.jpg', '.jpeg', '.svg', '.dxf', '.dwg', '.ifc', '.gif', '.webp', '.bmp', '.tif', '.tiff'}
MAX_UPLOAD = 120 * 1024 * 1024


@dataclass
class BatchError(Exception):
    kind: str
    message: str

    def __str__(self):
        return self.message


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward a credential or replay a billable POST on a redirect.
        return None


class Client:
    def __init__(self, base_url, timeout=180, environ=None):
        environment = os.environ if environ is None else environ
        split = parse.urlsplit(base_url)
        if (split.scheme not in {'http', 'https'} or not split.hostname
                or split.username is not None or split.password is not None
                or split.query or split.fragment):
            raise ValueError('Base URL must be HTTP(S), without credentials, query or fragment.')
        try:
            split.port
        except ValueError:
            raise ValueError('Base URL has an invalid port.') from None
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.headers = {'Accept': 'application/json', 'User-Agent': 'Trace-batch-answers/1.0'}
        username = environment.get('STOA_ACCESS_USERNAME', '')
        password = environment.get('STOA_ACCESS_PASSWORD', '')
        token = environment.get('STOA_ACCESS_TOKEN', '')
        if bool(username) != bool(password):
            raise ValueError('Set both STOA_ACCESS_USERNAME and STOA_ACCESS_PASSWORD, or neither.')
        if (username or token) and split.scheme != 'https' and split.hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise ValueError('Credentials require HTTPS except on the loopback interface.')
        if username:
            credential = base64.b64encode((username + ':' + password).encode()).decode()
            self.headers['Authorization'] = 'Basic ' + credential
        if token:
            self.headers['X-Trace-Token'] = token
        self.opener = request.build_opener(NoRedirect())

    def api(self, path, payload=None, *, body=None, content_type=None):
        headers = dict(self.headers)
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode()
            content_type = 'application/json'
        if content_type:
            headers['Content-Type'] = content_type
        req = request.Request(self.base_url + path, headers=headers, data=body,
                              method='POST' if body is not None else 'GET')
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                value = json.load(response)
            if not isinstance(value, dict):
                raise BatchError('invalid_response', 'Trace API returned an unexpected JSON shape.')
            return value
        except error.HTTPError as exc:
            raise BatchError('http_error', f'Trace API returned HTTP {exc.code}; request was not retried.') from None
        except (error.URLError, TimeoutError, OSError):
            raise BatchError('network_error', 'Trace API request failed; request was not retried.') from None
        except (ValueError, UnicodeError):
            raise BatchError('invalid_response', 'Trace API returned invalid JSON.') from None

    def documents(self):
        found = {}
        offset, limit = 0, 500
        for _ in range(1000):
            data = self.api('/api/documents?' + parse.urlencode({'limit': limit, 'offset': offset}))
            rows = data.get('documents')
            if not isinstance(rows, list):
                raise BatchError('invalid_catalog', 'Trace document catalog is invalid.')
            for doc in rows:
                if not isinstance(doc, dict) or not isinstance(doc.get('id'), str) or not isinstance(doc.get('path'), str):
                    raise BatchError('invalid_catalog', 'Trace document catalog contains an invalid document.')
                found[doc['id']] = doc
            offset += len(rows)
            total = data.get('total')
            if not rows or (isinstance(total, int) and offset >= total):
                return list(found.values())
        raise BatchError('catalog_limit', 'Trace document catalog exceeded the pagination limit.')

    def upload(self, path):
        size = path.stat().st_size
        if path.suffix.lower() not in FORMATS or not 0 < size <= MAX_UPLOAD:
            raise BatchError('invalid_upload', 'Upload must be a supported nonempty drawing no larger than 120 MB.')
        boundary = 'TraceBatch' + uuid.uuid4().hex
        name = re.sub(r'[^A-Za-z0-9_.() -]', '_', path.name)[:180]
        media = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        prefix = (f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\n'
                  f'Content-Type: {media}\r\n\r\n').encode()
        with path.open('rb') as stream:
            content = stream.read(MAX_UPLOAD + 1)
        if not 0 < len(content) <= MAX_UPLOAD:
            raise BatchError('invalid_upload', 'Upload became empty or exceeded 120 MB while reading.')
        body = prefix + content + f'\r\n--{boundary}--\r\n'.encode()
        response = self.api('/api/upload', body=body, content_type='multipart/form-data; boundary=' + boundary)
        docs = response.get('documents')
        if not isinstance(docs, list) or len(docs) != 1 or not isinstance(docs[0], dict) or not isinstance(docs[0].get('id'), str):
            raise BatchError('invalid_response', 'Trace upload did not return one document identifier.')
        return docs[0]

    def ask(self, payload):
        return self.api('/api/ask', payload)


def input_rows(path):
    """Yield (source line, row, parse error) and continue after bad JSONL rows."""
    with path.open(encoding='utf-8-sig', newline='') as stream:
        if path.suffix.lower() == '.csv':
            reader = csv.DictReader(stream)
            if not reader.fieldnames or not {'path', 'question'} <= set(reader.fieldnames):
                raise ValueError('CSV requires path and question column headers.')
            for row in reader:
                yield reader.line_num, row, None
        else:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except (ValueError, UnicodeError):
                    yield line_number, None, BatchError('invalid_row', 'Input line is not valid JSON.')
                    continue
                yield line_number, row, None


def normalized_path(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096 or '\x00' in value:
        raise BatchError('invalid_path', 'Each row requires a nonempty path of at most 4096 characters.')
    value = value.strip().replace('\\', '/')
    path = PurePosixPath(value)
    if '..' in path.parts:
        raise BatchError('invalid_path', 'Parent-directory traversal is not accepted.')
    return path.as_posix()


def local_upload(path_text, root):
    path = Path(path_text).expanduser()
    candidate = (path if path.is_absolute() else root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise BatchError('outside_input_root', 'Upload path, including any symlink, must stay inside --input-root.') from None
    if not candidate.is_file():
        raise BatchError('missing_file', 'Unmatched drawing is not a readable file inside --input-root.')
    return candidate


def resolve_document(path_text, documents, input_root=None):
    match_path = path_text
    if input_root is not None and Path(path_text).is_absolute():
        try:
            match_path = Path(path_text).resolve().relative_to(input_root).as_posix()
        except ValueError:
            raise BatchError('outside_input_root', 'Absolute input path must stay inside --input-root.') from None
    exact = [doc for doc in documents if normalized_path(doc['path']) == match_path]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise BatchError('ambiguous_path', 'Multiple catalog documents match this exact path.')
    # A supplied directory is meaningful. Never replace it with another source
    # simply because the basename happens to be unique.
    if '/' not in match_path:
        names = [doc for doc in documents if PurePosixPath(doc['path'].replace('\\', '/')).name == match_path]
        if len(names) == 1:
            return names[0]
        if len(names) > 1:
            raise BatchError('ambiguous_path', 'Basename matches multiple documents; supply the exact catalog path.')
    return None


def process_rows(rows, client, *, mode='native', input_root=None, upload_unmatched=False):
    try:
        documents = client.documents()
        catalog_error = None
    except BatchError as exc:
        documents, catalog_error = [], exc
    uploaded = {}
    for line_number, row, parse_error in rows:
        output = {'input_line': line_number, 'mode': mode}
        try:
            if parse_error:
                raise parse_error
            if not isinstance(row, dict):
                raise BatchError('invalid_row', 'Each input row must be an object with path and question.')
            path = normalized_path(row.get('path'))
            question = row.get('question')
            if not isinstance(question, str) or not 2 <= len(question.strip()) <= 2500:
                raise BatchError('invalid_question', 'Question must contain between 2 and 2500 characters.')
            scope = row.get('scope')
            scope = 'document' if scope is None or scope == '' else scope
            if isinstance(scope, str):
                scope = scope.strip()
            if not isinstance(scope, str) or scope not in {'document', 'page'}:
                raise BatchError('invalid_scope', 'Scope must be document or page.')
            page = row.get('page')
            if isinstance(page, str):
                page = page.strip()
            page = 1 if page is None or page == '' else page
            if isinstance(page, bool) or re.fullmatch(r'[1-9][0-9]*', str(page)) is None:
                raise BatchError('invalid_page', 'Page must be a positive integer.')
            output.update({'path': path, 'question': question.strip(), 'page': int(page), 'scope': scope})
            if catalog_error:
                raise catalog_error
            doc = uploaded.get(path) or resolve_document(path, documents, input_root)
            if doc is None and upload_unmatched:
                doc = client.upload(local_upload(path, input_root))
                uploaded[path] = doc
            if doc is None:
                raise BatchError('document_not_found', 'No exact catalog match; explicit --upload-unmatched and --input-root are required to upload.')
            # Deliberate allowlist: no gold, expected, row mode, source unit or
            # type is transferred from a benchmark file into inference.
            payload = {'document_id': doc['id'], 'question': question.strip(), 'page': int(page), 'scope': scope, 'mode': mode}
            result = client.ask(payload)
            output.update({key: result.get(key) for key in ('answer', 'value', 'unit', 'method', 'usage')})
            output.update({'status': result.get('status', 'unknown'), 'evidence': result.get('evidence', []),
                           'document_id': doc['id'], 'answer_id': result.get('id')})
            for key in ('warnings', 'ingestion_usage', 'interpreted_question', 'verification'):
                if key in result:
                    output[key] = result[key]
        except BatchError as exc:
            output.update({'status': 'error', 'error': {'kind': exc.kind, 'message': exc.message}})
        except OSError:
            output.update({'status': 'error', 'error': {'kind': 'file_error', 'message': 'Local drawing could not be read.'}})
        yield output


def main(argv=None, *, client=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input', type=Path, required=True, help='JSONL or CSV with path,question rows')
    parser.add_argument('--output', type=Path, required=True, help='Output JSONL; must differ from input')
    parser.add_argument('--base-url', default='http://127.0.0.1:8787')
    parser.add_argument('--mode', choices=('native', 'auto', 'vision'), default='native')
    parser.add_argument('--allow-paid', action='store_true', help='Allow the chosen auto/vision mode; server caps still apply')
    parser.add_argument('--upload-unmatched', action='store_true')
    parser.add_argument('--input-root', type=Path, help='Explicit local root permitted for unmatched uploads')
    parser.add_argument('--timeout', type=float, default=900)  # longer than one 600 s Gemini request
    args = parser.parse_args(argv)
    if args.mode != 'native' and not args.allow_paid:
        parser.error('auto/vision mode requires --allow-paid; native is the zero-model default')
    if args.upload_unmatched and args.input_root is None:
        parser.error('--upload-unmatched requires --input-root')
    if not 1 <= args.timeout <= 900:
        parser.error('--timeout must be from 1 to 900 seconds')
    if args.input.resolve() == args.output.resolve():
        parser.error('Input and output must differ; inputs are never overwritten')
    root = args.input_root.expanduser().resolve() if args.input_root else None
    if root is not None and not root.is_dir():
        parser.error('--input-root must be an existing directory')
    count = errors = 0
    try:
        api = client or Client(args.base_url, args.timeout)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('w', encoding='utf-8') as stream:
            for output in process_rows(input_rows(args.input), api, mode=args.mode, input_root=root,
                                       upload_unmatched=args.upload_unmatched):
                stream.write(json.dumps(output, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush()
                count += 1
                errors += output['status'] == 'error'
        if count == 0:
            raise ValueError('Input contains no question rows.')
    except (OSError, ValueError, csv.Error, BatchError):
        print('Batch configuration/input/output failure; inspect local paths and API configuration. No credential was printed.', file=sys.stderr)
        return 2
    print(json.dumps({'rows': count, 'errors': errors, 'mode': args.mode}), file=sys.stderr)
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())

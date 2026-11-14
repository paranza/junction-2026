from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_PROJECT_DATA_ROOT = ROOT / 'datasets' / 'junction-dataset-preview'
_DOWNLOADS_DATA_ROOT = Path.home() / 'Downloads' / 'junction-dataset-preview'
_DEFAULT_DATA_ROOT = (_PROJECT_DATA_ROOT if _PROJECT_DATA_ROOT.is_dir() or not _DOWNLOADS_DATA_ROOT.is_dir()
                      else _DOWNLOADS_DATA_ROOT)
_CONFIGURED_DATA_ROOT = Path(os.environ.get('STOA_DATA_ROOT', _DEFAULT_DATA_ROOT)).expanduser()
DATA_ROOT = (_CONFIGURED_DATA_ROOT if _CONFIGURED_DATA_ROOT.is_absolute() else ROOT / _CONFIGURED_DATA_ROOT).resolve()
RUNTIME = Path(os.environ.get('STOA_RUNTIME_DIR', ROOT / 'runtime')).expanduser().resolve()
from .rendering import RASTER_SUFFIXES
FORMATS = {'.pdf', '.ifc', '.dxf', '.svg', '.dwg'} | RASTER_SUFFIXES
for folder in (RUNTIME, RUNTIME / 'uploads', RUNTIME / 'cache', RUNTIME / 'previews'):
    folder.mkdir(parents=True, exist_ok=True)
_locks: dict[str, threading.Lock] = {}
_lock_guard = threading.Lock()
EXTRACTOR_REVISION = hashlib.sha256(b''.join((Path(__file__).parent / name).read_bytes()
                                           for name in ('extraction.py', 'rendering.py'))).hexdigest()[:16]


def connection():
    db = sqlite3.connect(RUNTIME / 'trace.sqlite3', timeout=30)
    db.row_factory = sqlite3.Row
    journal = os.environ.get('STOA_SQLITE_JOURNAL', 'WAL').upper()
    if journal not in {'WAL', 'DELETE'}:
        raise ValueError('STOA_SQLITE_JOURNAL must be WAL or DELETE')
    db.execute('PRAGMA journal_mode=' + journal)
    return db


def initialize():
    with connection() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE, absolute_path TEXT NOT NULL,
          name TEXT NOT NULL, format TEXT NOT NULL, source TEXT NOT NULL,
          size INTEGER NOT NULL, mtime REAL NOT NULL, indexed INTEGER DEFAULT 0,
          page_count INTEGER, error TEXT, uploaded INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS answers (
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL, question TEXT NOT NULL,
          result TEXT NOT NULL, original_result TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS analysis_cache (
          key TEXT PRIMARY KEY, kind TEXT NOT NULL, result TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, detail TEXT, created REAL NOT NULL);
        ''')
    if DATA_ROOT.is_dir():
        for p in sorted((DATA_ROOT / 'data').rglob('*')) if (DATA_ROOT / 'data').is_dir() else []:
            if p.is_file() and p.suffix.lower() in FORMATS:
                register(p)


def register(path: Path, uploaded=False):
    path = path.resolve()
    try:
        relative = path.relative_to(DATA_ROOT).as_posix()
    except ValueError:
        relative = 'uploads/' + path.name
    doc_id = hashlib.sha256(relative.encode()).hexdigest()[:20]
    stat = path.stat()
    source = 'uploads' if uploaded else (relative.split('/')[1] if relative.startswith('data/') else 'project')
    with connection() as db:
        old = db.execute('SELECT size,mtime FROM documents WHERE id=?', (doc_id,)).fetchone()
        changed = old is not None and (old['size'] != stat.st_size or old['mtime'] != stat.st_mtime)
        db.execute('''INSERT INTO documents(id,path,absolute_path,name,format,source,size,mtime,uploaded)
          VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET size=excluded.size,mtime=excluded.mtime,absolute_path=excluded.absolute_path''',
          (doc_id, relative, str(path), path.name, path.suffix[1:].lower(), source, stat.st_size, stat.st_mtime, int(uploaded)))
        if changed:
            db.execute('UPDATE documents SET indexed=0,error=NULL,page_count=NULL WHERE id=?', (doc_id,))
            cache_path(doc_id).unlink(missing_ok=True)
    return get_document(doc_id)


def public_document(row):
    result = dict(row)
    result.pop('absolute_path', None)
    result['indexed'] = bool(result.get('indexed'))
    result['uploaded'] = bool(result.get('uploaded'))
    return result


def get_document(doc_id):
    with connection() as db:
        row = db.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone()
    if not row:
        raise KeyError(doc_id)
    return public_document(row)


def get_path(doc_id):
    with connection() as db:
        row = db.execute('SELECT absolute_path FROM documents WHERE id=?', (doc_id,)).fetchone()
    if not row:
        raise KeyError(doc_id)
    return Path(row[0])


def resolve_evidence_path(path: str):
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = DATA_ROOT / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(DATA_ROOT) and not candidate.is_relative_to(RUNTIME / 'uploads'):
        raise ValueError('Evidence source is outside this project')
    return register(candidate, uploaded=candidate.is_relative_to(RUNTIME / 'uploads'))


def list_documents(search='', limit=100, offset=0, source=None, uploaded=None):
    where, args = [], []
    if search:
        where.append('(name LIKE ? OR path LIKE ?)')
        args += ['%' + search + '%'] * 2
    if source:
        where.append('source=?')
        args.append(source)
    if uploaded is not None:
        where.append('uploaded=?')
        args.append(int(uploaded))
    clause = ' WHERE ' + ' AND '.join(where) if where else ''
    with connection() as db:
        total = db.execute('SELECT COUNT(*) FROM documents' + clause, args).fetchone()[0]
        rows = db.execute('SELECT * FROM documents' + clause + ' ORDER BY uploaded DESC,indexed DESC,CASE source WHEN \'swiss_dwellings\' THEN 0 WHEN \'ifc_models\' THEN 1 WHEN \'cubicasa5k\' THEN 2 ELSE 3 END,name LIMIT ? OFFSET ?', args + [limit, offset]).fetchall()
        sources = [dict(r) for r in db.execute('SELECT source,COUNT(*) AS count FROM documents GROUP BY source ORDER BY count DESC')]
    return {'documents': [public_document(r) for r in rows], 'total': total, 'sources': sources}


def cache_path(doc_id):
    return RUNTIME / 'cache' / (doc_id + '.json')


def extract(doc_id):
    from .extraction import extract_document
    path = get_path(doc_id)
    register(path, uploaded=get_document(doc_id).get('uploaded', False))
    fingerprint = source_fingerprint(doc_id)
    with _lock_guard:
        lock = _locks.setdefault(doc_id, threading.Lock())
    with lock:
        cached = cache_path(doc_id)
        if cached.exists():
            previous = json.loads(cached.read_text())
            if (previous.get('extractor_revision') == EXTRACTOR_REVISION
                    and previous.get('source_fingerprint') == fingerprint):
                return previous
        try:
            data = extract_document(get_path(doc_id), DATA_ROOT)
            data['extractor_revision'] = EXTRACTOR_REVISION
            digest = hashlib.sha256()
            with get_path(doc_id).open('rb') as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(chunk)
            data['source_sha256'] = digest.hexdigest()
            data['document_id'] = doc_id
            data['source_fingerprint'] = fingerprint
            data.setdefault('warnings', [])
            data.setdefault('pages', [])
            data.setdefault('objects', [])
            data.setdefault('metadata', {})
            data['page_count'] = data.get('page_count') or len(data['pages']) or 1
            cached.write_text(json.dumps(data, ensure_ascii=False, default=str))
            with connection() as db:
                db.execute('UPDATE documents SET indexed=1,page_count=?,error=NULL WHERE id=?', (data['page_count'], doc_id))
            return data
        except Exception:
            with connection() as db:
                db.execute('UPDATE documents SET error=? WHERE id=?', ('Extraction could not complete for this file.', doc_id))
            raise


def save_answer(answer_id, doc_id, question, result):
    encoded = json.dumps(result, ensure_ascii=False, default=str)
    with connection() as db:
        db.execute('INSERT INTO answers VALUES(?,?,?,?,?,?)', (answer_id, doc_id, question, encoded, encoded, time.time()))


def read_answer(answer_id, original=False):
    with connection() as db:
        row = db.execute('SELECT * FROM answers WHERE id=?', (answer_id,)).fetchone()
    if not row:
        raise KeyError(answer_id)
    return json.loads(row['original_result' if original else 'result'])


def list_answers(limit=12):
    with connection() as db:
        rows = db.execute('SELECT result,created FROM answers ORDER BY created DESC LIMIT ?', (limit,)).fetchall()
    return [{**json.loads(row['result']), 'created_at': row['created']} for row in rows]


def update_answer(answer_id, result):
    with connection() as db:
        db.execute('UPDATE answers SET result=? WHERE id=?', (json.dumps(result, ensure_ascii=False), answer_id))


def record_event(kind, detail):
    with connection() as db:
        db.execute('INSERT INTO events(kind,detail,created) VALUES(?,?,?)', (kind, json.dumps(detail), time.time()))


def record_message_usage(session_id, message_id, usage, question, status, answer_id=None):
    """Record lifecycle metadata once per state change, never another model charge."""
    if not session_id or not message_id:
        return
    record_event('message_usage', {'session_id': session_id, 'message_id': message_id,
                                 'question': str(question)[:2500], 'status': str(status)[:50],
                                 'answer_id': answer_id, 'cache_hit': bool((usage or {}).get('cache_hit'))})


def session_usage(session_id):
    """Rebuild actual attempt usage; duplicate metadata/responses are idempotent.

    A missing response remains unknown, including while a request is running.
    Cached-analysis ingestion costs belong to the original attempt, not each
    later answer. Legacy events without tracking cannot be assigned to a session.
    """
    from .costs import summarize_calls
    with connection() as db:
        rows = db.execute("SELECT id,kind,detail,created FROM events WHERE kind IN ('model_request','model_response','message_usage') ORDER BY id").fetchall()
    requests, responses, messages = {}, {}, {}
    revision = 0
    for row in rows:
        try:
            detail = json.loads(row['detail'])
        except (TypeError, ValueError):
            continue
        if not isinstance(detail, dict) or detail.get('session_id') != session_id:
            continue
        message_id = detail.get('message_id')
        if not isinstance(message_id, str) or not message_id:
            continue
        revision = max(revision, row['id'])
        message = messages.setdefault(message_id, {'message_id': message_id, 'question': '',
                                                  'status': 'pending', 'answer_id': None,
                                                  'created_at': row['created'], 'cache_hit': False})
        if row['kind'] == 'message_usage':
            for key in ('question', 'status', 'answer_id', 'cache_hit'):
                if key in detail:
                    message[key] = detail[key]
            message['updated_at'] = row['created']
            continue
        request_id = detail.get('request_id')
        if not isinstance(request_id, str) or not request_id:
            continue
        if row['kind'] == 'model_request':
            # One reservation is one attempt. A duplicated event cannot charge twice.
            requests.setdefault(request_id, {'message_id': message_id,
                                             'model': str(detail.get('provider') or 'unknown') + '/' + str(detail.get('model') or 'unknown'),
                                             'created': row['created']})
        else:
            responses[request_id] = detail
    calls = []
    per_message = {message_id: [] for message_id in messages}
    for request_id, request in requests.items():
        response = responses.get(request_id, {})
        # A mismatched response cannot supply another message/model's usage.
        valid = (response.get('message_id') == request['message_id']
                 and str(response.get('provider')) + '/' + str(response.get('model')) == request['model'])
        call = {'model': request['model'], 'created': request['created'],
                'usage': response.get('usage') if valid else None}
        calls.append(call)
        per_message[request['message_id']].append(call)
    for message_id, message in messages.items():
        message['usage'] = summarize_calls(per_message[message_id], cache_hit=message.pop('cache_hit'))
    return {'session_id': session_id, 'revision': revision, 'usage': summarize_calls(calls),
            'messages': list(messages.values()), 'message_count': len(messages)}


def attribution(doc):
    if doc['source'] == 'uploads':
        return 'Uploaded project drawing. Source rights remain with its owner.'
    path = DATA_ROOT / 'data' / doc['source'] / 'LICENSE.md'
    if path.exists():
        text = path.read_text(errors='replace')
        lines = text.splitlines()
        selected = [line for line in lines if doc['name'] in line]
        return '\n'.join(selected[:3])[:2500] if selected else '\n'.join(lines[:12])[:2500]
    return 'Source: ' + doc['source'] + '. See the dataset source licence.'


def key_lock(key):
    """Serialize one expensive analysis/review in this single-worker runtime."""
    with _lock_guard:
        return _locks.setdefault(key, threading.RLock())


_digest_cache = {}


def file_digest(path):
    path = Path(path).resolve()
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns)
    with _lock_guard:
        previous = _digest_cache.get(key)
    if previous is not None:
        return previous
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    result = digest.hexdigest()
    with _lock_guard:
        _digest_cache[key] = result
    return result


def source_fingerprint(doc_id):
    """Hash source, actual rendered views, semantic siblings and linked models.

    IFC renderers accept every stem_* view, not only plans. A winning PDF view
    can still depend on its same-name semantic SVG for extraction and evidence.
    """
    from .rendering import visual_sources
    source = get_path(doc_id).resolve()
    related = {source}
    models = {source} if source.suffix.lower() == '.ifc' else {
        candidate.resolve() for candidate in source.parent.glob('*.ifc')
        if source.stem == candidate.stem or source.stem.startswith(candidate.stem + '_')}
    related.update(models)
    for candidate in [source, *models]:
        related.update(path.resolve() for path in visual_sources(candidate))
    # Preserve every same-view export, including the SVG hidden by a PDF in
    # visual_sources' display preference and the CAD used for PDF extraction.
    for candidate in list(related):
        for suffix in FORMATS:
            sibling = candidate.with_suffix(suffix)
            if sibling.is_file():
                related.add(sibling.resolve())
    parts = [(str(path), file_digest(path)) for path in sorted(related)]
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest()


def analysis_key(kind, components):
    return hashlib.sha256(json.dumps({'kind': kind, **components}, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def cached_analysis(key):
    with connection() as db:
        row = db.execute('SELECT result FROM analysis_cache WHERE key=?', (key,)).fetchone()
    return json.loads(row[0]) if row else None


def save_analysis(key, kind, result):
    # A cache contains immutable computed analysis, never a user's later review.
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO analysis_cache VALUES(?,?,?,?)',
                   (key, kind, json.dumps(result, ensure_ascii=False, default=str), time.time()))


def reserve_model_request(limit, detail):
    """Reserve an attempt atomically, including failed/translated/cross-check calls."""
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        count = db.execute("SELECT COUNT(*) FROM events WHERE kind='model_request'").fetchone()[0]
        if count >= limit:
            return False
        db.execute('INSERT INTO events(kind,detail,created) VALUES(?,?,?)',
                   ('model_request', json.dumps(detail), time.time()))
    return True


def workspace_usage(days=30):
    """Aggregate immutable attempts, including legacy unscoped calls, once each."""
    from .costs import summarize_calls
    from datetime import datetime, timezone, timedelta
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days-1)
    with connection() as db:
        rows = db.execute("SELECT id,kind,detail,created FROM events WHERE kind IN ('model_request','model_response') ORDER BY id").fetchall()
    attempts, responses = {}, {}
    for row in rows:
        try:
            detail = json.loads(row['detail'])
        except (ValueError, TypeError):
            continue
        if not isinstance(detail, dict):
            continue
        identity = detail.get('request_id')
        if not identity:
            if row['kind'] != 'model_request':
                continue
            # Earlier reservations lacked correlation IDs. Count each actual
            # attempt, but never invent a matching response or token charge.
            identity = f"legacy-event-{row['id']}"
        if row['kind'] == 'model_request':
            if start.timestamp() <= row['created'] < (start+timedelta(days=days)).timestamp():
                attempts.setdefault(identity, {**detail, 'created': row['created']})
        else:
            responses[identity] = detail
    calls, buckets = [], {}
    for identity, attempt in attempts.items():
        response = responses.get(identity, {})
        valid = all(response.get(k) == attempt.get(k) for k in ('provider','model','message_id'))
        call = {'model': str(attempt.get('provider') or 'unknown')+'/'+str(attempt.get('model') or 'unknown'), 'created': attempt['created'], 'usage': response.get('usage') if valid else None}
        calls.append(call)
        day = datetime.fromtimestamp(call['created'], timezone.utc).date().isoformat()
        buckets.setdefault(day, []).append(call)
    daily = [{'date': (start+timedelta(days=i)).date().isoformat(), 'usage': summarize_calls(buckets.get((start+timedelta(days=i)).date().isoformat(), []))} for i in range(days)]
    return {'days': days, 'timezone': 'UTC', 'aggregate': summarize_calls(calls), 'daily': daily}


def chat_workspace():
    with connection() as db:
        db.executescript("""CREATE TABLE IF NOT EXISTS chat_projects(id TEXT PRIMARY KEY,name TEXT NOT NULL,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS chat_threads(id TEXT PRIMARY KEY,title TEXT NOT NULL,project_id TEXT,document_id TEXT,created REAL NOT NULL,updated REAL NOT NULL);""")
        return {'projects':[dict(r) for r in db.execute('SELECT * FROM chat_projects ORDER BY created')], 'threads':[dict(r) for r in db.execute('SELECT t.*,d.name AS document_name FROM chat_threads t LEFT JOIN documents d ON d.id=t.document_id ORDER BY t.updated DESC')]}

def get_chat(identity):
    with connection() as db:
        row = db.execute('SELECT t.*,d.name AS document_name FROM chat_threads t LEFT JOIN documents d ON d.id=t.document_id WHERE t.id=?', (identity,)).fetchone()
        if not row:
            raise KeyError(identity)
        return dict(row)

def attach_chat_drawing(identity, document_id, next_identity):
    """Resolve the target chat from persisted state in one transaction."""
    chat_workspace()
    now = time.time()
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        drawing = db.execute('SELECT id,name FROM documents WHERE id=?', (document_id,)).fetchone()
        if not drawing:
            raise KeyError(document_id)
        current = db.execute('SELECT * FROM chat_threads WHERE id=?', (identity,)).fetchone()
        if current and current['document_id'] == document_id:
            target = identity
        elif current and current['document_id']:
            existing = db.execute('SELECT id FROM chat_threads WHERE document_id=? AND project_id IS ? ORDER BY updated DESC LIMIT 1', (document_id, current['project_id'])).fetchone()
            target = existing['id'] if existing else next_identity
            if not existing:
                collision = db.execute('SELECT document_id,project_id FROM chat_threads WHERE id=?', (target,)).fetchone()
                if collision and (collision['document_id'] != document_id or collision['project_id'] != current['project_id']):
                    raise ValueError('Chat identity already belongs to another drawing')
                db.execute('INSERT OR IGNORE INTO chat_threads VALUES(?,?,?,?,?,?)', (target, drawing['name'], current['project_id'], document_id, now, now))
        elif current:
            target = identity
            title = drawing['name'] if current['title'] in ('New chat', 'Floor plan') else current['title']
            db.execute('UPDATE chat_threads SET title=?,document_id=?,updated=? WHERE id=?', (title, document_id, now, target))
        else:
            target = identity
            db.execute('INSERT INTO chat_threads VALUES(?,?,?,?,?,?)', (target, drawing['name'], None, document_id, now, now))
    return get_chat(target)

def get_chat_project(identity):
    with connection() as db:
        row = db.execute('SELECT * FROM chat_projects WHERE id=?', (identity,)).fetchone()
        if not row:
            raise KeyError(identity)
        return dict(row)

def create_chat(name, project_id=None, document_id=None, project=False, identity=None):
    import uuid
    chat_workspace()
    identity=identity or str(uuid.uuid4()); now=time.time()
    with connection() as db:
        if project:
            db.execute('INSERT OR IGNORE INTO chat_projects VALUES(?,?,?)',(identity,name,now))
        else:
            if project_id and not db.execute('SELECT id FROM chat_projects WHERE id=?',(project_id,)).fetchone(): raise KeyError(project_id)
            if document_id and not db.execute('SELECT id FROM documents WHERE id=?',(document_id,)).fetchone(): raise KeyError(document_id)
            if document_id and name == 'Floor plan': name = db.execute('SELECT name FROM documents WHERE id=?',(document_id,)).fetchone()[0]
            db.execute('INSERT OR IGNORE INTO chat_threads VALUES(?,?,?,?,?,?)',(identity,name,project_id,document_id,now,now))
    return identity

def update_chat(identity,title=None,project_id=None,document_id=None):
    chat_workspace()
    with connection() as db:
        old=db.execute('SELECT * FROM chat_threads WHERE id=?',(identity,)).fetchone()
        if not old: raise KeyError(identity)
        if project_id and not db.execute('SELECT id FROM chat_projects WHERE id=?',(project_id,)).fetchone(): raise KeyError(project_id)
        if document_id and not db.execute('SELECT id FROM documents WHERE id=?',(document_id,)).fetchone(): raise KeyError(document_id)
        if document_id and not title and old['title'] == 'New chat': title = db.execute('SELECT name FROM documents WHERE id=?',(document_id,)).fetchone()[0]
        db.execute('UPDATE chat_threads SET title=?,project_id=?,document_id=?,updated=? WHERE id=?',(title or old['title'],old['project_id'] if project_id is None else project_id or None,document_id or old['document_id'],time.time(),identity))

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
FORMATS = {'.pdf', '.png', '.jpg', '.jpeg', '.ifc', '.dxf', '.svg', '.dwg'}
for folder in (RUNTIME, RUNTIME / 'uploads', RUNTIME / 'cache', RUNTIME / 'previews'):
    folder.mkdir(parents=True, exist_ok=True)
_locks: dict[str, threading.Lock] = {}
_lock_guard = threading.Lock()
EXTRACTOR_REVISION = hashlib.sha256((Path(__file__).parent / 'extraction.py').read_bytes()).hexdigest()[:16]


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
          VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET size=excluded.size,mtime=excluded.mtime''',
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


def list_documents(search='', limit=100, offset=0, source=None):
    where, args = [], []
    if search:
        where.append('(name LIKE ? OR path LIKE ?)')
        args += ['%' + search + '%'] * 2
    if source:
        where.append('source=?')
        args.append(source)
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
    with _lock_guard:
        lock = _locks.setdefault(doc_id, threading.Lock())
    with lock:
        cached = cache_path(doc_id)
        if cached.exists():
            previous = json.loads(cached.read_text())
            if previous.get('extractor_revision') == EXTRACTOR_REVISION and previous.get('source_sha256'):
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

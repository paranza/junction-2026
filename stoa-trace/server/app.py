from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(Path.home() / '.config/stoa-junction-2026/secrets.env', override=False)
load_dotenv(ROOT / '.env', override=False)

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import llm, rendering, store
from .selection import highlight_target, native_highlight, describe_highlights

ACCESS_TOKEN = os.environ.get('STOA_ACCESS_TOKEN', '')


@asynccontextmanager
async def lifespan(app):
    store.initialize()
    yield


app = FastAPI(title='Trace · Drawing evidence', version='0.1.0', lifespan=lifespan)


@app.middleware('http')
async def project_access(request: Request, call_next):
    # Deployment proxies may pass this header; no provider secret reaches a browser.
    if ACCESS_TOKEN and request.url.path.startswith('/api/') and request.url.path != '/api/health':
        provided = request.headers.get('x-trace-token', '')
        if not secrets.compare_digest(provided, ACCESS_TOKEN):
            return JSONResponse({'detail': 'This workspace needs an authorized project connection.'}, status_code=401)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    return response


def known_document(doc_id):
    try:
        return store.get_document(doc_id)
    except KeyError:
        raise HTTPException(404, 'Drawing not found') from None


def extracted(doc_id):
    known_document(doc_id)
    try:
        return store.extract(doc_id)
    except Exception as exc:
        # Native parsers can contain source text in exceptions, so keep user errors bounded.
        raise HTTPException(422, 'This file could not be extracted. Try its PDF, image, DXF or IFC counterpart.') from None


@app.get('/api/health')
def health():
    with store.connection() as db:
        count = db.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
        indexed = db.execute('SELECT COUNT(*) FROM documents WHERE indexed=1').fetchone()[0]
    return {'status': 'ok', 'model_available': llm.model_available(), 'model': llm.MODEL,
            'documents': count, 'indexed_documents': indexed, 'auth_required': bool(ACCESS_TOKEN), 'version': '0.1.0'}


@app.get('/api/documents')
def documents(search: str = '', limit: int = 100, offset: int = 0, source: str | None = None):
    return store.list_documents(search[:300], max(1, min(limit, 1000)), max(0, offset), source)


@app.get('/api/documents/{doc_id}')
def document_detail(doc_id: str):
    doc = known_document(doc_id)
    data = extracted(doc_id)
    doc = store.get_document(doc_id)
    credit = store.attribution(doc)
    objects = data.get('objects', [])
    pages = [{k: v for k, v in p.items() if k in {'page', 'width', 'height', 'name', 'source_path'}} for p in data.get('pages', [])]
    return {'document': {**doc, 'credit': credit, 'attribution': credit, 'license_credit': credit}, 'pages': pages,
            'page_count': data.get('page_count', 1), 'objects': objects[:2000], 'object_count': len(objects),
            'metadata': data.get('metadata', {}), 'warnings': data.get('warnings', [])}


@app.get('/api/documents/{doc_id}/pages/{page}/image')
def document_image(doc_id: str, page: int, size: int = 2400):
    known_document(doc_id)
    size = max(600, min(size, 4000))
    path = store.get_path(doc_id)
    cache = store.RUNTIME / 'previews' / f'{doc_id}-{path.stat().st_mtime_ns}-{page}-{size}.png'
    if not cache.exists():
        try:
            image, _ = rendering.render_page(path, page, size)
            cache.write_bytes(rendering.png_bytes(image))
        except Exception:
            raise HTTPException(422, 'No two-dimensional preview is available. Native model objects can still be inspected.') from None
    return FileResponse(cache, media_type='image/png', headers={'Cache-Control': 'private,max-age=3600'})


@app.get('/api/documents/{doc_id}/original')
def document_original(doc_id: str):
    doc = known_document(doc_id)
    return FileResponse(store.get_path(doc_id), filename=doc['name'])


@app.post('/api/upload')
async def upload(files: list[UploadFile] = File(...)):
    if len(files) > 12:
        raise HTTPException(413, 'Upload at most 12 drawings at a time.')
    result = []
    for file in files:
        name = Path(file.filename or 'drawing').name
        if Path(name).suffix.lower() not in store.FORMATS:
            raise HTTPException(415, 'Use PDF, PNG, JPEG, SVG, DXF, DWG or IFC files.')
        safe_name = re.sub(r'[^\w.() -]', '_', name)[:180]
        target = store.RUNTIME / 'uploads' / (uuid.uuid4().hex[:10] + '-' + safe_name)
        total = 0
        try:
            with target.open('wb') as stream:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > 120 * 1024 * 1024:
                        raise HTTPException(413, 'Each drawing must be smaller than 120 MB.')
                    stream.write(chunk)
            if total == 0:
                raise HTTPException(422, 'The uploaded file is empty.')
            result.append(store.register(target, uploaded=True))
        except Exception:
            target.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
    return {'documents': result}


_suggestions_cache = {}


@app.get('/api/questions/{doc_id}')
def suggested_questions(doc_id: str):
    # Deliberately uses task wording only. Gold answers never enter extraction or model prompts.
    doc = known_document(doc_id)
    if not _suggestions_cache:
        path = store.DATA_ROOT / 'questions.jsonl'
        if path.exists():
            for line in path.open():
                try:
                    item = json.loads(line)
                    question = item.get('question', '')
                    if re.match(r'^(How|What|On |In |Calculate|Which|Give|List|Provide)', question):
                        _suggestions_cache.setdefault(item['path'], []).append(question)
                except (ValueError, KeyError):
                    pass
    items = list(dict.fromkeys(_suggestions_cache.get(doc['path'], [])))[:8]
    if not items:
        items = ['What information is shown in this drawing?', 'How many doors are shown?', 'What is the area of the largest labelled room?']
    return {'questions': items, 'source': 'Supplied example question wording' if doc['path'] in _suggestions_cache else 'Suggested starting questions'}


class AskRequest(BaseModel):
    document_id: str
    question: str = Field(min_length=2, max_length=2500)
    page: int = Field(default=1, ge=1)
    scope: str = 'document'
    region: list[float] | None = None
    mode: str = 'auto'


def _evidence(result, doc_id):
    normalized = []
    for i, evidence in enumerate(result.get('evidence', [])):
        item = dict(evidence)
        item['id'] = str(item.get('id') or f'item-{i + 1}')
        item.setdefault('label', item.get('type', 'Source object'))
        item.setdefault('page', 1)
        item.setdefault('document_id', doc_id)
        source = item.get('source_path')
        if source:
            try:
                linked = store.resolve_evidence_path(str(source))
                item['document_id'] = linked['id']
                item['source_path'] = linked['path']
            except (ValueError, OSError):
                item.pop('source_path', None)
        box = item.get('bbox')
        if box:
            if not isinstance(box, (list, tuple)) or len(box) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in box):
                item.pop('bbox', None)
            else:
                box = [max(0, min(1, v)) for v in box]
                if box[0] < box[2] and box[1] < box[3]:
                    item['bbox'] = box
                else:
                    item.pop('bbox', None)
        normalized.append(item)
    result['evidence'] = normalized
    return result


@app.post('/api/ask')
def ask(payload: AskRequest):
    started = time.monotonic()
    doc = known_document(payload.document_id)
    if payload.mode not in {'auto', 'native', 'vision'} or payload.scope not in {'document', 'page'}:
        raise HTTPException(422, 'Choose a supported analysis mode and scope.')
    if payload.region is not None:
        r = payload.region
        if len(r) != 4 or not all(math.isfinite(v) and 0 <= v <= 1 for v in r) or r[0] >= r[2] or r[1] >= r[3]:
            raise HTTPException(422, 'The selected drawing region is invalid.')
    data = extracted(payload.document_id)
    if payload.page > data.get('page_count', 1):
        raise HTTPException(422, 'That drawing page does not exist.')
    source = store.get_path(payload.document_id)
    from .native_qa import answer_native
    result = None
    question = payload.question.strip()
    native_data = data
    if payload.scope == 'page':
        native_data = {**data, 'metadata': {**data.get('metadata', {}), 'requested_scope': 'page'},
                       'pages': [p for p in data.get('pages', []) if p.get('page') == payload.page],
                       'objects': [o for o in data.get('objects', []) if o.get('page') == payload.page]}
    if payload.mode != 'vision' and not payload.region:
        if not (payload.scope == 'page' and source.suffix.lower() == '.ifc'):
            result = native_highlight(question, native_data, source, store.DATA_ROOT) if highlight_target(question) else answer_native(question, native_data, source, store.DATA_ROOT)
        if result is None and payload.mode == 'auto' and llm.model_available() and re.search(r'[^\x00-\x7f]', question):
            try:
                translated = llm.translate_question(question)
                result = answer_native(translated, native_data, source, store.DATA_ROOT)
                if result:
                    result['interpreted_question'] = translated
            except llm.ModelError:
                pass
    if result is None and payload.mode != 'native':
        try:
            result = llm.answer_with_model(question, data, source, payload.page, payload.scope, payload.region)
        except llm.ModelError as exc:
            raise HTTPException(503, str(exc)) from None
    if result is None:
        result = {'answer': 'The native source tools could not establish this answer. Use automatic analysis to inspect the drawing, or choose a question supported by its native records.',
                  'value': None, 'unit': None, 'method': 'native', 'status': 'insufficient_evidence', 'evidence': [], 'warnings': [], 'scope': payload.scope}
    result = _evidence(result, payload.document_id)
    if highlight_target(question):
        result = describe_highlights(result)
    result.setdefault('warnings', [])
    result.setdefault('status', 'computed')
    result.setdefault('scope', payload.scope)
    result.setdefault('method', 'native')
    result.setdefault('value', None)
    result.setdefault('unit', None)
    result.setdefault('answer', str(result['value']))
    quantity_type = {'count': 'count', 'm²': 'area', 'ft²': 'area', 'm³': 'volume', 'm': 'length', 'mm': 'length', 'ft': 'length'}.get(result.get('unit'), 'text')
    result.setdefault('operation', quantity_type)
    result.setdefault('can_review', result['operation'] == 'count' and result.get('value') == len(result['evidence']) and bool(result['evidence']))
    result['question'] = payload.question
    result['document_id'] = doc['id']
    result['document'] = doc
    result['id'] = uuid.uuid4().hex
    result['duration_ms'] = round((time.monotonic() - started) * 1000)
    result['attribution'] = store.attribution(doc)
    result['provenance'] = {'source_path': doc['path'], 'source_sha256': data.get('source_sha256'),
                            'extractor_revision': data.get('extractor_revision'), 'file_size': doc['size'],
                            'file_modified': doc['mtime'], 'scope': payload.scope, 'page': payload.page,
                            'region': payload.region, 'question_source': 'user'}
    store.save_answer(result['id'], doc['id'], payload.question, result)
    return result


class ReviewRequest(BaseModel):
    excluded_evidence_ids: list[str] = Field(default_factory=list, max_length=10000)


@app.post('/api/answers/{answer_id}/review')
def review_answer(answer_id: str, payload: ReviewRequest):
    try:
        original = store.read_answer(answer_id, original=True)
    except KeyError:
        raise HTTPException(404, 'Answer not found') from None
    if not original.get('can_review'):
        raise HTTPException(422, 'This answer does not support count corrections.')
    ids = {e['id'] for e in original['evidence']}
    excluded = set(payload.excluded_evidence_ids)
    if not excluded <= ids:
        raise HTTPException(422, 'A correction references an unknown source object.')
    result = {**original, 'evidence': [{**e, 'excluded': e['id'] in excluded} for e in original['evidence']],
              'value': len(ids - excluded), 'status': 'needs_review', 'human_reviewed': True,
              'excluded_evidence_ids': sorted(excluded), 'original_value': original['value']}
    result['answer'] = f'{result["value"]} included objects after your review.'
    result['calculation'] = f'{len(ids)} located objects − {len(excluded)} excluded = {result["value"]}'
    result['warnings'] = list(dict.fromkeys(original.get('warnings', []) + ['Your corrections change the included set; they do not independently establish detection completeness.']))
    store.update_answer(answer_id, result)
    return result


@app.get('/api/answers/{answer_id}')
def answer_detail(answer_id: str):
    try:
        return store.read_answer(answer_id)
    except KeyError:
        raise HTTPException(404, 'Answer not found') from None


@app.get('/api/answers')
def recent_answers(limit: int = 12):
    return {'answers': store.list_answers(max(1, min(limit, 50)))}


DIST = ROOT / 'frontend' / 'dist'
if DIST.exists():
    app.mount('/', StaticFiles(directory=DIST, html=True), name='workspace')

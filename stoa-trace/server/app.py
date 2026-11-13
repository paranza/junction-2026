from __future__ import annotations

import hashlib
import copy
from datetime import datetime, timezone
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
def document_image(doc_id: str, page: int, request: Request, size: int = 2400):
    known_document(doc_id)
    size = max(600, min(size, 4000))
    path = store.get_path(doc_id)
    try:
        fingerprint = store.source_fingerprint(doc_id)
    except OSError:
        raise HTTPException(422, 'The source or linked drawing preview is unavailable.') from None
    render_revision = hashlib.sha256(Path(rendering.__file__).read_bytes()).hexdigest()[:16]
    key = hashlib.sha256(f'{doc_id}:{fingerprint}:{render_revision}:{page}:{size}'.encode()).hexdigest()
    etag = '"' + key + '"'
    headers = {'Cache-Control': 'private, no-cache', 'ETag': etag}
    if request.headers.get('if-none-match') == etag:
        return Response(status_code=304, headers=headers)
    cache = store.RUNTIME / 'previews' / f'{doc_id}-{key}.png'
    with store.key_lock('preview:' + key):
        if not cache.exists():
            try:
                image, _ = rendering.render_page(path, page, size)
                staging = cache.with_suffix('.tmp')
                staging.write_bytes(rendering.png_bytes(image))
                staging.replace(cache)
            except Exception:
                raise HTTPException(422, 'No two-dimensional preview is available. Native model objects can still be inspected.') from None
    return FileResponse(cache, media_type='image/png', headers=headers)


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
    cross_check: bool = False


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


def _solver_revision():
    digest = hashlib.sha256()
    for name in ('app.py', 'native_qa.py', 'extraction.py', 'selection.py', 'llm.py', 'inventory.py', 'verification.py', 'rendering.py', 'store.py'):
        path = Path(__file__).parent / name
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:20]


def _cross_check(payload, question, native_result, data, source):
    """Compare independently image-derived candidates only at matching scope."""
    from . import inventory
    unavailable = {'status': 'unavailable', 'native_value': native_result.get('value') if native_result else None,
                   'visual_value': None, 'unit': 'count', 'evidence': [],
                   'reason': 'A comparable native count and independent visual inventory are required.'}
    # Printed annotations and independently calculated room-outline geometry
    # are comparable without another model call. Rounding uses the dataset's 2% rule.
    if native_result and native_result.get('unit') in {'m²', 'm2'} and native_result.get('evidence'):
        evidence = native_result['evidence']
        fields = ('printed_area_m2', 'geometry_area_m2')
        if all(all(type((e.get('properties') or {}).get(field)) in (int, float)
                       and math.isfinite(e['properties'][field]) and e['properties'][field] >= 0
                       for field in fields) for e in evidence):
            printed = sum(e['properties']['printed_area_m2'] for e in evidence)
            geometry = sum(e['properties']['geometry_area_m2'] for e in evidence)
            agreement = abs(printed - geometry) <= max(abs(printed) * .02, .01)
            return {'status': 'agreement' if agreement else 'disagreement', 'native_value': printed,
                    'visual_value': geometry, 'unit': 'm²', 'evidence': _evidence(copy.deepcopy(native_result), payload.document_id)['evidence'],
                    'native_method': 'printed_area_annotations', 'visual_method': 'native_polygon_geometry',
                    'native_label': 'Printed annotations', 'visual_label': 'Room outline geometry',
                    'scope': native_result.get('scope'), 'difference': geometry - printed, 'relative_tolerance': .02,
                    'reason': 'Printed room areas and independently calculated polygon areas agree within 2% (with 0.01 m² rounding tolerance).' if agreement else 'Printed room areas and room-outline geometry differ beyond 2%. Inspect the source annotations, polygon interpretation and quantity role before choosing a working area.'}
    if payload.mode == 'native':
        return {**unavailable, 'reason': 'Native mode never launches a model cross-check. Choose automatic analysis to request one.'}
    if not native_result or native_result.get('unit') != 'count' or not inventory.count_category(question):
        return unavailable
    scope = str(native_result.get('scope', '')).lower()
    method = str(native_result.get('method', '')).lower()
    if (source.suffix.lower() == '.ifc' or 'model' in scope or 'schedule' in scope or 'schedule' in method
            or (data.get('page_count', 1) > 1 and payload.scope != 'page' and not payload.region)):
        return {**unavailable, 'status': 'scope_mismatch', 'reason': 'Model inventories, schedule rows and visible drawing objects have different scope; they are not contradictory counts.'}
    if any(not item.get('bbox') and not item.get('polygon') for item in native_result.get('evidence', [])):
        return {**unavailable, 'status': 'scope_mismatch', 'reason': 'Native elements lack a registered drawing location, so visible-object completeness cannot be compared.'}
    try:
        visual = inventory.answer_inventory(question, data, source, payload.page, payload.scope, payload.region)
    except (llm.ModelError, ValueError, OSError):
        return {**unavailable, 'reason': 'The independent visual inventory was unavailable; the native answer is preserved.'}
    if not visual or visual.get('value') is None:
        return unavailable
    native_value, visual_value = native_result.get('value'), visual['value']
    return {'status': 'agreement' if native_value == visual_value else 'disagreement',
            'native_value': native_value, 'visual_value': visual_value, 'unit': 'count',
            'evidence': _evidence(copy.deepcopy(visual), payload.document_id)['evidence'],
            'native_method': native_result.get('method'), 'visual_method': visual.get('method'),
            'scope': visual.get('scope'), 'inventory_cache_hit': visual.get('inventory_cache_hit'),
            'reason': 'The independent visual candidates agree with the native count; agreement does not prove completeness.' if native_value == visual_value else 'Native source objects and independently located visual candidates disagree. Inspect both sets and their interpretation before choosing a working quantity.'}


def _native_region_answer(question, data, source, page, region):
    """Only count native boxes registered to this rendered view.

    IFC object projections carry local page numbers from several separate
    views, so page=1 alone cannot resolve a selected model view. Standalone DXF
    extents also lack registration to the renderer's fitted layout viewport.
    """
    from . import inventory
    if source.suffix.lower() in {'.ifc', '.dwg'}:
        return None
    views = rendering.visual_sources(source)
    if not views:
        return None
    visible_source = views[0].resolve()
    if source.suffix.lower() == '.dxf' and visible_source == source.resolve():
        return None
    category = inventory.count_category(question)
    if category is None:
        return None
    for obj in data.get('objects', []):
        if obj.get('page') != page:
            continue
        obj_category = inventory.canonical_category(obj.get('category') or obj.get('type'))
        if obj_category != category or not obj.get('source_path'):
            continue
        object_source = Path(str(obj['source_path'])).expanduser()
        if not object_source.is_absolute():
            object_source = store.DATA_ROOT / object_source
        if object_source.resolve() != visible_source:
            return None
    return inventory.native_region_count(question, data, page, region)


def _compute_analysis(payload, question, data, source):
    from .native_qa import answer_native
    from . import inventory
    result = None
    native_result = None
    native_data = data
    if payload.scope == 'page':
        native_data = {**data, 'metadata': {**data.get('metadata', {}), 'requested_scope': 'page'},
                       'pages': [p for p in data.get('pages', []) if p.get('page') == payload.page],
                       'objects': [o for o in data.get('objects', []) if o.get('page') == payload.page]}
    if payload.mode != 'vision':
        if payload.region:
            result = _native_region_answer(question, data, source, payload.page, payload.region)
        elif not (payload.scope == 'page' and source.suffix.lower() == '.ifc'):
            result = native_highlight(question, native_data, source, store.DATA_ROOT) if highlight_target(question) else answer_native(question, native_data, source, store.DATA_ROOT)
        if result is None and payload.mode == 'auto' and llm.model_available() and re.search(r'[^\x00-\x7f]', question):
            try:
                translated = llm.translate_question(question)
                result = answer_native(translated, native_data, source, store.DATA_ROOT) if not payload.region else _native_region_answer(translated, data, source, payload.page, payload.region)
                if result:
                    result['interpreted_question'] = translated
            except llm.ModelError:
                pass
        native_result = copy.deepcopy(result)
    if result is None and payload.mode != 'native':
        try:
            result = inventory.answer_inventory(question, data, source, payload.page, payload.scope, payload.region)
            if result is None:
                result = llm.answer_with_model(question, data, source, payload.page, payload.scope, payload.region)
        except llm.ModelError as exc:
            raise HTTPException(503, str(exc)) from None
        except (ValueError, OSError):
            raise HTTPException(422, 'This source has no usable visual preview. Native source tools remain available.') from None
    if result is None:
        result = {'answer': 'The native source tools could not establish this answer. Use automatic analysis to inspect the drawing, or choose a question supported by its native records.',
                  'value': None, 'unit': None, 'method': 'native', 'status': 'insufficient_evidence', 'evidence': [], 'warnings': [], 'scope': payload.scope}
    if payload.cross_check:
        result['reconciliation'] = _cross_check(payload, question, native_result, data, source)
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
    doc = store.get_document(payload.document_id)
    source = store.get_path(payload.document_id)
    question = payload.question.strip()
    key = store.analysis_key('answer', {'document': doc['id'], 'source': data.get('source_fingerprint'),
                            'extractor': data.get('extractor_revision'), 'solver': _solver_revision(),
                            'model': llm.MODEL, 'prompt': llm.PROMPT_REVISION, 'question': question,
                            'page': payload.page, 'scope': payload.scope, 'region': payload.region,
                            'mode': payload.mode, 'cross_check': payload.cross_check})
    with llm.usage_scope():
        with store.key_lock('answer:' + key):
            result = store.cached_analysis(key)
            hit = result is not None
            if hit:
                result['cached_analysis_usage'] = result.get('usage', {})
            else:
                result = _compute_analysis(payload, question, data, source)
                result['usage'] = llm.usage_snapshot()
                store.save_analysis(key, 'answer', result)
        result['usage'] = llm.usage_snapshot(cache_hit=hit)
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
    if result['operation'] == 'count':
        from .inventory import answer_category
        result.setdefault('category', answer_category(question, result))
    result['usage']['inventory_cache_hit'] = bool(result.get('inventory_cache_hit'))
    result.setdefault('can_review', result['operation'] == 'count' and result.get('value') is not None and result.get('value') == len(result['evidence']))
    result['question'] = payload.question
    result['document_id'] = doc['id']
    result['document'] = doc
    result['id'] = uuid.uuid4().hex
    result['duration_ms'] = round((time.monotonic() - started) * 1000)
    result['attribution'] = store.attribution(doc)
    result['request_context'] = {'document_id': doc['id'], 'scope': payload.scope, 'page': payload.page, 'region': payload.region}
    result['provenance'] = {'source_path': doc['path'], 'source_sha256': data.get('source_sha256'),
                            'source_fingerprint': data.get('source_fingerprint'), 'extractor_revision': data.get('extractor_revision'),
                            'solver_revision': _solver_revision(), 'file_size': doc['size'], 'file_modified': doc['mtime'],
                            'scope': payload.scope, 'page': payload.page, 'region': payload.region, 'question_source': 'user'}
    store.save_answer(result['id'], doc['id'], payload.question, result)
    return result


class ManualEvidence(BaseModel):
    id: str | None = Field(default=None, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=80)
    document_id: str | None = None
    page: int = Field(default=1, ge=1)
    bbox: list[float] = Field(min_length=4, max_length=4)
    note: str = Field(default='', max_length=2000)


class ReviewRequest(BaseModel):
    excluded_evidence_ids: list[str] = Field(default_factory=list, max_length=10000)
    added_evidence: list[ManualEvidence] = Field(default_factory=list, max_length=1000)
    note: str = Field(default='', max_length=4000)


@app.post('/api/answers/{answer_id}/review')
def review_answer(answer_id: str, payload: ReviewRequest):
    with store.key_lock('review:' + answer_id):
        try:
            original = store.read_answer(answer_id, original=True)
            current = store.read_answer(answer_id)
        except KeyError:
            raise HTTPException(404, 'Answer not found') from None
        if not original.get('can_review'):
            raise HTTPException(422, 'This answer does not support count corrections.')
        original_evidence = copy.deepcopy(original.get('evidence', []))
        ids = {e['id'] for e in original_evidence}
        allowed_documents = {original['document_id']} | {e.get('document_id', original['document_id']) for e in original_evidence}
        from .inventory import answer_category, canonical_category
        expected_category = canonical_category(original.get('category') or answer_category(original.get('question', ''), original))
        added = []
        for item in payload.added_evidence:
            box = item.bbox
            if not item.label.strip():
                raise HTTPException(422, 'A manually added object needs a meaningful label.')
            category = canonical_category(item.category) if item.category else expected_category or 'manual_object'
            if expected_category and category != expected_category:
                raise HTTPException(422, f'This answer counts {expected_category} objects. A manual addition must use the same category.')
            if not all(math.isfinite(v) and 0 <= v <= 1 for v in box) or box[0] >= box[2] or box[1] >= box[3]:
                raise HTTPException(422, 'A manually added object has invalid page coordinates.')
            doc_id = item.document_id or original['document_id']
            if doc_id not in allowed_documents:
                raise HTTPException(422, 'A manually added object must belong to the original answer sources.')
            context = original.get('request_context', {})
            if context.get('scope') == 'page' or context.get('region'):
                if doc_id != context.get('document_id', original['document_id']) or item.page != context.get('page', 1):
                    raise HTTPException(422, 'A manually added object must stay on the originally requested page.')
                if context.get('region'):
                    from .inventory import contains
                    if not contains(context['region'], box):
                        raise HTTPException(422, 'A manually added object must remain inside the originally selected region.')
            detail = extracted(doc_id)
            if item.page > detail.get('page_count', 1):
                raise HTTPException(422, 'A manually added object references a missing page.')
            identity = item.id or 'manual-' + uuid.uuid4().hex
            if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', identity) or identity in ids or any(a['id'] == identity for a in added):
                raise HTTPException(422, 'Each manually added object needs a distinct safe identifier.')
            added.append({'id': identity, 'label': item.label.strip(), 'category': category,
                          'document_id': doc_id, 'page': item.page, 'bbox': box, 'note': item.note,
                          'evidence_kind': 'manual', 'source_verified': False, 'manually_added': True, 'manual': True})
        excluded = set(payload.excluded_evidence_ids)
        all_ids = ids | {e['id'] for e in added}
        if not excluded <= all_ids:
            raise HTTPException(422, 'A correction references an unknown source object.')
        reviewed_value = len(all_ids - excluded)
        previous_review = current.get('review', {})
        revision = int(previous_review.get('revision', 0)) + 1
        review = {'revision': revision, 'reviewed_at': datetime.now(timezone.utc).isoformat(), 'note': payload.note,
                  'added_count': len(added), 'excluded_count': len(excluded), 'original_value': original['value'], 'reviewed_value': reviewed_value}
        prior_added = {e['id'] for e in current.get('added_evidence', [])}
        prior_excluded = set(current.get('excluded_evidence_ids', []))
        revision_record = {**review, 'added_evidence': copy.deepcopy(added), 'excluded_evidence_ids': sorted(excluded),
                           'changes': {'added_ids': sorted({e['id'] for e in added} - prior_added),
                                       'removed_manual_ids': sorted(prior_added - {e['id'] for e in added}),
                                       'excluded_ids': sorted(excluded - prior_excluded),
                                       'restored_ids': sorted(prior_excluded - excluded)}}
        history = list(current.get('review_history', [])) + [revision_record]
        result = {**original, 'evidence': [{**e, 'excluded': e['id'] in excluded} for e in original_evidence + added],
                  'value': reviewed_value, 'status': 'needs_review', 'human_reviewed': True,
                  'excluded_evidence_ids': sorted(excluded), 'original_value': original['value'],
                  'original_evidence': original_evidence, 'added_evidence': added, 'category': expected_category or None,
                  'review': review, 'review_history': history,
                  'completeness': {'human_review_performed': True, 'independently_verified': False}}
        result['answer'] = f'{reviewed_value} included objects after your review.'
        result['calculation'] = f'{len(ids)} original objects + {len(added)} added − {len(excluded)} excluded = {reviewed_value}'
        result['warnings'] = list(dict.fromkeys(original.get('warnings', []) + ['Your corrections change the included set; they do not independently establish detection completeness.']))
        if added and not expected_category:
            result['warnings'].append('Manual classifications are user supplied; the original count did not identify a single object category.')
        store.update_answer(answer_id, result)
    return result


@app.get('/api/answers/{answer_id}/reviews')
def answer_reviews(answer_id: str):
    try:
        current = store.read_answer(answer_id)
        original = store.read_answer(answer_id, original=True)
    except KeyError:
        raise HTTPException(404, 'Answer not found') from None
    return {'answer_id': answer_id, 'original_value': original.get('value'),
            'original_evidence': original.get('evidence', []), 'revisions': current.get('review_history', [])}


@app.get('/api/answers/{answer_id}')
def answer_detail(answer_id: str, original: bool = False):
    try:
        return store.read_answer(answer_id, original=original)
    except KeyError:
        raise HTTPException(404, 'Answer not found') from None


@app.get('/api/answers')
def recent_answers(limit: int = 12):
    return {'answers': store.list_answers(max(1, min(limit, 50)))}


DIST = ROOT / 'frontend' / 'dist'
if DIST.exists():
    app.mount('/', StaticFiles(directory=DIST, html=True), name='workspace')

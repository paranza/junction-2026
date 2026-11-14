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
from functools import lru_cache
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent
from .config import load_environment
load_environment(ROOT)

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import inventory, llm, rendering, store  # inventory validates its settings at startup
from .normalize import to_english, translation_preserves_constraints
from .selection import highlight_target, native_highlight, describe_highlights

ACCESS_TOKEN = os.environ.get('STOA_ACCESS_TOKEN', '')


@asynccontextmanager
async def lifespan(app):
    _solver_revision()
    store.initialize()
    yield


app = FastAPI(title='Metria · Drawing evidence', version='0.1.0', lifespan=lifespan)


@app.middleware('http')
async def project_access(request: Request, call_next):
    # Deployment proxies may pass this header; no provider secret reaches a browser.
    if ACCESS_TOKEN and request.url.path.startswith('/api/') and request.url.path != '/api/health':
        provided = request.headers.get('x-trace-token', '')
        if not secrets.compare_digest(provided, ACCESS_TOKEN):
            return JSONResponse({'detail': 'This workspace needs an authorized project connection.'}, status_code=401)
    response = await call_next(request)
    if request.url.path.startswith('/api/') or request.url.path == '/':
        response.headers.setdefault('Cache-Control', 'no-store')
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
    from . import inventory, visual_audit
    with store.connection() as db:
        count = db.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
        indexed = db.execute('SELECT COUNT(*) FROM documents WHERE indexed=1').fetchone()[0]
    return {'status': 'ok', 'model_available': llm.model_available(), 'provider': llm.PROVIDER, 'model': llm.MODEL,
            'documents': count, 'indexed_documents': indexed, 'auth_required': bool(ACCESS_TOKEN), 'version': '0.1.0',
            'provider_signature': llm.provider_signature(), 'inventory_signature': inventory.config_signature(),
            'audit_signature': visual_audit.config_signature(), 'solver_revision': _solver_revision(),
            'source_revision':_source_revision(),'restart_required':_solver_revision()!=_source_revision()}


@app.get('/api/documents')
def documents(search: str = '', limit: int = 100, offset: int = 0, source: str | None = None, uploaded: bool | None = None):
    return store.list_documents(search[:300], max(1, min(limit, 1000)), max(0, offset), source, uploaded)


@app.get('/api/usage')
def session_usage(session_id: uuid.UUID):
    summary = store.session_usage(str(session_id))
    return {'session_id': summary['session_id'], 'revision': summary['revision'],
            'aggregate': summary['usage'], 'message_count': summary['message_count'],
            'by_message': [{**item, 'request_id': item['message_id']} for item in summary['messages']]}


@app.get('/api/usage/overview')
def usage_overview(days: int = 30):
    if days not in (7, 30, 90):
        raise HTTPException(422, 'Choose 7, 30 or 90 days.')
    return store.workspace_usage(days)


@app.get('/api/media/status')
def media_status():
    from . import cloudinary_media
    return {'available': cloudinary_media.available(), 'provider': 'cloudinary'}


@app.post('/api/answers/{answer_id}/evidence/{evidence_id:path}/closeup')
def evidence_closeup(answer_id: str, evidence_id: str):
    from . import cloudinary_media
    try:
        return cloudinary_media.create_closeup(answer_id, evidence_id)
    except cloudinary_media.MediaError as exc:
        raise HTTPException(exc.status, str(exc)) from None


@app.get('/api/media/{token}.png')
def closeup_image(token: str):
    from . import cloudinary_media
    try:
        path = cloudinary_media.media_path(token)
    except cloudinary_media.MediaError as exc:
        raise HTTPException(exc.status, str(exc)) from None
    return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'private, no-cache'})


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
    names = []
    for file in files:
        name = Path(file.filename or 'drawing').name
        if Path(name).suffix.lower() not in store.FORMATS:
            raise HTTPException(415, 'Use PDF, common raster images, SVG, DXF, DWG or IFC files.')
        names.append(re.sub(r'[^\w.() -]', '_', name)[:180])
    if len({name.casefold() for name in names}) != len(names):
        raise HTTPException(422, 'Upload each filename once per batch so paired drawing files remain unambiguous.')
    # A shared prefix preserves plan.pdf / plan.dxf sibling discovery while
    # keeping independent upload batches isolated from each other.
    batch_prefix = uuid.uuid4().hex[:12] + '-'
    for file, safe_name in zip(files, names):
        target = store.RUNTIME / 'uploads' / (batch_prefix + safe_name)
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
    verify_visual: bool = False
    session_id: uuid.UUID | None = None
    previous_answer_id: str | None = Field(default=None, max_length=100)


class MeasurementRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    kind: Literal['area', 'length'] = 'area'
    source_fingerprint: str = Field(min_length=16, max_length=128)
    calibration: dict
    geometry: list[list[float]] = Field(min_length=2, max_length=513)


def _measurement_context(doc_id, page):
    data = extracted(doc_id)
    if page > data.get('page_count', 1):
        raise HTTPException(422, 'That drawing page does not exist.')
    try:
        picture, _ = rendering.render_page(store.get_path(doc_id), page, 2400)
    except (ValueError, OSError):
        raise HTTPException(422, 'This source has no calibrated two-dimensional measurement view.') from None
    return data, {'document_id': doc_id, 'page': page,
                  'source_fingerprint': data['source_fingerprint'],
                  'image_width': picture.width, 'image_height': picture.height}


@app.get('/api/documents/{doc_id}/inspection')
def inspection(doc_id: str, ceiling_height_m: float | None = None, glazing_height_m: float | None = None,
               daylight_min_ratio: float | None = None, egress_limit_m: float | None = None,
               turning_diameter_m: float | None = None, waste_factor: float | None = None):
    """Takeoff, tender estimate and code checks from the drawing's native objects (no model call)."""
    from .inspector import inspect
    bounds = {'ceiling_height_m': (1.8, 10), 'glazing_height_m': (0.2, 6), 'daylight_min_ratio': (0, 1),
              'egress_limit_m': (1, 500), 'turning_diameter_m': (0.5, 5), 'waste_factor': (0, 1)}
    options = {}
    for key, (lo, hi) in bounds.items():
        value = locals()[key]
        if value is not None:
            if not (math.isfinite(value) and lo <= value <= hi):
                raise HTTPException(422, f'{key} must be between {lo} and {hi}.')
            options[key] = value
    return inspect(extracted(doc_id), options)


@app.get('/api/documents/{doc_id}/measurement-context')
def measurement_context(doc_id: str, page: int = 1):
    if page < 1:
        raise HTTPException(422, 'Page must be positive.')
    return _measurement_context(doc_id, page)[1]


@app.post('/api/documents/{doc_id}/measurement')
def measure_document(doc_id: str, payload: MeasurementRequest):
    from .measurements import calibrated_polygon_area, calibrated_length, MeasurementError
    data, context = _measurement_context(doc_id, payload.page)
    if payload.source_fingerprint != context['source_fingerprint']:
        raise HTTPException(409, 'The source changed. Reload the page and set its reference length again.')
    operation = calibrated_polygon_area if payload.kind == 'area' else calibrated_length
    try:
        measured = operation(payload.geometry, payload.calibration, page=payload.page,
                             image_width=context['image_width'], image_height=context['image_height'], document_id=doc_id)
    except MeasurementError as exc:
        raise HTTPException(422, str(exc)) from None
    doc = known_document(doc_id)
    answer_id = uuid.uuid4().hex
    xs, ys = zip(*payload.geometry)
    evidence = {'id': 'measurement-' + answer_id, 'document_id': doc_id, 'page': payload.page,
                'label': 'Your outlined area' if payload.kind == 'area' else 'Your measured segment',
                'bbox': [min(xs), min(ys), max(xs), max(ys)], 'evidence_kind': 'manual',
                'manual': True, 'source_verified': False, 'value': measured['value'], 'unit': measured['unit'],
                'properties': {'measurement_basis': 'Explicit reference length and user-selected geometry',
                               'reference_length': f"{payload.calibration.get('value')} {payload.calibration.get('unit')}",
                               'reference_points': payload.calibration.get('points')}}
    if payload.kind == 'area':
        evidence['polygon'] = payload.geometry
    result = {**measured, 'id': answer_id, 'document_id': doc_id, 'document': doc,
              'question': 'Measure my outlined area' if payload.kind == 'area' else 'Measure my selected length',
              'answer': f"{measured['value']:g} {measured['unit']}, calculated from your reference length and selected geometry.",
              'operation': payload.kind, 'status': 'needs_review', 'scope': f'Page {payload.page}',
              'can_review': False, 'evidence': [evidence],
              'calculation': f"Selected geometry, scaled using your {payload.calibration.get('value')} {payload.calibration.get('unit')} reference = {measured['value']:g} {measured['unit']}",
              'usage': {'model_calls': 0, 'input_tokens': 0, 'output_tokens': 0, 'cached_input_tokens': 0,
                        'cache_hit': False, 'cost_estimate_usd': 0.0, 'cost_basis': 'deterministic_geometry'},
              'warnings': ['Check the reference endpoints, stated length, perspective and boundary. This is a user-calibrated measurement, not an independently verified net/gross room area.'],
              'request_context': {'document_id': doc_id, 'scope': 'page', 'page': payload.page, 'region': None},
              'provenance': {'source_path': doc['path'], 'source_fingerprint': data['source_fingerprint'],
                             'source_sha256': data['source_sha256'], 'solver_revision': _solver_revision(),
                             'scope': 'page', 'page': payload.page, 'question_source': 'user_calibration'}}
    store.save_answer(answer_id, doc_id, result['question'], result)
    return result


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


def _source_revision():
    digest = hashlib.sha256()
    for name in ('app.py', 'native_qa.py', 'takeoff.py', 'native_query.py', 'schedule_planner.py', 'schedules.py', 'quantities.py', 'detector.py', 'extraction.py', 'selection.py', 'llm.py', 'costs.py', 'gemini_provider.py', 'inventory.py', 'verification.py', 'rendering.py', 'store.py', 'measurements.py', 'visual_audit.py', 'normalize.py', 'question_templates.json'):
        path = Path(__file__).parent / name
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:20]


@lru_cache(maxsize=1)
def _solver_revision():
    # A running process must never claim newly edited files are already loaded.
    return _source_revision()


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


def _native_region_context(data, source, page, region):
    """Bind a selection to objects registered to the exact displayed source."""
    if source.suffix.lower() in {'.ifc', '.dwg'}:
        return None
    views = rendering.visual_sources(source)
    if not views:
        return None
    visible = views[0].resolve()
    if source.suffix.lower() == '.dxf' and visible == source.resolve() and not data.get('metadata', {}).get('cad_projection_registered'):
        return None
    selected = []
    for obj in data.get('objects', []):
        if obj.get('page') != page:
            continue
        object_source = obj.get('source_path')
        if object_source:
            object_source = Path(str(object_source)).expanduser()
            if not object_source.is_absolute():
                object_source = store.DATA_ROOT / object_source
            if object_source.resolve() != visible:
                return None
        box = obj.get('bbox')
        if not box:
            # An unlocated source quantity might lie in the selection.
            from . import native_query
            if native_query.available({'objects':[obj]}):
                return None
            continue
        anchor = obj.get('properties', {}).get('preview_anchor') or [(box[0]+box[2])/2,(box[1]+box[3])/2]
        if region[0] <= anchor[0] <= region[2] and region[1] <= anchor[1] <= region[3]:
            selected.append(obj)
    pages = []
    for original in data.get('pages', []):
        if original.get('page') != page:
            continue
        words = [word for word in original.get('words', []) if word.get('bbox') and
                 region[0] <= (word['bbox'][0]+word['bbox'][2])/2 <= region[2] and
                 region[1] <= (word['bbox'][1]+word['bbox'][3])/2 <= region[3]]
        pages.append({**original,'words':words,'text':' '.join(word.get('text','') for word in words)})
    return {**data,'objects':selected,'pages':pages,
            'metadata':{**data.get('metadata', {}),'requested_scope':'region','selected_region':region}}


def _native_region_answer(question, data, source, page, region):
    """Resolve native queries only against geometry registered to this view.

    IFC object projections carry local page numbers from several separate
    views, so page=1 alone cannot resolve a selected model view. Standalone DXF
    geometry requires the exact placement transform from its preview renderer.
    """
    from . import inventory
    if source.suffix.lower() in {'.ifc', '.dwg'}:
        return None
    views = rendering.visual_sources(source)
    if not views:
        return None
    visible_source = views[0].resolve()
    if source.suffix.lower() == '.dxf' and visible_source == source.resolve() and not data.get('metadata', {}).get('cad_projection_registered'):
        return None
    category = inventory.count_category(question)
    if category is None:
        scoped = _native_region_context(data, source, page, region)
        if scoped is None:
            return None
        from .native_qa import answer_native
        return answer_native(question, scoped, source, store.DATA_ROOT)
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


def _rectangle_from_quoted_dimensions(result, question):
    """Recompute explicit rectangular dimensions instead of accepting model math."""
    if result.get('operation') != 'area' or not re.search(r'\brectang(?:le|ular)\b', question, re.I):
        return None
    from .verification import _text_candidates, normalized
    from .measurements import length_in_metres
    evidence = result.get('evidence') or []
    if not evidence or len({item.get('page', 1) for item in evidence}) != 1:
        return None
    quote = '\n'.join(str(item.get('quoted_text') or '') for item in evidence)
    # An explicit area reading remains the preferred source operand.
    if list(_text_candidates(quote, 'area')):
        return None
    role = next((role for role in ('net', 'gross') if re.search(r'\b' + role + r'\b', question, re.I)), None)
    if role and role not in normalized(quote):
        return None
    dimensions = list(_text_candidates(quote, 'length'))
    if len(dimensions) != 2:
        return None
    try:
        value = math.prod(length_in_metres(item['value'], item['unit']) for item in dimensions)
    except ValueError:
        return None
    revised = copy.deepcopy(result)
    revised.update(value=value, unit='m²', status='needs_review', needs_review=True,
                   answer=f'{value:g} m² for the stated rectangle, calculated from the two quoted dimensions. Check their source regions and the rectangular boundary.',
                   calculation=' × '.join(f"{item['value']:g} {item['unit']}" for item in dimensions) + f' = {value:g} m²',
                   measurement_basis='explicit_quoted_rectangle_dimensions')
    revised.setdefault('warnings', []).append('The rectangular shape was specified in the question; the quoted dimensions still require source review. No DPI or typical object size supplies the scale.')
    return revised


def _guard_visual_measurements(result, question=''):
    """Do not turn an unscaled image estimate into a measured quantity.

    Native verified operands remain usable. Unverified image readings require
    an explicit quoted quantity with compatible units; a guessed door width,
    image DPI or a scale inferred by the model cannot establish an area.
    Quoted image text still needs human review because OCR is not verification.
    """
    operation = result.get('operation')
    rectangular = _rectangle_from_quoted_dimensions(result, question)
    if rectangular is not None:
        return rectangular
    if operation not in {'area', 'length', 'volume'} or result.get('value') is None:
        return result
    evidence = result.get('evidence') or []
    from .verification import ground_native_evidence
    for item in evidence:
        if item.get('source_verified'):
            continue
        quote = str(item.get('quoted_text') or '').strip()
        checked, _ = ground_native_evidence({'id': 'visual-quote', 'text': quote}, item, operation)
        if not quote or checked.get('value') is None:
            result = copy.deepcopy(result)
            result.update(value=None, status='insufficient_evidence', needs_review=True,
                          answer='A measured quantity could not be established. Supply a readable printed quantity or dimensioned native source; image size and assumed door widths do not establish drawing scale.',
                          calculation=None, measurement_basis='unverified_scale_or_quantity')
            result.setdefault('warnings', []).append('The visual measurement lacked an explicit quoted source quantity with compatible units. No numeric measurement was accepted.')
            return result
    if not evidence:
        result = copy.deepcopy(result)
        result.update(value=None, status='insufficient_evidence', needs_review=True,
                      answer='No source quantity or calibrated measurement supports this result.', calculation=None)
    return result


def _compute_analysis(payload, question, data, source, previous=None):
    from .native_qa import answer_native
    from . import inventory
    english = to_english(question)
    normalized = english != question
    question = english
    result = None
    native_result = None
    native_data = data
    region_data = _native_region_context(data, source, payload.page, payload.region) if payload.region else None
    if payload.scope == 'page':
        native_data = {**data, 'metadata': {**data.get('metadata', {}), 'requested_scope': 'page'},
                       'pages': [p for p in data.get('pages', []) if p.get('page') == payload.page],
                       'objects': [o for o in data.get('objects', []) if o.get('page') == payload.page]}
        native_data['metadata']['schedule_tables'] = [t for t in data.get('metadata',{}).get('schedule_tables',[]) if t.get('page') == payload.page]
    if region_data is not None:
        native_data = region_data
    contextual = bool(previous and re.search(r'\b(those|these|their|them|that room|that space|same rooms?|previous|instead)\b', question, re.I))
    if payload.mode != 'vision' and not contextual:
        if payload.region:
            result = _native_region_answer(question, data, source, payload.page, payload.region)
        elif not (payload.scope == 'page' and source.suffix.lower() == '.ifc'):
            result = native_highlight(question, native_data, source, store.DATA_ROOT) if highlight_target(question) else answer_native(question, native_data, source, store.DATA_ROOT)
        if result is None and payload.mode == 'auto' and llm.model_available() and not normalized and re.search(r'[^\x00-\x7f]', question):
            try:
                translated = llm.translate_question(question)
                if translation_preserves_constraints(question, translated):
                    result = answer_native(translated, native_data, source, store.DATA_ROOT) if not payload.region else _native_region_answer(translated, data, source, payload.page, payload.region)
                    if result:
                        result['interpreted_question'] = translated
            except llm.ModelError:
                pass
        native_result = copy.deepcopy(result)
    if result is None and payload.mode != 'native' and (not payload.region or region_data is not None) and llm.model_available():
        # Schedule sheets: a model plans the table query, the program executes it over the cells.
        from . import schedule_planner
        if not contextual and not payload.region and schedule_planner.usable_tables(native_data):
            def _plan_cache_get(key):
                return store.cached_analysis(store.analysis_key('schedule_plan', {'plan': key, 'provider': llm.provider_signature()}))

            def _plan_cache_put(key, plan):
                store.save_analysis(store.analysis_key('schedule_plan', {'plan': key, 'provider': llm.provider_signature()}), 'schedule_plan', plan)
            try:
                result = schedule_planner.answer(question, native_data, request=llm._request, cache=(_plan_cache_get, _plan_cache_put))
            except llm.ModelError:
                result = None
        if result is None:
            from . import native_query
            def _native_plan_get(key):
                return store.cached_analysis(store.analysis_key('native_query', {'plan':key,'provider':llm.provider_signature()}))
            def _native_plan_put(key, plan):
                store.save_analysis(store.analysis_key('native_query', {'plan':key,'provider':llm.provider_signature()}), 'native_query', plan)
            try:
                result = native_query.answer(question, native_data, request=llm._request, cache=(_native_plan_get,_native_plan_put), previous=previous if contextual else None)
            except llm.ModelError:
                result = None
    if result is None and contextual:
        result = {'answer':'Do you mean the objects from the previous answer, or every matching object in the current selection?',
                  'value':None,'unit':None,'method':'context_clarification','status':'needs_clarification',
                  'evidence':[],'can_review':False,'warnings':[]}
    if result is None and payload.mode != 'native':
        try:
            result = inventory.answer_inventory(question, data, source, payload.page, payload.scope, payload.region)
            if result is None:
                result = llm.answer_with_model(question, data, source, payload.page, payload.scope, payload.region)
            result = _guard_visual_measurements(result, question)
            if payload.verify_visual:
                from .visual_audit import audit_visual_count
                result = audit_visual_count(question, result, data, source, payload.page, payload.scope, payload.region)
        except llm.ModelError as exc:
            raise HTTPException(503, str(exc)) from None
        except (ValueError, OSError):
            raise HTTPException(422, 'This source has no usable visual preview. Native source tools remain available.') from None
    if result is None:
        result = {'answer': 'The native source tools could not establish this answer. Use automatic analysis to inspect the drawing, or choose a question supported by its native records.',
                  'value': None, 'unit': None, 'method': 'native', 'status': 'insufficient_evidence', 'evidence': [], 'warnings': [], 'scope': payload.scope}
    if payload.cross_check:
        result['reconciliation'] = _cross_check(payload, question, native_result, data, source)
    if normalized:
        result.setdefault('interpreted_question', english)
    return result


@app.post('/api/ask')
def ask(payload: AskRequest):
    message_id = uuid.uuid4().hex
    session_id = str(payload.session_id) if payload.session_id else None
    store.record_message_usage(session_id, message_id, {}, payload.question, 'pending')
    with llm.usage_scope(session_id=session_id, message_id=message_id):
        try:
            result = _ask_question(payload, message_id)
        except HTTPException as exc:
            usage = llm.usage_snapshot()
            store.record_message_usage(session_id, message_id, usage, payload.question, 'error')
            detail = exc.detail.get('message', 'The question could not be completed.') if isinstance(exc.detail, dict) else str(exc.detail)
            raise HTTPException(exc.status_code, {'message': detail, 'usage': usage,
                                'message_id': message_id, 'session_id': session_id}, headers=exc.headers) from None
        except Exception as exc:
            usage = llm.usage_snapshot()
            store.record_message_usage(session_id, message_id, usage, payload.question, 'error')
            store.record_event('question_error', {'message_id': message_id, 'error_type': type(exc).__name__})
            raise HTTPException(500, {'message': 'The question could not be completed. Try again.',
                                'usage': usage, 'message_id': message_id, 'session_id': session_id}) from None
        store.record_message_usage(session_id, message_id, result['usage'], payload.question,
                                   'completed', answer_id=result['id'])
        return result


def _ask_question(payload: AskRequest, answer_id: str):
    started = time.monotonic()
    if _solver_revision() != _source_revision():
        raise HTTPException(503, 'The backend is still running the previous code. Restart the local server to finish loading this update.')
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
    previous = None
    if payload.previous_answer_id:
        try:
            candidate = store.read_answer(payload.previous_answer_id)
        except KeyError:
            raise HTTPException(409, 'The previous answer is unavailable. Ask again without referring to it.') from None
        context = candidate.get('request_context') or {}
        if candidate.get('document_id') != doc['id'] or candidate.get('provenance',{}).get('source_fingerprint') != data.get('source_fingerprint'):
            raise HTTPException(409, 'The previous answer belongs to a different or changed drawing.')
        # A changed region is a fresh selection. Never carry IDs from another scope.
        if context.get('page',1) == payload.page and context.get('region') == payload.region and context.get('scope','document') == payload.scope:
            previous = candidate
    canonical_question = to_english(question)
    from .inventory import config_signature
    from .visual_audit import config_signature as audit_signature
    key = store.analysis_key('answer', {'document': doc['id'], 'source': data.get('source_fingerprint'),
                            'extractor': data.get('extractor_revision'), 'solver': _solver_revision(),
                            'model': llm.provider_signature(), 'inventory': config_signature(),
                            'audit': audit_signature() if payload.verify_visual else None,
                            'prompt': llm.PROMPT_REVISION, 'question': canonical_question,
                            'page': payload.page, 'scope': payload.scope, 'region': payload.region,
                            'mode': payload.mode, 'cross_check': payload.cross_check, 'verify_visual': payload.verify_visual})
    if previous:
        key = store.analysis_key('contextual_answer', {'base':key,'previous':previous['id'],
                                 'review_revision':(previous.get('review') or {}).get('revision',0)})
    with store.key_lock('answer:' + key):
        result = store.cached_analysis(key)
        hit = result is not None
        if hit:
            result['cached_analysis_usage'] = result.get('usage', {})
        else:
            result = _compute_analysis(payload, question, data, source, previous=previous)
            result['usage'] = llm.usage_snapshot()
            store.save_analysis(key, 'answer', result)
    result['usage'] = llm.usage_snapshot(cache_hit=hit)
    result = _evidence(result, payload.document_id)
    if canonical_question != question:
        result['interpreted_question'] = canonical_question
    elif result.get('interpreted_question') == question:
        result.pop('interpreted_question', None)
    if highlight_target(to_english(question)):
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
        from .inventory import answer_category, categories_for_count
        result.setdefault('category', answer_category(to_english(question), result))
        result['allowed_count_categories'] = list(categories_for_count(result.get('category')))
    result['usage']['inventory_cache_hit'] = bool(result.get('inventory_cache_hit'))
    result.setdefault('can_review', result['operation'] == 'count' and result.get('value') is not None and result.get('value') == len(result['evidence']))
    result['question'] = payload.question
    result['document_id'] = doc['id']
    result['document'] = doc
    result['id'] = answer_id
    result['message_id'] = answer_id
    result['duration_ms'] = round((time.monotonic() - started) * 1000)
    result['attribution'] = store.attribution(doc)
    result['request_context'] = {'document_id': doc['id'], 'scope': payload.scope, 'page': payload.page, 'region': payload.region}
    result['provenance'] = {'source_path': doc['path'], 'source_sha256': data.get('source_sha256'),
                            'source_fingerprint': data.get('source_fingerprint'), 'extractor_revision': data.get('extractor_revision'),
                            'solver_revision': _solver_revision(), 'file_size': doc['size'], 'file_modified': doc['mtime'],
                            'scope': payload.scope, 'page': payload.page, 'region': payload.region, 'question_source': 'user'}
    store.save_answer(result['id'], doc['id'], payload.question, result)
    return result


def _answer_view(result, fingerprints=None):
    """Decorate history with current-source status without rewriting its record."""
    answer = copy.deepcopy(result)
    expected = answer.get('provenance', {}).get('source_fingerprint')
    if not expected:
        answer.update(source_changed=False, source_status='untracked')
        return answer
    doc_id = answer.get('document_id')
    fingerprints = fingerprints if fingerprints is not None else {}
    if doc_id not in fingerprints:
        try:
            fingerprints[doc_id] = store.source_fingerprint(doc_id)
        except (KeyError, OSError, ValueError):
            fingerprints[doc_id] = None
    current = fingerprints[doc_id]
    changed = current != expected
    answer.update(source_changed=changed, source_status='unavailable' if current is None else ('changed' if changed else 'current'))
    if changed:
        answer['can_review'] = False
        answer['status'] = 'needs_review'
        answer['warnings'] = list(dict.fromkeys(answer.get('warnings', []) + ['The source or a linked drawing changed after this answer. Its old locations and quantities need a new analysis before review.']))
        if answer.get('working_quantity'):
            answer['working_quantity'] = {**answer['working_quantity'], 'source_changed': True}
    return answer


class ResolutionRequest(BaseModel):
    choice: Literal['native', 'comparison']
    note: str = Field(min_length=3, max_length=4000)


@app.post('/api/answers/{answer_id}/resolution')
def resolve_answer(answer_id: str, payload: ResolutionRequest):
    """Save an explicit human working quantity; retain every machine result."""
    note = payload.note.strip()
    if len(note) < 3:
        raise HTTPException(422, 'Explain the working quantity choice in at least three characters.')
    with store.key_lock('review:' + answer_id):
        try:
            current = store.read_answer(answer_id)
        except KeyError:
            raise HTTPException(404, 'Answer not found') from None
        if _answer_view(current).get('source_changed'):
            raise HTTPException(409, 'The source changed. Run a new analysis before selecting a working quantity.')
        comparison = current.get('reconciliation') or {}
        if comparison.get('status') not in {'agreement', 'disagreement'}:
            raise HTTPException(422, 'Only comparable source quantities can be resolved.')
        from .verification import convert_quantity, unit_spec, finite_number
        unit = comparison.get('unit')
        if not unit_spec(unit):
            raise HTTPException(422, 'The comparison has no supported quantity unit.')
        answer_unit = unit_spec(current.get('unit'))
        if answer_unit and answer_unit[0] != unit_spec(unit)[0]:
            raise HTTPException(422, 'The comparison quantity is incompatible with the answer quantity.')
        native_value, compared_value = comparison.get('native_value'), comparison.get('visual_value')
        native_unit = comparison.get('native_unit') or unit
        compared_unit = comparison.get('comparison_unit') or comparison.get('visual_unit') or unit
        if not finite_number(native_value) or not finite_number(compared_value):
            raise HTTPException(422, 'Both compared source quantities must be finite and nonnegative.')
        native = convert_quantity(native_value, native_unit, unit)
        compared = convert_quantity(compared_value, compared_unit, unit)
        if native is None or compared is None:
            raise HTTPException(422, 'Compared quantities must have compatible dimensions and units.')
        if unit_spec(unit)[0] == 'count' and any(not float(value).is_integer() for value in (native, compared)):
            raise HTTPException(422, 'Compared object counts must be exact whole numbers.')
        selected_value = native if payload.choice == 'native' else compared
        if unit_spec(unit)[0] == 'count':
            selected_value = int(selected_value)
        label = comparison.get('native_label') if payload.choice == 'native' else comparison.get('visual_label')
        working = {'value': selected_value, 'unit': unit, 'selected_source': payload.choice,
                   'source_label': label or ('Native source' if payload.choice == 'native' else 'Compared source'),
                   'note': note, 'reviewed_at': datetime.now(timezone.utc).isoformat()}
        history = list(current.get('resolution_history', []))
        history.append({**working, 'revision': len(history) + 1,
                        'comparison_snapshot': copy.deepcopy(comparison)})
        result = {**current, 'working_quantity': working, 'resolution_history': history, 'human_reviewed': True}
        result.pop('resolution_superseded', None)
        result['warnings'] = list(dict.fromkeys(current.get('warnings', []) + ['The working quantity is a recorded human judgment; it does not independently verify either source or detection completeness.']))
        store.update_answer(answer_id, result)
    return _answer_view(result)


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
    base_revision: int | None = Field(default=None, ge=0)


@app.post('/api/answers/{answer_id}/review')
def review_answer(answer_id: str, payload: ReviewRequest):
    with store.key_lock('review:' + answer_id):
        try:
            original = store.read_answer(answer_id, original=True)
            current = store.read_answer(answer_id)
        except KeyError:
            raise HTTPException(404, 'Answer not found') from None
        if _answer_view(original).get('source_changed'):
            raise HTTPException(409, 'The source changed. Run a new analysis before correcting its count.')
        if not original.get('can_review'):
            raise HTTPException(422, 'This answer does not support count corrections.')
        if payload.base_revision is not None and payload.base_revision != int((current.get('review') or {}).get('revision',0)):
            raise HTTPException(409, 'This review changed in another tab. Reopen the answer before saving your correction.')
        original_evidence = copy.deepcopy(original.get('evidence', []))
        ids = {e['id'] for e in original_evidence}
        allowed_documents = {original['document_id']} | {e.get('document_id', original['document_id']) for e in original_evidence}
        from .inventory import answer_category, canonical_category, categories_for_count
        expected_category = canonical_category(original.get('category') or answer_category(original.get('question', ''), original))
        allowed_categories = categories_for_count(expected_category) or ((expected_category,) if expected_category else ())
        added = []
        for item in payload.added_evidence:
            box = item.bbox
            if not item.label.strip():
                raise HTTPException(422, 'A manually added object needs a meaningful label.')
            category = canonical_category(item.category) if item.category else (allowed_categories[0] if len(allowed_categories) == 1 else 'manual_object')
            if allowed_categories and category not in allowed_categories:
                raise HTTPException(422, 'A manual addition must use one of the counted categories: ' + ', '.join(allowed_categories) + '.')
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
        result['resolution_history'] = copy.deepcopy(current.get('resolution_history', []))
        if reviewed_value != current.get('value') and current.get('working_quantity'):
            result['working_quantity'] = None
            result['resolution_superseded'] = {'reason': 'The object count changed after this working quantity was selected. Choose a working quantity again after inspecting the revised evidence.',
                                               'reviewed_at': review['reviewed_at'],
                                               'previous_working_quantity': copy.deepcopy(current['working_quantity'])}
        elif current.get('working_quantity'):
            result['working_quantity'] = copy.deepcopy(current['working_quantity'])
        elif current.get('resolution_superseded'):
            result['working_quantity'] = None
            result['resolution_superseded'] = copy.deepcopy(current['resolution_superseded'])
        noun = expected_category.replace('_',' ') if expected_category and '+' not in expected_category else 'object'
        if reviewed_value != 1 and not noun.endswith('s'):
            noun += 's'
        result['answer'] = f'{reviewed_value} {noun} after your review.'
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
            'original_evidence': original.get('evidence', []), 'revisions': current.get('review_history', []),
            'resolution_history': current.get('resolution_history', []),
            'working_quantity': _answer_view(current).get('working_quantity'),
            'resolution_superseded': current.get('resolution_superseded')}


@app.get('/api/answers/{answer_id}')
def answer_detail(answer_id: str, original: bool = False):
    try:
        return _answer_view(store.read_answer(answer_id, original=original))
    except KeyError:
        raise HTTPException(404, 'Answer not found') from None


@app.get('/api/answers/{answer_id}/export')
def export_answer(answer_id: str, format: Literal['json','csv'] = 'json'):
    from .receipts import receipt, csv_receipt
    try:
        result = _answer_view(store.read_answer(answer_id))
    except KeyError:
        raise HTTPException(404, 'Answer not found') from None
    exported = receipt(result)
    content = csv_receipt(exported) if format == 'csv' else json.dumps(exported,ensure_ascii=False,indent=2)
    return Response(content,media_type='text/csv' if format=='csv' else 'application/json',
                    headers={'Content-Disposition':f'attachment; filename="metria-{result["id"]}-r{exported["export_revision"]}.{format}"'})


@app.get('/api/answers')
def recent_answers(limit: int = 12):
    fingerprints = {}
    return {'answers': [_answer_view(answer, fingerprints) for answer in store.list_answers(max(1, min(limit, 50)))]}


class ChatCreate(BaseModel):
    session_id: uuid.UUID | None = None
    name: str = Field(min_length=1,max_length=160)
    project_id: str | None = None
    document_id: str | None = None

class ChatUpdate(BaseModel):
    title: str | None = Field(default=None,min_length=1,max_length=160)
    project_id: str | None = None
    document_id: str | None = None

@app.get('/api/workspace/chats')
@app.get('/api/chats')
def chats():
    return store.chat_workspace()

@app.post('/api/workspace/projects')
@app.post('/api/chat-projects')
def create_project(payload: ChatCreate):
    identity=store.create_chat(payload.name.strip() or 'Untitled project',project=True,identity=str(payload.session_id) if payload.session_id else None)
    return {'id':identity, 'project':store.get_chat_project(identity)}

class DrawingAttachment(BaseModel):
    session_id: uuid.UUID
    next_session_id: uuid.UUID
    document_id: str = Field(min_length=1, max_length=100)

@app.post('/api/workspace/attachments')
def attach_drawing(payload: DrawingAttachment):
    try:
        thread = store.attach_chat_drawing(str(payload.session_id), payload.document_id, str(payload.next_session_id))
    except KeyError:
        raise HTTPException(404, 'Drawing not found. Upload it again or select it from Dataset.') from None
    except ValueError:
        raise HTTPException(409, 'This chat identity belongs to another drawing.') from None
    return {'thread':thread}

@app.post('/api/workspace/chats')
@app.post('/api/chats')
def create_chat(payload: ChatCreate):
    try:
        identity=store.create_chat(payload.name.strip() or 'New chat',payload.project_id,payload.document_id,identity=str(payload.session_id) if payload.session_id else None)
    except KeyError:
        raise HTTPException(404,'Project or drawing not found') from None
    return {'id':identity, 'thread':store.get_chat(identity)}

class ThreadAnswer(BaseModel):
    answer_id: str

@app.post('/api/workspace/chats/{identity}/answers')
@app.post('/api/chats/{identity}/answers')
def remember_chat_answer(identity: str,payload: ThreadAnswer):
    workspace=store.chat_workspace()
    if not any(t['id']==identity for t in workspace['threads']): raise HTTPException(404,'Chat not found')
    try: answer=store.read_answer(payload.answer_id)
    except KeyError: raise HTTPException(404,'Answer not found') from None
    with store.connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS chat_thread_answers(thread_id TEXT,answer_id TEXT,PRIMARY KEY(thread_id,answer_id))')
        inserted=db.execute('INSERT OR IGNORE INTO chat_thread_answers VALUES(?,?)',(identity,payload.answer_id)).rowcount
    if inserted: store.record_message_usage(identity,'saved:'+payload.answer_id,answer.get('usage'),answer.get('question','Measurement'),'completed',payload.answer_id)
    return {'status':'ok'}

@app.patch('/api/workspace/chats/{identity}')
@app.patch('/api/chats/{identity}')
def update_chat(identity: str,payload: ChatUpdate):
    try:
        store.update_chat(identity,payload.title,payload.project_id,payload.document_id)
    except KeyError:
        raise HTTPException(404,'Chat, project or drawing not found') from None
    return {'status':'ok', 'thread':store.get_chat(identity)}

DIST = ROOT / 'frontend' / 'dist'
if DIST.exists():
    app.mount('/', StaticFiles(directory=DIST, html=True), name='workspace')

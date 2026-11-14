"""Optional, protected source-region close-ups using Cloudinary.

Only an explicit close-up request uploads a canonical rendered page. Inference
inputs, coordinates, answers and model-request accounting are never modified.
Cloudinary stores the page as authenticated media; the browser sees only a
workspace-protected local image route, never a signed Cloudinary capability.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import threading
from urllib.parse import unquote, urlsplit

REVISION = 'cloudinary-closeup-v1'
PRESET = 'trace-evidence-pages'
MAX_IMAGE_BYTES = 24 * 1024 * 1024
MAX_OUTPUT_EDGE = 1000
_sdk_lock = threading.Lock()


class MediaError(Exception):
    def __init__(self, message, status=503):
        self.status = status
        super().__init__(message)


@dataclass(frozen=True)
class Credentials:
    cloud_name: str
    api_key: str = field(repr=False)
    api_secret: str = field(repr=False)

    def options(self):
        return {'cloud_name': self.cloud_name, 'api_key': self.api_key,
                'api_secret': self.api_secret, 'secure': True,
                'upload_prefix': 'https://api.cloudinary.com'}

    def identity(self):
        return hashlib.sha256((self.cloud_name + ':' + self.api_key).encode()).hexdigest()


def credentials():
    raw = os.environ.get('CLOUDINARY_URL', '')
    try:
        uri = urlsplit(raw)
        cloud = uri.hostname or ''
        key, secret = unquote(uri.username or ''), unquote(uri.password or '')
        if (len(raw) > 4096 or uri.scheme != 'cloudinary' or uri.port is not None
                or uri.query or uri.fragment or uri.path not in ('', '/')
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', cloud)
                or not key or not secret or len(key) > 256 or len(secret) > 1024
                or any(ord(c) < 33 or ord(c) == 127 for c in key + secret)):
            raise ValueError
    except (ValueError, TypeError):
        raise MediaError('Cloudinary evidence close-ups are not configured.') from None
    return Credentials(cloud, key, secret)


def available():
    try:
        credentials()
        return importlib.util.find_spec('cloudinary') is not None
    except (MediaError, ImportError, ValueError):
        return False


class _NoReplayTransport:
    """The pinned SDK has no per-call retry/redirect controls for uploads."""
    def __init__(self, transport):
        self.transport = transport

    def request(self, *args, **kwargs):
        kwargs.update(retries=False, redirect=False)
        return self.transport.request(*args, **kwargs)


def _sdk():
    try:
        uploader = importlib.import_module('cloudinary.uploader')
        utils = importlib.import_module('cloudinary.utils')
        api_transport = importlib.import_module('cloudinary.api_client.call_api')
        with _sdk_lock:
            for module in (uploader, api_transport):
                if not isinstance(module._http, _NoReplayTransport):
                    module._http = _NoReplayTransport(module._http)
        return uploader, utils
    except ImportError:
        raise MediaError('Cloudinary evidence close-ups are unavailable on this server.') from None


def _box(item):
    box = item.get('bbox')
    if box is None and item.get('polygon'):
        points = item['polygon']
        if (not isinstance(points, list) or not 3 <= len(points) <= 10000
                or any(not isinstance(p, (list, tuple)) or len(p) != 2
                       or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in p)
                       for p in points)):
            raise MediaError('This source item has no usable drawing location.', 422)
        box = [min(p[0] for p in points), min(p[1] for p in points),
               max(p[0] for p in points), max(p[1] for p in points)]
    if (not isinstance(box, (list, tuple)) or len(box) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in box)
            or box[0] >= box[2] or box[1] >= box[3]):
        raise MediaError('This source item has no usable drawing location.', 422)
    return list(box)


def _source(answer_id, evidence_id):
    from . import store
    try:
        answer = store.read_answer(answer_id)
    except KeyError:
        raise MediaError('Answer not found.', 404) from None
    expected = (answer.get('provenance') or {}).get('source_fingerprint')
    try:
        current = store.source_fingerprint(answer['document_id'])
    except (KeyError, OSError, ValueError):
        current = None
    if not expected or current != expected:
        raise MediaError('The source changed or is untracked. Run a new analysis before opening a close-up.', 409)
    items = [*answer.get('evidence', []), *answer.get('original_evidence', []), *answer.get('added_evidence', [])]
    item = next((row for row in items if row.get('id') is not None and str(row['id']) == evidence_id), None)
    if item is None:
        raise MediaError('Source item not found.', 404)
    box = _box(item)
    doc_id = item.get('document_id') or answer['document_id']
    page = item.get('page', 1)
    if type(page) is not int or page < 1:
        raise MediaError('This source item references an unavailable page.', 422)
    try:
        path = store.get_path(doc_id)
        fingerprint = store.source_fingerprint(doc_id)
    except (KeyError, OSError, ValueError):
        raise MediaError('The linked drawing is unavailable.', 422) from None
    return {'answer_id': answer_id, 'evidence_id': evidence_id, 'document_id': doc_id,
            'page': page, 'bbox': box, 'fingerprint': fingerprint, 'path': path}


def crop_geometry(box, width, height):
    # Add a little page context; never shift focus using saliency or generation.
    xpad, ypad = max((box[2] - box[0]) * .2, .005), max((box[3] - box[1]) * .2, .005)
    left, top = max(0, math.floor((box[0] - xpad) * width)), max(0, math.floor((box[1] - ypad) * height))
    right, bottom = min(width, math.ceil((box[2] + xpad) * width)), min(height, math.ceil((box[3] + ypad) * height))
    cw, ch = right - left, bottom - top
    output_width = max(1, round(cw * min(4, MAX_OUTPUT_EDGE / max(cw, ch))))
    transform = [{'crop': 'crop', 'gravity': 'north_west', 'x': left, 'y': top, 'width': cw, 'height': ch},
                 {'crop': 'scale', 'width': output_width}, {'fetch_format': 'png'}]
    return transform, [left / width, top / height, right / width, bottom / height]


def _download(url, cred):
    import httpx
    from PIL import Image
    parsed = urlsplit(url)
    prefix = '/' + cred.cloud_name + '/image/authenticated/'
    if (parsed.scheme != 'https' or parsed.netloc != 'res.cloudinary.com'
            or not parsed.path.startswith(prefix) or '/s--' not in parsed.path
            or parsed.query or parsed.fragment):
        raise MediaError('Cloudinary returned an unsupported protected delivery location.')
    try:
        with httpx.Client(follow_redirects=False, timeout=45, trust_env=False) as client:
            with client.stream('GET', url) as response:
                if response.status_code != 200:
                    raise MediaError('Cloudinary could not deliver this protected close-up.')
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_IMAGE_BYTES:
                        raise MediaError('The close-up exceeds the image delivery limit.')
        with Image.open(io.BytesIO(content)) as image:
            if image.format != 'PNG' or max(image.size) > MAX_OUTPUT_EDGE + 1:
                raise MediaError('Cloudinary returned an unsupported close-up image.')
            image.load()
            size = image.size
        return bytes(content), size
    except MediaError:
        raise
    except Exception:
        raise MediaError('Cloudinary close-up delivery failed. The request was not retried.') from None


def create_closeup(answer_id, evidence_id):
    from . import rendering, store
    cred = credentials()
    uploader, utils = _sdk()
    source = _source(answer_id, evidence_id)
    folder = store.RUNTIME / 'media'
    folder.mkdir(exist_ok=True)
    identity = {k: v for k, v in source.items() if k != 'path'}
    token = hashlib.sha256(json.dumps([REVISION, cred.identity(), identity], sort_keys=True).encode()).hexdigest()
    target = folder / (token + '.png')
    with store.key_lock('cloudinary-closeup:' + token):
        cached = store.cached_analysis(token)
        if cached and target.is_file():
            return {k: cached[k] for k in ('image_url', 'width', 'height', 'source_region', 'provider')} | {'cache_hit': True}
        try:
            image, _ = rendering.render_page(source['path'], source['page'], 4000)
            width, height = image.size
            png = rendering.png_bytes(image)
        except Exception:
            raise MediaError('No two-dimensional preview is available for this source item.', 422) from None
        if len(png) > MAX_IMAGE_BYTES:
            raise MediaError('The rendered page exceeds the media upload limit.', 422)
        page_key = hashlib.sha256((cred.identity() + hashlib.sha256(png).hexdigest()).encode()).hexdigest()
        public_id = 'trace-evidence/' + page_key
        options = cred.options()
        try:
            with store.key_lock('cloudinary-page:' + page_key):
                page_asset = store.cached_analysis('cloudinary-page:' + page_key)
                if not page_asset:
                    uploaded = uploader.upload(io.BytesIO(png), resource_type='image', type='authenticated',
                        public_id=public_id, overwrite=False,
                        upload_preset=os.environ.get('STOA_CLOUDINARY_UPLOAD_PRESET', PRESET),
                        allowed_formats=['png'], timeout=60, **options)
                    if (uploaded.get('type') != 'authenticated' or uploaded.get('public_id') != public_id
                            or uploaded.get('width') != width or uploaded.get('height') != height
                            or type(uploaded.get('version')) is not int):
                        raise MediaError('Cloudinary did not preserve the protected source page.')
                    page_asset = {'public_id': public_id, 'version': uploaded['version']}
                    store.save_analysis('cloudinary-page:' + page_key, 'cloudinary_page', page_asset)
            transform, region = crop_geometry(source['bbox'], width, height)
            # Authenticated media requires pre-generated derived assets.
            uploader.explicit(public_id, resource_type='image', type='authenticated',
                              eager=[{'transformation': transform, 'format': 'png'}], timeout=60, **options)
            url, _ = utils.cloudinary_url(public_id, resource_type='image', type='authenticated',
                version=page_asset['version'], transformation=transform, format='png',
                sign_url=True, secure_distribution='res.cloudinary.com', private_cdn=False,
                cdn_subdomain=False, secure_cdn_subdomain=False, **options)
            content, (out_w, out_h) = _download(url, cred)
        except MediaError:
            raise
        except Exception:
            raise MediaError('Cloudinary close-up creation failed. The request was not retried.') from None
        # Recheck after the external calls so a changed source cannot acquire a current result.
        if {k: v for k, v in _source(answer_id, evidence_id).items() if k != 'path'} != identity:
            raise MediaError('The source item changed while creating its close-up. Open the current answer again.', 409)
        staging = target.with_suffix('.tmp')
        staging.write_bytes(content)
        staging.replace(target)
        result = {'image_url': '/api/media/' + token + '.png', 'width': out_w, 'height': out_h,
                  'source_region': region, 'provider': 'cloudinary', 'binding': identity}
        store.save_analysis(token, 'cloudinary_closeup', result)
        return {k: result[k] for k in ('image_url', 'width', 'height', 'source_region', 'provider')} | {'cache_hit': False}


def media_path(token):
    from . import store
    if not re.fullmatch(r'[a-f0-9]{64}', token):
        raise MediaError('Close-up not found.', 404)
    cached = store.cached_analysis(token)
    path = store.RUNTIME / 'media' / (token + '.png')
    if not cached or not path.is_file() or 'binding' not in cached:
        raise MediaError('Close-up not found.', 404)
    old = cached['binding']
    current = {k: v for k, v in _source(old['answer_id'], old['evidence_id']).items() if k != 'path'}
    if old != current:
        raise MediaError('This close-up belongs to an older source item.', 409)
    return path

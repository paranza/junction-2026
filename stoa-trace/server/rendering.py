from __future__ import annotations

import io
import os
import re
from pathlib import Path
from functools import lru_cache

import pymupdf
from PIL import Image, ImageOps

# Optional enlarged overlapping crops for small plans. The active setting belongs
# in both inventory and answer cache keys so changing it triggers fresh analysis.
SMALL_IMAGE_CROPS = os.environ.get('STOA_SMALL_IMAGE_CROPS', '1') == '1'


RASTER_SUFFIXES = frozenset({'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tif', '.tiff'})
RASTER_ENCODINGS = frozenset({'PNG', 'JPEG', 'WEBP', 'BMP', 'GIF', 'TIFF'})
MAX_RASTER_BYTES = 120 * 1024 * 1024
MAX_RASTER_PIXELS = 100_000_000
MAX_RASTER_PAGES = 200


def _raster_limits(path, image):
    if path.stat().st_size > MAX_RASTER_BYTES:
        raise ValueError('Image exceeds the 120 MB processing size limit')
    if image.width <= 0 or image.height <= 0 or image.width * image.height > MAX_RASTER_PIXELS:
        raise ValueError('Image exceeds the processing pixel limit')


def _raster_frame_count(path, image):
    if image.format not in RASTER_ENCODINGS:
        raise ValueError('Unsupported image encoding; export to PNG, JPEG, WebP, BMP, GIF or TIFF')
    # Animations are not drawing-page sequences. A GIF/WebP overview is always
    # the first frame, while TIFF explicitly represents a stack of scan pages.
    count = getattr(image, 'n_frames', 1)
    if image.format == 'TIFF':
        if count > MAX_RASTER_PAGES:
            raise ValueError(f'TIFF exceeds the {MAX_RASTER_PAGES}-page processing limit')
        return count
    return 1


def raster_metadata(path: Path):
    """Describe the same oriented pages the drawing renderer will show."""
    path = Path(path)
    if path.stat().st_size > MAX_RASTER_BYTES:
        raise ValueError('Image exceeds the 120 MB processing size limit')
    pages, warnings = [], []
    with Image.open(path) as image:
        count = _raster_frame_count(path, image)
        frames = getattr(image, 'n_frames', 1)
        if image.format == 'GIF' or (frames > 1 and count == 1):
            warnings.append(f'Only the first frame of this {image.format or "animated image"} is analyzed; animation frames are not separate drawing pages.')
        for index in range(count):
            image.seek(index)
            _raster_limits(path, image)
            width, height = image.size
            # Pillow's TIFF decoder already advertises its oriented size.
            # JPEG/PNG/WebP retain the encoded dimensions until transposed.
            if image.format != 'TIFF' and image.getexif().get(274) in {5, 6, 7, 8}:
                width, height = height, width
            pages.append({'page': index + 1, 'width': width, 'height': height,
                          'text': '', 'words': []})
    return pages, warnings


def _raster_page(path: Path, page: int, max_edge: int):
    if path.stat().st_size > MAX_RASTER_BYTES:
        raise ValueError('Image exceeds the 120 MB processing size limit')
    with Image.open(path) as image:
        count = _raster_frame_count(path, image)
        if page > count:
            raise ValueError('Drawing page is unavailable')
        image.seek(page - 1)
        _raster_limits(path, image)
        image = ImageOps.exif_transpose(image)
        if image.mode in {'RGBA', 'LA'} or 'transparency' in image.info:
            rgba = image.convert('RGBA')
            normalized = Image.new('RGB', rgba.size, 'white')
            normalized.paste(rgba, mask=rgba.getchannel('A'))
        else:
            normalized = image.convert('RGB')
        normalized.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        return normalized.copy()


def natural_key(path):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', str(path))]


def visual_sources(path: Path):
    suffix = path.suffix.lower()
    if suffix == '.ifc':
        choices = {}
        for ext in ('.svg', '.png', '.pdf'):
            for p in path.parent.glob(path.stem + '_*' + ext):
                choices[p.stem] = p
        return sorted(choices.values(), key=natural_key)
    if suffix in {'.dxf', '.dwg'}:
        for ext in ('.pdf', '.png', '.svg', '.jpg'):
            p = path.with_suffix(ext)
            if p.exists():
                return [p]
    return [path] if suffix != '.ifc' else []


@lru_cache(maxsize=4)
def _dxf_render(path, mtime_ns, size):
    """Return the exact PDF and WCS-to-normalized-page transform used by its renderer."""
    import ezdxf
    from ezdxf.addons.drawing import Frontend, RenderContext, layout, config
    from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend, get_coordinate_output_space
    cad = ezdxf.readfile(path)
    backend = PyMuPdfBackend()
    cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE)
    Frontend(RenderContext(cad), backend, config=cfg).draw_layout(cad.modelspace(), finalize=True)
    settings = layout.Settings()
    # Mirror the first get_replay() placement, before that call transforms its recordings.
    output_layout = layout.Layout(backend.player().bbox(), flip_y=True)
    page = output_layout.get_final_page(layout.Page(0, 0), settings)
    settings.output_coordinate_space = get_coordinate_output_space(page)
    matrix = output_layout.get_placement_matrix(page, settings=settings, top_origin=True)
    origin = matrix.transform((0, 0, 0))
    x_axis = matrix.transform((1, 0, 0))
    y_axis = matrix.transform((0, 1, 0))
    pdf = backend.get_pdf_bytes(layout.Page(0, 0))
    with pymupdf.open(stream=pdf, filetype='pdf') as document:
        width, height = document[0].rect.width, document[0].rect.height
    if width <= 0 or height <= 0:
        raise ValueError('Invalid CAD preview dimensions')
    transform = [(x_axis.x-origin.x)/width, (y_axis.x-origin.x)/width, origin.x/width,
                 (x_axis.y-origin.y)/height, (y_axis.y-origin.y)/height, origin.y/height]
    return pdf, transform


def dxf_render(path):
    from . import native_worker
    if not native_worker.in_worker():
        import base64
        result=native_worker.call("dxf",path=str(Path(path).resolve()))
        return base64.b64decode(result["pdf"]),result["transform"]
    path = Path(path).resolve()
    stat = path.stat()
    return _dxf_render(str(path), stat.st_mtime_ns, stat.st_size)


def render_page(path: Path, page=1, max_edge=2400):
    path=Path(path)
    from . import native_worker
    if path.suffix.lower() not in RASTER_SUFFIXES and not native_worker.in_worker():
        import base64
        result=native_worker.call("render",path=str(path.resolve()),page=page,max_edge=max_edge)
        with Image.open(io.BytesIO(base64.b64decode(result["png"]))) as image:
            return image.copy(),Path(result["source"])
    if page < 1:
        raise ValueError('Page numbers begin at 1')
    sources = visual_sources(path)
    if not sources:
        raise ValueError('No linked two-dimensional drawing is available for this model')
    if path.suffix.lower() == '.ifc':
        if page > len(sources):
            raise ValueError('Drawing page is unavailable')
        source, source_page = sources[page - 1], 1
    else:
        source, source_page = sources[0], page
    suffix = source.suffix.lower()
    if suffix in RASTER_SUFFIXES:
        return _raster_page(source, source_page, max_edge), source
    if suffix in {'.pdf', '.svg'}:
        with pymupdf.open(source) as doc:
            if source_page > len(doc):
                raise ValueError('Drawing page is unavailable')
            p = doc[source_page - 1]
            scale = min(max_edge / max(p.rect.width, p.rect.height), 5)
            pix = p.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            return Image.frombytes('RGB', (pix.width, pix.height), pix.samples), source
    if suffix == '.dxf':
        pdf, _ = dxf_render(source)
        with pymupdf.open(stream=pdf, filetype='pdf') as doc:
            p = doc[0]
            pix = p.get_pixmap(matrix=pymupdf.Matrix(max_edge / max(p.rect.width, p.rect.height), max_edge / max(p.rect.width, p.rect.height)), alpha=False)
            return Image.frombytes('RGB', (pix.width, pix.height), pix.samples), source
    raise ValueError('This file needs a supported drawing export before previewing')


def png_bytes(image: Image.Image):
    out = io.BytesIO()
    image.save(out, 'PNG', optimize=True)
    return out.getvalue()


def image_inputs(path: Path, pages: list[int], region=None):
    """Overview plus detail crops, with invertible image-to-page coordinates."""
    inputs = []
    for page in pages:
        image, _ = render_page(path, page, max_edge=3200)
        if region:
            x0, y0, x1, y1 = region
            crop = image.crop((int(x0 * image.width), int(y0 * image.height), int(x1 * image.width), int(y1 * image.height)))
            crop.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
            inputs.append({'image': crop, 'page': page, 'region': list(region), 'kind': 'selected region'})
            continue
        overview = image.copy()
        overview.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
        inputs.append({'image': overview, 'page': page, 'region': [0, 0, 1, 1], 'kind': 'overview'})
        small = SMALL_IMAGE_CROPS and max(image.size) <= 1600
        if (max(image.size) > 1600 or small) and len(pages) <= 2:
            # Overlap makes tiny symbols crossing a crop boundary inspectable.
            for x0, y0, x1, y1 in ((0, 0, .55, .55), (.45, 0, 1, .55), (0, .45, .55, 1), (.45, .45, 1, 1)):
                crop = image.crop((int(x0 * image.width), int(y0 * image.height), int(x1 * image.width), int(y1 * image.height)))
                if small:  # enlarge small plans so their symbols cover more pixels
                    crop = crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.LANCZOS)
                crop.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
                inputs.append({'image': crop, 'page': page, 'region': [x0, y0, x1, y1],
                               'kind': 'enlarged detail crop' if small else 'detail crop'})
    return inputs

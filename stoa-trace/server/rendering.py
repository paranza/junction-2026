from __future__ import annotations

import io
import os
import re
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

# Enlarged overlapping crops for small plans (most CubiCasa images are under 1,000 px).
# Off until the cubicasa comparison shows it helps; part of the inventory cache key.
SMALL_IMAGE_CROPS = os.environ.get('STOA_SMALL_IMAGE_CROPS', '') == '1'


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


def render_page(path: Path, page=1, max_edge=2400):
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
    if suffix in {'.png', '.jpg', '.jpeg'}:
        if source_page != 1:
            raise ValueError('Image has one page')
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            if image.width * image.height > 100_000_000:
                raise ValueError('Image exceeds the processing size limit')
            image = image.convert('RGB')
            image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            return image.copy(), source
    if suffix in {'.pdf', '.svg'}:
        with pymupdf.open(source) as doc:
            if source_page > len(doc):
                raise ValueError('Drawing page is unavailable')
            p = doc[source_page - 1]
            scale = min(max_edge / max(p.rect.width, p.rect.height), 5)
            pix = p.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            return Image.frombytes('RGB', (pix.width, pix.height), pix.samples), source
    if suffix == '.dxf':
        import ezdxf
        from ezdxf.addons.drawing import Frontend, RenderContext, layout, config
        from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend
        cad = ezdxf.readfile(source)
        backend = PyMuPdfBackend()
        cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE)
        Frontend(RenderContext(cad), backend, config=cfg).draw_layout(cad.modelspace(), finalize=True)
        pdf = backend.get_pdf_bytes(layout.Page(0, 0))
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

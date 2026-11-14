import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Independent SVG structure check: element counts, embedded rasters, text, CSS classes, patterns; twin JPG aspect;
# PyMuPDF render vs twin (grey correlation) to see whether the render is usable.
import os, re, collections, xml.etree.ElementTree as ET
import numpy as np, cv2, pymupdf
D = _DATA + "/data/wikimedia"
V = os.path.dirname(os.path.abspath(__file__))
for f in sorted(x for x in os.listdir(D) if x.endswith('.svg')):
    raw = open(os.path.join(D, f), 'rb').read()
    root = ET.fromstring(raw)
    tags = collections.Counter(el.tag.split('}')[-1] for el in root.iter())
    texts = [''.join(el.itertext()).strip() for el in root.iter() if el.tag.split('}')[-1] == 'text']
    texts = [t for t in texts if t]
    n_class = sum(1 for el in root.iter() if 'class' in el.attrib)
    n_patfill = len(re.findall(rb'fill="url\(#|fill:url\(#', raw))
    vb = root.attrib.get('viewBox'); wv, hv = root.attrib.get('width'), root.attrib.get('height')
    jpg = cv2.imread(os.path.join(D, f[:-4] + '.jpg'), cv2.IMREAD_GRAYSCALE)
    doc = pymupdf.open(os.path.join(D, f)); pg = doc[0]
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(jpg.shape[1] / pg.rect.width, jpg.shape[0] / pg.rect.height), alpha=False)
    ren = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
    ren = cv2.cvtColor(ren, cv2.COLOR_RGB2GRAY) if pix.n >= 3 else ren[..., 0]
    ren = cv2.resize(ren, (jpg.shape[1], jpg.shape[0]), interpolation=cv2.INTER_AREA)
    corr = np.corrcoef(cv2.resize(ren, (300, int(300 * jpg.shape[0] / jpg.shape[1]))).ravel().astype(float),
                       cv2.resize(jpg, (300, int(300 * jpg.shape[0] / jpg.shape[1]))).ravel().astype(float))[0, 1]
    side = np.hstack([cv2.resize(jpg, (600, int(600 * jpg.shape[0] / jpg.shape[1]))), cv2.resize(ren, (600, int(600 * jpg.shape[0] / jpg.shape[1])))])
    cv2.imwrite(os.path.join(V, f'svg_pair_{f[:-4]}.png'), side)
    print(f, 'bytes', len(raw), 'image', tags.get('image', 0), 'data:image', raw.count(b'data:image'), 'text', tags.get('text', 0),
          'tspan', tags.get('tspan', 0), 'style', tags.get('style', 0), 'class_attrs', n_class, 'pattern', tags.get('pattern', 0),
          'url_fills', n_patfill, 'paths', tags.get('path', 0), 'viewBox', vb, 'wh', wv, hv,
          'jpg', jpg.shape[::-1], 'aspect_svg', round(pg.rect.width / pg.rect.height, 4), 'aspect_jpg', round(jpg.shape[1] / jpg.shape[0], 4),
          'corr', round(float(corr), 3))
    print('   texts:', texts[:20])

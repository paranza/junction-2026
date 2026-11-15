"""Source-bound OCR and geometry tools for the complex drawing reader.

Geometry is computed locally. Semantic selection, calibration endpoints and
OCR remain reviewable interpretations, never native-source verification.
No reference answers or drawing-specific profiles belong in this module.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import rendering
from .verification import ground_native_evidence, user_declared_dimension, unit_spec

REVISION = 'drawing-tools-v1'
MAX_TOOLS = 12
MAX_TILES = 48
MAX_GRAPH_PIXELS = 100_000
_engine = None
_ocr_lock = threading.Lock()


class ToolError(ValueError):
    pass


def box(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ToolError('A normalized page-coordinate rectangle is required.')
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
        raise ToolError('Coordinates must be finite numbers.')
    x0, y0, x1, y1 = value
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ToolError('Rectangle is outside the page or empty.')
    return list(value)


def contains(outer, inner):
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def point(value, bounds):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ToolError('A page-coordinate point is required.')
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
        raise ToolError('Invalid point.')
    if not (bounds[0] <= value[0] <= bounds[2] and bounds[1] <= value[1] <= bounds[3]):
        raise ToolError('Point is outside the requested region.')
    return list(value)


def _map(points, region, width, height):
    return [[region[0] + x / width * (region[2]-region[0]),
             region[1] + y / height * (region[3]-region[1])] for x, y in points]


def _bbox(points):
    return [min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)]


@lru_cache(maxsize=48)
def _digest(path, size, mtime):
    result = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''): result.update(chunk)
    return result.hexdigest()


def fingerprint(path):
    stat = path.stat()
    return _digest(str(path.resolve()), stat.st_size, stat.st_mtime_ns)


def _engine_read(image):
    global _engine
    # One engine and bounded ONNX threads avoid competing full CPU pools.
    with _ocr_lock:
        if _engine is None:
            from rapidocr_onnxruntime import RapidOCR
            _engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1,
                               det_limit_side_len=2400)
        result, _ = _engine(np.asarray(image.convert('RGB'))[:, :, ::-1].copy())
    return result or []


def _native_words(path, page):
    if path.suffix.lower() != '.pdf': return []
    import pymupdf
    with pymupdf.open(path) as doc:
        p = doc[page-1]; rect = p.rect
        result = []
        for word in p.get_text('words'):
            r = pymupdf.Rect(word[:4]) * p.rotation_matrix
            b = [r.x0/rect.width, r.y0/rect.height, r.x1/rect.width, r.y1/rect.height]
            if all(0 <= v <= 1 for v in b):
                result.append({'text': word[4], 'bbox': b, 'confidence': 1,
                               'basis': 'native_pdf_text', 'page': page})
        return result


def _overlap(a, b):
    intersection = max(0, min(a[2],b[2])-max(a[0],b[0])) * max(0,min(a[3],b[3])-max(a[1],b[1]))
    area = min((a[2]-a[0])*(a[3]-a[1]), (b[2]-b[0])*(b[3]-b[1]))
    return intersection / max(area, 1e-14)


def deduplicate_words(rows):
    kept = []; by_text = {}
    for row in sorted(rows, key=lambda r: -r['confidence']):
        # Prime marks are physical units, not cosmetic punctuation. A rotated
        # OCR reading of 8 must not delete a lower-confidence reading of 8'.
        text = row['text'].casefold().translate(str.maketrans({'′':"'",'’':"'",'″':'"'}))
        text = re.sub(r'[^\w\'"²³]', '', text)
        if not any(_overlap(row['bbox'],r['bbox']) > .5 for r in by_text.get(text,[])):
            kept.append(row);by_text.setdefault(text,[]).append(row)
    return sorted(kept, key=lambda r: (round(r['bbox'][1], 3), r['bbox'][0]))


def read_words(path, page, region, *, cache_root=None, rotated=True):
    """Persistent content-addressed original-resolution tiles, no answer cache."""
    region = box(region); native = _native_words(path, page)
    native = [w for w in native if contains(region, w['bbox'])]
    if len(native) >= 12: return {'words': native, 'complete': True, 'basis': 'native_pdf_text', 'tiles': 0}
    if cache_root is None:
        from .store import RUNTIME
        cache_root = RUNTIME / 'drawing-index'
    cache_root = Path(cache_root); cache_root.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in rendering.RASTER_SUFFIXES:
        metadata = rendering.raster_metadata(path)[0][page-1]
        width, height = metadata['width'], metadata['height']
    else:
        import pymupdf
        with pymupdf.open(path) as doc:
            width, height = doc[page-1].rect.width*3, doc[page-1].rect.height*3
    tile = 2200; stride = 1800
    nx = max(1, math.ceil(max(0, (region[2]-region[0])*width-tile)/stride)+1)
    ny = max(1, math.ceil(max(0, (region[3]-region[1])*height-tile)/stride)+1)
    if nx*ny*(2 if rotated else 1) > MAX_TILES:
        raise ToolError('OCR region exceeds the tile budget. Request smaller source regions.')
    rows = list(native); digest = fingerprint(path); started = time.monotonic(); count = 0
    for y in range(ny):
        for x in range(nx):
            left = min(region[0]+x*stride/width, max(region[0],region[2]-tile/width))
            top = min(region[1]+y*stride/height, max(region[1],region[3]-tile/height))
            r = [left, top, min(region[2],left+tile/width), min(region[3],top+tile/height)]
            key = hashlib.sha256(json.dumps([REVISION,digest,page,r,rotated]).encode()).hexdigest()
            target = cache_root/(key+'.json')
            try: words = json.loads(target.read_text())
            except (OSError, ValueError):
                if time.monotonic()-started > 150:
                    return {'words': deduplicate_words(rows), 'complete': False, 'basis': 'ocr', 'tiles': count}
                image = rendering.render_region(path,page,r,2200); words = []
                for angle in ([0,90] if rotated else [0]):
                    im = image if angle == 0 else image.rotate(90, expand=True)
                    for poly, text, confidence in _engine_read(im):
                        if float(confidence) < .5: continue
                        # PIL +90: x_original = W-y_rotated, y_original=x_rotated.
                        points = [[float(p[0]),float(p[1])] for p in poly]
                        if angle: points = [[image.width-p[1],p[0]] for p in points]
                        b = _bbox(_map(points,r,image.width,image.height))
                        if not contains(region,b): continue
                        # Ignore fragments cut by an internal tile seam. The overlap owns them.
                        px = _bbox(points)
                        if ((r[0] > region[0] and px[0] < 3) or (r[1] > region[1] and px[1] < 3)
                            or (r[2] < region[2] and px[2] > image.width-3)
                            or (r[3] < region[3] and px[3] > image.height-3)): continue
                        words.append({'text':str(text),'bbox':b,'confidence':float(confidence),'page':page,'basis':'ocr','orientation':angle})
                temporary = target.with_suffix(f'.{threading.get_ident()}.tmp')
                temporary.write_text(json.dumps(words)); os.replace(temporary,target)
            rows.extend(words); count += 1
    return {'words': deduplicate_words(rows), 'complete': True, 'basis': 'ocr', 'tiles':count}


def _ink(image, color=None):
    import cv2
    rgb = np.asarray(image.convert('RGB'))
    if color:
        colors = {'red':(0,170,80),'green':(35,90,40),'blue':(90,145,50),
                  'magenta':(135,175,45),'cyan':(75,105,45)}
        if color not in colors: raise ToolError('Unsupported line color; use red, green, blue, cyan or magenta.')
        lo,hi,sat = colors[color]; hsv = cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
        if color == 'red': return ((hsv[:,:,0]<12)|(hsv[:,:,0]>170)) & (hsv[:,:,1]>80) & (hsv[:,:,2]>40)
        return (hsv[:,:,0]>=lo)&(hsv[:,:,0]<=hi)&(hsv[:,:,1]>sat)&(hsv[:,:,2]>40)
    gray = cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    return cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1] > 0


def thin(mask):
    """Bounded Zhang-Suen thinning, preserving each foreground centerline."""
    a = np.pad(mask.astype(np.uint8),1)
    for _ in range(100):
        changed = False
        for phase in (0,1):
            p = [a[:-2,1:-1],a[:-2,2:],a[1:-1,2:],a[2:,2:],a[2:,1:-1],a[2:,:-2],a[1:-1,:-2],a[:-2,:-2]]
            count = sum(p); transitions = sum((p[i]==0)&(p[(i+1)%8]==1) for i in range(8))
            if phase == 0: condition = (p[0]*p[2]*p[4]==0)&(p[2]*p[4]*p[6]==0)
            else: condition = (p[0]*p[2]*p[6]==0)&(p[0]*p[4]*p[6]==0)
            remove = (a[1:-1,1:-1]==1)&(count>=2)&(count<=6)&(transitions==1)&condition
            if remove.any(): a[1:-1,1:-1][remove] = 0; changed = True
        if not changed: return a[1:-1,1:-1].astype(bool)
    raise ToolError('Centerline thinning did not converge within the processing budget.')


def skeleton_graph(mask, seed=None):
    """Unique undirected pixel edges; a shared run is never summed twice."""
    pixels = {tuple(p) for p in np.argwhere(thin(mask))}
    if len(pixels)>MAX_GRAPH_PIXELS: raise ToolError('Too much line geometry. Narrow the region or select a line color.')
    adjacency = {}
    for y,x in pixels:
        neighbors = []
        for dy,dx in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
            q = (y+dy,x+dx)
            if q not in pixels: continue
            if dx and dy and ((y,x+dx) in pixels or (y+dy,x) in pixels): continue
            neighbors.append(q)
        adjacency[(y,x)] = neighbors
    if seed is not None and pixels:
        nearest = min(pixels,key=lambda p:(p[0]-seed[1])**2+(p[1]-seed[0])**2)
        if math.dist(nearest,(seed[1],seed[0]))>16: raise ToolError('Seed is not near a detected line.')
        connected = {nearest}; stack=[nearest]
        while stack:
            for q in adjacency[stack.pop()]:
                if q not in connected: connected.add(q);stack.append(q)
        adjacency = {p:n for p,n in adjacency.items() if p in connected}
    if not adjacency: raise ToolError('No usable line network was detected.')
    nodes = {p for p,n in adjacency.items() if len(n)!=2}
    visited = set(); paths=[]
    def walk(start, neighbor):
        path=[start,neighbor];visited.add(tuple(sorted((start,neighbor))))
        while path[-1] not in nodes:
            choices=[p for p in adjacency[path[-1]] if p!=path[-2] and tuple(sorted((path[-1],p))) not in visited]
            if not choices: break
            q=choices[0];visited.add(tuple(sorted((path[-1],q))));path.append(q)
        return path
    for p in sorted(nodes):
        for q in adjacency[p]:
            if tuple(sorted((p,q))) not in visited: paths.append(walk(p,q))
    # Closed loops have no endpoints and must still contribute exactly once.
    for p,n in adjacency.items():
        for q in n:
            if tuple(sorted((p,q))) not in visited: paths.append(walk(p,q))
    length = math.fsum(math.dist(a,b) for path in paths for a,b in zip(path,path[1:]))
    return {'paths':paths,'length_pixels':length,'junctions':sum(len(n)>2 for n in adjacency.values()),
            'endpoints':sum(len(n)==1 for n in adjacency.values()),'components_selected':'seeded' if seed is not None else 'all'}


def template_matches(image, template, *, threshold=.78, maximum=120):
    """Rotated/scaled legend proposals with overlap suppression."""
    import cv2
    source = cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2GRAY)
    target = cv2.cvtColor(np.asarray(template.convert('RGB')),cv2.COLOR_RGB2GRAY)
    if target.std()<8: raise ToolError('Template is blank or has insufficient contrast.')
    matches=[]; truncated=False
    for rotation in range(4):
        rotated=np.rot90(target,rotation)
        for factor in (.8,1.,1.2):
            sample=cv2.resize(rotated,None,fx=factor,fy=factor,interpolation=cv2.INTER_AREA)
            h,w=sample.shape
            if h<5 or w<5 or h>source.shape[0] or w>source.shape[1]:continue
            scores=cv2.matchTemplate(source,sample,cv2.TM_CCOEFF_NORMED)
            for _ in range(maximum+1):
                _,score,_,location=cv2.minMaxLoc(scores)
                if score<threshold:break
                x,y=location;b=[x,y,x+w,y+h]
                if not any(_overlap(b,m['bbox'])>.35 for m in matches):matches.append({'bbox':b,'score':float(score),'rotation':rotation*90})
                scores[max(0,y-h//2):min(scores.shape[0],y+h//2+1),max(0,x-w//2):min(scores.shape[1],x+w//2+1)]=-1
                if len(matches)>maximum:truncated=True;break
            if truncated:break
        if truncated:break
    return {'matches':sorted(matches,key=lambda m:-m['score'])[:maximum],'truncated':truncated}


class DrawingSession:
    def __init__(self,path,page,bounds):
        self.path=Path(path);self.page=page;self.bounds=box(bounds)
        self.source=fingerprint(self.path);self.results={};self.calibrations={};self.calls=0
        self.max_tools=MAX_TOOLS

    def _region(self,value):
        r=box(value or self.bounds)
        if not contains(self.bounds,r):raise ToolError('Tool region is outside the selected scope.')
        return r

    def _words(self,region):return read_words(self.path,self.page,region)

    def _image(self,region):return rendering.render_region(self.path,self.page,region,2600)

    def execute(self,request):
        if self.calls>=self.max_tools:raise ToolError('Local tool budget reached.')
        self.calls+=1
        if fingerprint(self.path)!=self.source:raise ToolError('Source changed during inspection.')
        tool=request.get('name')
        # Calibration may read a scale outside a selected takeoff region. Only
        # measured geometry/search regions remain restricted to that selection.
        r=box(request.get('region') or [0,0,1,1]) if tool=='calibrate' else self._region(request.get('region'))
        identity=f't{self.calls}'
        result={'id':identity,'name':tool,'page':self.page,'bbox':r,'source_verified':False,'needs_review':True}
        if tool=='ocr':
            data=self._words(r);query=str(request.get('query') or '').casefold().strip()
            rows=data['words']
            if query:
                terms=query.split();rows=sorted(rows,key=lambda w:-sum(term in w['text'].casefold() for term in terms))
            result.update(**{k:v for k,v in data.items() if k!='words'},words=rows[:240],returned=len(rows[:240]),total_words=len(rows),truncated=len(rows)>240)
        elif tool=='calibrate':
            reference=request.get('reference') or {};points=reference.get('points') or []
            if len(points)!=2:raise ToolError('Calibration requires two endpoints.')
            points=[point(p,r) for p in points];annotation=box(reference.get('annotation_bbox'))
            data=self._words(annotation)
            quote=str(reference.get('quote') or '').strip()
            clean=lambda t:re.sub(r'[^\w.,\'"²³]+','',t.casefold())
            def quoted_stream(words):
                streams=[' '.join(w['text'] for w in words if w.get('orientation',0)==angle) for angle in (0,90)]
                return next((text for text in streams if quote and clean(quote) in clean(text)),None)
            def source_reference(words):
                for word in words:
                    wb=word.get('bbox')
                    if not wb or not (annotation[0]<=(wb[0]+wb[2])/2<=annotation[2] and annotation[1]<=(wb[1]+wb[3])/2<=annotation[3]):continue
                    printed=str(word.get('text') or '')
                    checked,_=ground_native_evidence({'text':printed},{'quoted_text':printed,
                        'value':reference.get('value'),'unit':reference.get('unit')},'length')
                    if checked.get('value') is not None:return printed
            text=quoted_stream(data['words'])
            # Scale labels are often separate OCR tokens and a tight crop can
            # lose a foot/inch prime. Re-read with bounded surrounding context,
            # but a replacement scalar token must remain INSIDE the original
            # annotation box. Nearby unrelated unit labels cannot qualify it.
            supported_word=source_reference(data['words'])
            if text is None and supported_word is None:
                margin=max(.015,min(.06,max(annotation[2]-annotation[0],annotation[3]-annotation[1])*.5))
                expanded=[max(0,annotation[0]-margin),max(0,annotation[1]-margin),min(1,annotation[2]+margin),min(1,annotation[3]+margin)]
                data=self._words(expanded)
                text=quoted_stream(data['words']);supported_word=source_reference(data['words'])
            if supported_word and (text is None or not quote):
                quote=supported_word;text=supported_word
            if text is None:raise ToolError('Calibration quote was not reproduced by positioned source OCR/text. Inspect its annotation region.')
            item={'value':reference.get('value'),'unit':reference.get('unit'),'quoted_text':quote}
            checked,_=ground_native_evidence({'text':quote},item,'length')
            # OCR may retain a printed suffix that the requested substring
            # omitted, e.g. quote="8" in the located token "8'". Qualify from
            # that SAME source token, never a unit elsewhere on the sheet.
            if checked.get('value') is None:
                for word in data['words']:
                    printed=str(word.get('text') or '')
                    if not clean(quote) or clean(quote) not in clean(printed):continue
                    supported,_=ground_native_evidence({'text':printed},{**item,'quoted_text':printed},'length')
                    if supported.get('value') is not None:
                        quote=printed;checked=supported;break
            if checked.get('value') is None and not user_declared_dimension(item,text,'length'):
                raise ToolError('Calibration needs a reproduced source length and explicit source units.')
            spec=unit_spec(reference.get('unit'));value=reference.get('value')
            if not spec or spec[0]!='length' or type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ToolError('Invalid reference length.')
            self.calibrations[identity]={'points':points,'metres':value*spec[1], 'region':r,'quote':quote,'annotation_bbox':annotation}
            result.update(calibration_id=identity,reference={**reference,'quote':quote},complete=data['complete'],warning='Source text was reproduced; endpoints and scale applicability still require visual review.')
        elif tool in {'polygon','perimeter','path','multipath','room','network','vectors'}:
            calibration=self.calibrations.get(request.get('calibration_id'))
            if calibration is None or not contains(calibration['region'],r):raise ToolError('Use an established calibration valid for this entire region.')
            image=self._image(r);w,h=image.size
            sx=w/(r[2]-r[0]);sy=h/(r[3]-r[1])
            a,b=calibration['points'];pixels=math.hypot((a[0]-b[0])*sx,(a[1]-b[1])*sy)
            if pixels<8:raise ToolError('Calibration endpoints are too close for reliable measurement.')
            scale=calibration['metres']/pixels;geometry=request.get('geometry') or []
            result.update(calibration_id=request['calibration_id'],reference_quote=calibration['quote'],complete=True)
            if tool in {'polygon','perimeter','path','multipath'}:
                from shapely.geometry import Polygon,LineString
                from shapely.ops import unary_union
                if not (3 if tool in {'polygon','perimeter'} else 2)<=len(geometry)<=640:raise ToolError('Invalid geometry point count.')
                parts=[[]]
                for p in geometry:
                    if p is None and tool=='multipath':
                        if parts[-1]:parts.append([])
                    else:parts[-1].append(point(p,r))
                parts=[part for part in parts if part]
                if any(len(part)<2 for part in parts):raise ToolError('Each measured path needs two points.')
                # Analytic geometry uses a fixed source aspect, independent of
                # arbitrary preview sizes or per-tool crop rounding.
                if self.path.suffix.lower() in rendering.RASTER_SUFFIXES:
                    meta=rendering.raster_metadata(self.path)[0][self.page-1];gx,gy=meta['width'],meta['height']
                else:
                    import pymupdf
                    with pymupdf.open(self.path) as pdf:gx,gy=pdf[self.page-1].rect.width,pdf[self.page-1].rect.height
                shapes=[LineString([(x*gx,y*gy) for x,y in part]) for part in parts]
                if tool in {'polygon','perimeter'}:shape=Polygon([(x*gx,y*gy) for x,y in parts[0]])
                else:shape=unary_union(shapes)
                if shape.is_empty or not shape.is_valid or (tool=='path' and not shapes[0].is_simple):raise ToolError('Geometry intersects itself or is invalid.')
                a,b=calibration['points'];metres_per_source=calibration['metres']/math.hypot((a[0]-b[0])*gx,(a[1]-b[1])*gy)
                flat=[p for part in parts for p in part]
                if tool=='perimeter':flat=flat+[flat[0]]
                result.update(value=shape.area*metres_per_source**2 if tool=='polygon' else shape.length*metres_per_source,
                    unit='m²' if tool=='polygon' else 'm',geometry=flat,
                    perimeter_m=shape.length*metres_per_source,measurement_basis='source_calibrated_selected_geometry')
                if tool=='multipath':result['polylines']=parts
                result['bbox']=_bbox(flat)
                result['measurement_key']=hashlib.sha256((str(request['calibration_id'])+shape.normalize().wkb_hex).encode()).hexdigest()
            elif tool=='vectors':
                if self.path.suffix.lower()!='.pdf':raise ToolError('Vector paths require a vector PDF. Use raster geometry tools for scans.')
                import pymupdf
                segments=[];skipped_curves=0
                with pymupdf.open(self.path) as pdf:
                    source_page=pdf[self.page-1];rect=source_page.rect
                    for drawing in source_page.get_drawings():
                        if drawing.get('type')=='f':continue
                        for item in drawing['items']:
                            if item[0]=='l':pairs=[(item[1],item[2])]
                            elif item[0]=='re':
                                v=item[1];pairs=[(v.tl,v.tr),(v.tr,v.br),(v.br,v.bl),(v.bl,v.tl)]
                            else:skipped_curves+=1;continue
                            for a,b in pairs:
                                a=a*source_page.rotation_matrix;b=b*source_page.rotation_matrix
                                points=[[a.x/rect.width,a.y/rect.height],[b.x/rect.width,b.y/rect.height]]
                                if not all(r[0]<=p[0]<=r[2] and r[1]<=p[1]<=r[3] for p in points):continue
                                value=math.hypot((points[1][0]-points[0][0])*sx,(points[1][1]-points[0][1])*sy)*scale
                                if value<=0:continue
                                segment={'id':f'{identity}.v{len(segments)+1}','value':value,'unit':'m','geometry':points,
                                         'bbox':self._line_box(points,r,sx,sy),'page':self.page,'source_verified':False,'needs_review':True,'complete':True,
                                         'label':'Source vector segment','measurement_basis':'source_calibrated_pdf_vector',
                                         'stroke_color':drawing.get('color'),'stroke_width':drawing.get('width'),'dashes':drawing.get('dashes'),
                                         'reference_quote':calibration['quote']}
                                segments.append(segment)
                                if len(segments)>300:raise ToolError('More than 300 vector candidates. Request a smaller region.')
                for segment in segments:self.results[segment['id']]=segment
                result.update(segments=segments,complete=False,skipped_curves=skipped_curves,
                              warning='Source vector proposals, not a complete system inventory. Shared strokes, dash conventions, curves and semantics require inspection.')
            elif tool=='room':
                import cv2
                seed=point(request.get('seed'),r);ink=_ink(image,request.get('color'))
                # Conservative gap closing. A region touching the crop border is not a closed room.
                barriers=cv2.morphologyEx(ink.astype(np.uint8),cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
                n,labels,stats,_=cv2.connectedComponentsWithStats(1-barriers,8)
                x=min(w-1,int((seed[0]-r[0])*sx));y=min(h-1,int((seed[1]-r[1])*sy));label=labels[y,x]
                if label==0:raise ToolError('Room seed lies on ink; select a point inside the room.')
                component=(labels==label).astype(np.uint8)
                if component[0,:].any() or component[-1,:].any() or component[:,0].any() or component[:,-1].any():raise ToolError('Room boundary is open or extends outside the inspected region.')
                contours,_=cv2.findContours(component,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
                contour=max(contours,key=cv2.contourArea);poly=cv2.approxPolyDP(contour,1,True).reshape(-1,2).tolist()
                result.update(value=float(component.sum())*scale**2,unit='m²',perimeter_m=float(cv2.arcLength(contour,True))*scale,
                              geometry=_map(poly,r,w,h),measurement_basis='source_calibrated_closed_ink_region',warning='Wall faces, furniture and gap closing affect this provisional region.')
            else:
                ink=_ink(image,request.get('color'))
                # Optional text removal uses located OCR boxes, never model-supplied masks.
                if request.get('remove_text'):
                    words=self._words(r)
                    for word in words['words']:
                        b=word['bbox'];x0=max(0,int((b[0]-r[0])*sx));x1=min(w,int((b[2]-r[0])*sx)+1)
                        y0=max(0,int((b[1]-r[1])*sy));y1=min(h,int((b[3]-r[1])*sy)+1);ink[y0:y1,x0:x1]=False
                seed=request.get('seed')
                if seed is not None:seed=point(seed,r);seed=[(seed[0]-r[0])*sx,(seed[1]-r[1])*sy]
                graph=skeleton_graph(ink,seed)
                if len(graph['paths'])>300:raise ToolError('Network is too fragmented. Narrow the region or isolate its line style.')
                edges=[]
                words=self._words(r)['words'] if request.get('query') else []
                from shapely.geometry import LineString,Point
                for index,path in enumerate(graph['paths']):
                    if len(path)<2:continue
                    mapped=_map([[p[1],p[0]] for p in path],r,w,h);line=LineString(mapped)
                    nearby=[word['text'] for word in words if line.distance(Point((word['bbox'][0]+word['bbox'][2])/2,(word['bbox'][1]+word['bbox'][3])/2))<.015]
                    edge_id=f'{identity}.s{index+1}'
                    geometry=mapped[::max(1,len(mapped)//24)]
                    if geometry[-1]!=mapped[-1]:geometry.append(mapped[-1])
                    edge={'id':edge_id,'value':math.fsum(math.dist(a,b) for a,b in zip(path,path[1:]))*scale,'unit':'m',
                          'bbox':self._line_box(mapped,r,sx,sy),'page':self.page,'source_verified':False,'needs_review':True,'complete':True,
                          'label':'Traced segment '+str(index+1),'measurement_basis':'source_calibrated_traced_ink_segment',
                          'geometry':geometry,'nearby_text':nearby,'reference_quote':calibration['quote']}
                    edges.append(edge);self.results[edge_id]=edge
                result.update(value=graph['length_pixels']*scale,unit='m',junctions=graph['junctions'],endpoints=graph['endpoints'],edges=edges,
                              measurement_basis='source_calibrated_traced_ink_network',
                              warning='This measures detected ink centerlines. Crossings may be junctions; text removal may cut runs. Check line isolation, components, dashed gaps, vertical and off-sheet scope. It is not independently verified physical pipe length.')
            if tool!='vectors' and (not math.isfinite(result['value']) or result['value']<=0):raise ToolError('No positive measured geometry.')
        elif tool=='symbols':
            template_region=box(request.get('template'));source=self._image(r)
            # Render the template at the SAME page scale as the search raster.
            edge=max(8,round(max((template_region[2]-template_region[0])*source.width/(r[2]-r[0]),(template_region[3]-template_region[1])*source.height/(r[3]-r[1]))))
            if edge>500:raise ToolError('Choose a tight legend symbol crop, without its description.')
            template=rendering.render_region(self.path,self.page,template_region,edge)
            data=template_matches(source,template);matches=[]
            for match in data['matches']:
                b=match['bbox'];mapped=_bbox(_map([[b[0],b[1]],[b[2],b[3]]],r,source.width,source.height))
                if _overlap(mapped,template_region)>.2:continue
                matches.append({**match,'bbox':mapped})
            result.update(matches=matches,complete=False,truncated=data['truncated'],warning='Template similarity proposals only. Confirm each source symbol and inspect missed or alternative symbols; not a final count.')
        else:raise ToolError('Unknown drawing tool.')
        result['label']=str(request.get('label') or tool)[:300]
        self.results[identity]=result
        return result

    def preview(self,identity,*,part=None):
        """Render computed geometry over the actual source, never an answer label."""
        result=self.results.get(identity,{})
        parts=result.get('polylines') or ([result['geometry']] if result.get('geometry') else [])
        if part is not None:
            if part not in parts:raise ToolError('Preview geometry is not part of this source measurement.')
            parts=[part]
        if not parts:return None
        pts=[p for part in parts for p in part];r=_bbox(pts)
        margin=.012;r=[max(self.bounds[0],r[0]-margin),max(self.bounds[1],r[1]-margin),min(self.bounds[2],r[2]+margin),min(self.bounds[3],r[3]+margin)]
        image=rendering.render_region(self.path,self.page,r,2600).convert('RGB')
        from PIL import ImageDraw
        draw=ImageDraw.Draw(image)
        for part in parts:
            points=[((p[0]-r[0])/(r[2]-r[0])*image.width,(p[1]-r[1])/(r[3]-r[1])*image.height) for p in part]
            if result.get('name')=='polygon':points.append(points[0])
            draw.line(points,fill='#dd2048',width=3)
            for x,y in points:draw.ellipse((x-3,y-3,x+3,y+3),fill='#2459ff')
        return image,r

    def operand(self,identity):
        result=self.results.get(identity)
        if not result or not result.get('complete') or result.get('value') is None:return None
        operand={k:result[k] for k in ('id','value','unit','page','bbox','label','source_verified','measurement_basis','measurement_key') if k in result}
        geometry=result.get('geometry')
        if geometry:
            b=_bbox(geometry)
            operand['bbox']=[max(0,b[0]-1e-5),max(0,b[1]-1e-5),min(1,b[2]+1e-5),min(1,b[3]+1e-5)]
            if result['unit']=='m²':operand['polygon']=geometry
            elif result.get('polylines'):operand['polylines']=result['polylines']
            else:operand['polyline']=geometry
        return operand

    @staticmethod
    def _line_box(points,region,sx,sy):
        b=_bbox(points)
        return [max(region[0],b[0]-2/sx),max(region[1],b[1]-2/sy),min(region[2],b[2]+2/sx),min(region[3],b[3]+2/sy)]

    def prompt_results(self):
        return list(self.results.values())

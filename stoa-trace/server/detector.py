"""CPU inference for checksum-pinned visual proposal models. No answer keys or filename rules."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from functools import lru_cache
from pathlib import Path

REVISION = 'symbol-detectors-onnx-v2'
_lock = threading.Lock()


def _manifest():
    value=os.environ.get('STOA_DETECTOR_MANIFEST','').strip()
    if not value:return None
    path=Path(value).expanduser().resolve()
    manifest=json.loads(path.read_text())
    model=(path.parent/manifest['model_file']).resolve()
    if model.parent!=path.parent or manifest.get('kind') not in {'plannet_heatmap','yolo_boxes'}:
        raise ValueError('Unsupported detector manifest')
    checksum=hashlib.sha256(model.read_bytes()).hexdigest()
    if checksum!=manifest.get('model_sha256'):
        raise ValueError('Detector checksum mismatch')
    if not 0<float(manifest.get('threshold',.35))<1:
        raise ValueError('Invalid detector threshold')
    classes=manifest.get('classes')
    if not isinstance(classes,list) or not classes or len(set(classes))!=len(classes) or any(not isinstance(c,str) for c in classes):
        raise ValueError('Invalid class mapping')
    if manifest['kind']=='yolo_boxes':
        size=manifest.get('input_size',1024)
        if type(size) is not int or size<320 or size>1536 or size%32:raise ValueError('Invalid model input size')
        if not 0<float(manifest.get('iou_threshold',.5))<1:raise ValueError('Invalid overlap threshold')
        thresholds=manifest.get('class_thresholds',{})
        if not isinstance(thresholds,dict) or any(k not in classes or not 0<float(v)<1 for k,v in thresholds.items()):raise ValueError('Invalid class threshold')
        if manifest.get('color_mode','rgb') not in {'rgb','grayscale'}:raise ValueError('Invalid detector color mode')
    return {**manifest,'threshold':float(manifest.get('threshold',.35)),
            'class_thresholds':{k:float(v) for k,v in manifest.get('class_thresholds',{}).items()},
            'iou_threshold':float(manifest.get('iou_threshold',.5)),'path':str(model)}


def signature():
    try:
        manifest=_manifest()
        return {'revision':REVISION,'model_sha256':manifest['model_sha256'],
                'threshold':manifest.get('threshold',.35),'classes':manifest['classes'],
                'kind':manifest['kind'],'input_size':manifest.get('input_size'),
                'class_thresholds':manifest.get('class_thresholds',{}),'iou_threshold':manifest.get('iou_threshold'),
                'color_mode':manifest.get('color_mode','rgb')} if manifest else None
    except (KeyError,ValueError,OSError,TypeError):
        return {'revision':REVISION,'unavailable':True}


@lru_cache(maxsize=2)
def _session(path,checksum):
    import onnxruntime as ort
    options=ort.SessionOptions()
    options.intra_op_num_threads=2
    options.inter_op_num_threads=1
    return ort.InferenceSession(path,sess_options=options,providers=['CPUExecutionProvider'])


def detect_image(image,document_id=None,page=1):
    """Return point detections with approximate boxes, not measured object extents."""
    started=time.monotonic()
    try:
        manifest=_manifest()
        if not manifest:return None
        import numpy as np
        width,height=image.size
        if width*height>100_000_000:raise ValueError('Detector image too large')
        session=_session(manifest['path'],manifest['model_sha256'])
        if manifest['kind']=='yolo_boxes':
            return _detect_boxes(image,session,manifest,document_id,page,started)
        if width*height>6_000_000:raise ValueError('Heatmap detector image too large')
        gray=np.asarray(image.convert('L'),dtype=np.float32)
        source=1-gray/255.
        heat=np.zeros((len(manifest['classes']),height,width),dtype=np.float32)
        tile,pad=512,64
        with _lock:
            for top in range(0,height,tile):
                for left in range(0,width,tile):
                    ya,xa=max(0,top-pad),max(0,left-pad)
                    yb,xb=min(height,top+tile+pad),min(width,left+tile+pad)
                    crop=np.zeros((1,1,640,640),dtype=np.float32)
                    crop[0,0,:yb-ya,:xb-xa]=source[ya:yb,xa:xb]
                    output=session.run(None,{session.get_inputs()[0].name:crop})[0]
                    if output.shape!=(1,len(manifest['classes']),640,640):
                        raise ValueError('Unexpected detector output shape')
                    if not np.isfinite(output).all() or output.min()<0 or output.max()>1:
                        raise ValueError('Detector output must contain finite probabilities')
                    ye,xe=min(height,top+tile),min(width,left+tile)
                    heat[:,top:ye,left:xe]=output[0,:,top-ya:ye-ya,left-xa:xe-xa]
        # Pool after stitching. Adjacent tiles never double count the same peak.
        padded=np.pad(heat,((0,0),(3,3),(3,3)),constant_values=-1)
        maximum=np.maximum.reduce([padded[:,dy:dy+height,dx:dx+width] for dy in range(7) for dx in range(7)])
        points=np.argwhere((heat==maximum)&(heat>float(manifest.get('threshold',.35))))
        if len(points)>3000:raise ValueError('Unusable detector output')
        objects=[]
        aliases={'wc':'toilet','washbasin':'sink'}
        for channel,y,x in points:
            category=aliases.get(manifest['classes'][channel],manifest['classes'][channel])
            radius=18 if category=='door' else 14
            box=[max(0,(x-radius)/width),max(0,(y-radius)/height),min(1,(x+radius)/width),min(1,(y+radius)/height)]
            identity=hashlib.sha256(f"{manifest['model_sha256']}:{page}:{channel}:{x}:{y}".encode()).hexdigest()[:18]
            objects.append({'id':'detector-'+identity,'category':category,'type':category,'label':category.title()+' detector candidate',
                            'page':page,'document_id':document_id,'bbox':box,'point':[float(x/width),float(y/height)],
                            'score':round(float(heat[channel,y,x]),5),'evidence_kind':'visual','source_verified':False,
                            'location_kind':'detected_center','extent_estimated':True})
        return {'objects':objects,'model_sha256':manifest['model_sha256'],'name':manifest.get('name','PlanNet'),
                'training_domain':manifest.get('training_domain','Unknown'),'calibrated':False,
                'abstained':not objects,
                'duration_ms':round((time.monotonic()-started)*1000),'revision':REVISION}
    except Exception as error:  # optional inference must never erase the primary answer
        return {'objects':[],'unavailable':True,'reason':type(error).__name__,
                'duration_ms':round((time.monotonic()-started)*1000),'revision':REVISION}


def _overlap(a,b):
    overlap=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return overlap/max(1e-12,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-overlap)


def _detect_boxes(image,session,manifest,document_id,page,started):
    import numpy as np
    from PIL import Image
    width,height=image.size;size=manifest.get('input_size',1024)
    scale=min(size/width,size/height)
    new_width,new_height=round(width*scale),round(height*scale)
    left,top=(size-new_width)//2,(size-new_height)//2
    canvas=Image.new('RGB',(size,size),(114,114,114))
    source=image.convert('L').convert('RGB') if manifest.get('color_mode','rgb')=='grayscale' else image.convert('RGB')
    canvas.paste(source.resize((new_width,new_height),Image.Resampling.BILINEAR),(left,top))
    tensor=np.asarray(canvas,dtype=np.float32).transpose(2,0,1)[None]/255
    with _lock:output=session.run(None,{session.get_inputs()[0].name:tensor})[0]
    if output.ndim!=3 or output.shape[0]!=1 or output.shape[1]!=4+len(manifest['classes']) or output.shape[2]>200000 or not np.isfinite(output).all():
        raise ValueError('Invalid box detector output')
    scores=output[0,4:]
    if scores.min()<0 or scores.max()>1:raise ValueError('Invalid detection probabilities')
    categories=scores.argmax(axis=0);confidence=scores.max(axis=0)
    candidates=[]
    for index,category in enumerate(categories):
        name=manifest['classes'][int(category)]
        if confidence[index]<manifest.get('class_thresholds',{}).get(name,manifest.get('threshold',.35)):continue
        x,y,w,h=output[0,:4,index]
        if w<=0 or h<=0:continue
        box=[max(0,float((x-w/2-left)/new_width)),max(0,float((y-h/2-top)/new_height)),
             min(1,float((x+w/2-left)/new_width)),min(1,float((y+h/2-top)/new_height))]
        if box[2]<=box[0] or box[3]<=box[1]:continue
        candidates.append({'category':name,'bbox':box,'score':float(confidence[index])})
    if len(candidates)>5000:raise ValueError('Too many detection candidates')
    selected=[]
    for candidate in sorted(candidates,key=lambda row:-row['score']):
        if any(row['category']==candidate['category'] and _overlap(row['bbox'],candidate['bbox'])>manifest.get('iou_threshold',.5) for row in selected):continue
        selected.append(candidate)
    objects=[]
    for row in selected:
        box=row['bbox'];category=row['category']
        identity=hashlib.sha256(json.dumps([manifest['model_sha256'],page,category,box]).encode()).hexdigest()[:18]
        objects.append({**row,'id':'detector-'+identity,'type':category,'label':category.title()+' detector candidate',
                        'page':page,'document_id':document_id,'point':[(box[0]+box[2])/2,(box[1]+box[3])/2],
                        'evidence_kind':'visual','source_verified':False,'location_kind':'detected_box','extent_estimated':True})
    return {'objects':objects,'model_sha256':manifest['model_sha256'],'name':manifest.get('name','Symbol detector'),
            'training_domain':manifest.get('training_domain','Unknown'),'calibrated':False,'abstained':not objects,
            'duration_ms':round((time.monotonic()-started)*1000),'revision':REVISION}

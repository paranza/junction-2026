"""CPU inference for a checksum-pinned PlanNet model. No answer keys or filename rules."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from functools import lru_cache
from pathlib import Path

REVISION = 'plannet-onnx-v1'
_lock = threading.Lock()


def _manifest():
    value=os.environ.get('STOA_DETECTOR_MANIFEST','').strip()
    if not value:return None
    path=Path(value).expanduser().resolve()
    manifest=json.loads(path.read_text())
    model=(path.parent/manifest['model_file']).resolve()
    if model.parent!=path.parent or manifest.get('kind')!='plannet_heatmap':
        raise ValueError('Unsupported detector manifest')
    checksum=hashlib.sha256(model.read_bytes()).hexdigest()
    if checksum!=manifest.get('model_sha256'):
        raise ValueError('Detector checksum mismatch')
    if not 0<float(manifest.get('threshold',.35))<1:
        raise ValueError('Invalid detector threshold')
    classes=manifest.get('classes')
    if not isinstance(classes,list) or not classes or len(set(classes))!=len(classes) or any(not isinstance(c,str) for c in classes):
        raise ValueError('Invalid class mapping')
    return {**manifest,'path':str(model)}


def signature():
    try:
        manifest=_manifest()
        return {'revision':REVISION,'model_sha256':manifest['model_sha256'],
                'threshold':manifest.get('threshold',.35),'classes':manifest['classes']} if manifest else None
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
        if width*height>6_000_000:raise ValueError('Detector image too large')
        session=_session(manifest['path'],manifest['model_sha256'])
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

"""Calibrate exactly the deployment decoder on external validation, never confirmation."""
import argparse,hashlib,importlib.util,json,time
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from ultralytics import YOLO
from validate_yolo import metrics

class TorchSession:
    def __init__(self,model):self.model=model.cuda().float().eval()
    def get_inputs(self):return [type('Input',(),{'name':'images'})()]
    def run(self,_,inputs):
        with torch.inference_mode():
            output=self.model(torch.from_numpy(inputs['images']).contiguous().cuda())
            if isinstance(output,tuple):output=output[0]
            return [output.float().cpu().numpy()]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--weights',type=Path,required=True)
    p.add_argument('--runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--imgsz',type=int,default=1280);a=p.parse_args()
    if a.output.exists():raise ValueError('Do not replace a frozen calibration')
    if not torch.cuda.is_available():raise ValueError('This validation run requires CUDA')
    spec=importlib.util.spec_from_file_location('deployment_decoder',a.runtime);runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
    provenance=json.loads((a.root/'provenance.json').read_text())
    weights_hash=hashlib.sha256(a.weights.read_bytes()).hexdigest()
    session=TorchSession(YOLO(str(a.weights)).model)
    base={'kind':'yolo_boxes','model_sha256':weights_hash,'classes':['door','window'],'input_size':a.imgsz,
          'color_mode':provenance['color_mode'],'threshold':.05,'iou_threshold':.5}
    modes={};thresholds=[.05,.1,.15,.2,.25,.3,.4,.5,.6,.7,.8]
    for mode in ['full_page','native_tiles']:
        rows=[];started=time.monotonic()
        for path in sorted((a.root/'images/val').glob('*.png')):
            truth=[]
            for line in (a.root/'labels/val'/path.with_suffix('.txt').name).read_text().splitlines():
                c,x,y,w,h=map(float,line.split());truth.append({'category':int(c),'bbox':[x-w/2,y-h/2,x+w/2,y+h/2]})
            with Image.open(path) as image:
                result=runtime._detect_boxes(image,session,{**base,'inference_mode':mode},path.stem,1,time.monotonic())
            objects=[{'category':base['classes'].index(o['category']),'bbox':o['bbox'],'score':o['score']} for o in result['objects']]
            rows.append({'image':path.name,'truth':truth,'objects':objects})
            if len(rows)%16==0:print(json.dumps({'mode':mode,'images':len(rows),'seconds':round(time.monotonic()-started)}),flush=True)
        grid={str(c):{str(t):metrics(rows,c,t) for t in thresholds} for c in (0,1)}
        selected={str(c):max(thresholds,key=lambda t:(grid[str(c)][str(t)]['exact_counts'],-grid[str(c)][str(t)]['absolute_count_error'],t)) for c in (0,1)}
        chosen={str(c):grid[str(c)][str(selected[str(c)])] for c in (0,1)}
        modes[mode]={'thresholds':selected,'selected_metrics':chosen,'grid':grid,'rows':rows,'duration_seconds':time.monotonic()-started}
    winner=max(modes,key=lambda mode:(sum(v['exact_counts'] for v in modes[mode]['selected_metrics'].values()),-sum(v['absolute_count_error'] for v in modes[mode]['selected_metrics'].values()),mode=='full_page'))
    report={'weights_sha256':weights_hash,'runtime_sha256':hashlib.sha256(a.runtime.read_bytes()).hexdigest(),
            'dataset_manifest_sha256':hashlib.sha256((a.root/'provenance.json').read_bytes()).hexdigest(),
            'images':len(modes[winner]['rows']),'thresholds':modes[winner]['thresholds'],'selected_metrics':modes[winner]['selected_metrics'],
            'inference':{**base,'inference_mode':winner},'modes':modes,'confirmation_scored':False,'frozen_at':time.time()}
    a.output.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ['images','thresholds','selected_metrics','inference','confirmation_scored']}),flush=True)
if __name__=='__main__':main()

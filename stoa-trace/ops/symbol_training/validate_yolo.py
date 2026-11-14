"""Freeze thresholds using external validation, before confirmation scoring."""
import argparse,csv,hashlib,json,time
from pathlib import Path
import numpy as np
from ultralytics import YOLO

def iou(a,b):
 x0,y0=max(a[0],b[0]),max(a[1],b[1]);x1,y1=min(a[2],b[2]),min(a[3],b[3])
 overlap=max(0,x1-x0)*max(0,y1-y0)
 return overlap/max(1e-12,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-overlap)
def metrics(rows,category,threshold):
 result={'exact_counts':0,'cases':len(rows),'absolute_count_error':0,'true_positive_iou50':0,'false_positive_iou50':0,'false_negative_iou50':0}
 for row in rows:
  gt=[o['bbox'] for o in row['truth'] if o['category']==category]
  predictions=sorted([o for o in row['objects'] if o['category']==category and o['score']>=threshold],key=lambda o:-o['score'])
  result['exact_counts']+=int(len(gt)==len(predictions));result['absolute_count_error']+=abs(len(gt)-len(predictions))
  unmatched=set(range(len(gt)))
  for pred in predictions:
   best=max(unmatched,key=lambda k:iou(pred['bbox'],gt[k]),default=None)
   if best is not None and iou(pred['bbox'],gt[best])>=.5:result['true_positive_iou50']+=1;unmatched.remove(best)
   else:result['false_positive_iou50']+=1
  result['false_negative_iou50']+=len(unmatched)
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--weights',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--imgsz',type=int,default=1024);a=p.parse_args()
 if not 320<=a.imgsz<=1536 or a.imgsz%32:raise ValueError('Invalid inference size')
 if a.output.exists():raise ValueError('Refusing to replace frozen validation')
 model=YOLO(str(a.weights));paths=sorted((a.root/'images/val').glob('*.png'));rows=[]
 for prediction in model.predict([str(p) for p in paths],imgsz=a.imgsz,device=0,conf=.01,iou=.5,max_det=1000,verbose=False,stream=True):
  image=Path(prediction.path);truth=[]
  for line in (a.root/'labels/val'/image.with_suffix('.txt').name).read_text().splitlines():
   c,x,y,w,h=map(float,line.split());truth.append({'category':int(c),'bbox':[x-w/2,y-h/2,x+w/2,y+h/2]})
  objects=[{'category':int(c),'bbox':[float(v) for v in b],'score':float(s)} for c,b,s in zip(prediction.boxes.cls.cpu().tolist(),prediction.boxes.xyxyn.cpu().tolist(),prediction.boxes.conf.cpu().tolist())]
  rows.append({'image':image.name,'truth':truth,'objects':objects})
 thresholds=[.05,.1,.15,.2,.25,.3,.4,.5,.6,.7,.8]
 all_metrics={str(c):{str(t):metrics(rows,c,t) for t in thresholds} for c in (0,1)}
 selected={str(c):max(thresholds,key=lambda t:(all_metrics[str(c)][str(t)]['exact_counts'],-all_metrics[str(c)][str(t)]['absolute_count_error'],t)) for c in (0,1)}
 report={'weights_sha256':hashlib.sha256(a.weights.read_bytes()).hexdigest(),'dataset_manifest_sha256':hashlib.sha256((a.root/'provenance.json').read_bytes()).hexdigest(),'images':len(rows),'thresholds':selected,'selected_metrics':{str(c):all_metrics[str(c)][str(selected[str(c)])] for c in (0,1)},'grid':all_metrics,'inference':{'imgsz':a.imgsz,'iou':.5,'max_det':1000},'frozen_at':time.time(),'confirmation_scored':False,'rows':rows}
 a.output.write_text(json.dumps(report,indent=2));print(json.dumps({k:report[k] for k in ['images','thresholds','selected_metrics','weights_sha256','confirmation_scored']}))
if __name__=='__main__':main()

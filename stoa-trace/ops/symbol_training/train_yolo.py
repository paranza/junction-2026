"""Frozen transfer-learning experiment. External train/validation only."""
import argparse,hashlib,json,time,platform
from pathlib import Path
import torch,ultralytics
from ultralytics import YOLO
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,default=Path('/srv/metria-training'))
parser.add_argument('--experiment',choices=['v1','v2'],default='v1')
args=parser.parse_args()
root=args.root
if (root/'configuration.json').exists():raise ValueError('Use a fresh training root')
if not torch.cuda.is_available():raise RuntimeError('CUDA required on this training host')
config={'architecture':'yolo11s.pt','pretrained':True,'epochs':60,'imgsz':1024,'batch':4,'seed':8127,'device':0,'workers':2,'patience':60,'optimizer':'AdamW','lr0':.001,'cos_lr':True,'mosaic':.5,'close_mosaic':10,'degrees':90,'fliplr':.5,'flipud':.5,'scale':.3,'translate':.1,'hsv_h':0,'hsv_s':0,'hsv_v':.2,'cache':False,'amp':True,'deterministic':True,'save_period':10,'plots':False,'project':str(root/'runs'),'name':'yolo11s-external-v1','exist_ok':False,'data':str(root/'data/data.yaml')}
if args.experiment=='v2':
 config.update(epochs=80,time=1.2,imgsz=1280,batch=8,cache='disk',mosaic=0.,close_mosaic=0,degrees=0.,name='yolo11s-external-v2')
dataset=json.loads((root/'data/provenance.json').read_text())
if args.experiment=='v2' and dataset.get('color_mode')!='rgb':raise ValueError('V2 requires matched RGB source preprocessing')
for record in dataset['records']:
 for kind,suffix,key in [('images','.png','derived_image_sha256'),('labels','.txt','derived_label_sha256')]:
  if key not in record:
   if args.experiment=='v2':raise ValueError('Missing derived source hash')
   continue
  path=root/'data'/kind/record['split']/(record['name']+suffix)
  if hashlib.sha256(path.read_bytes()).hexdigest()!=record[key]:raise ValueError('Training file checksum mismatch')
provenance={'configuration':dict(config),'torch':torch.__version__,'ultralytics':ultralytics.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'dataset_manifest_sha256':hashlib.sha256((root/'data/provenance.json').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'started_at':time.time(),'platform':platform.platform()}
provenance['color_mode']=dataset.get('color_mode','grayscale')
(root/'configuration.json').write_text(json.dumps(provenance,indent=2))
model=YOLO(config.pop('architecture'))
weights=Path('yolo11s.pt')
if weights.exists():provenance['pretrained_sha256']=hashlib.sha256(weights.read_bytes()).hexdigest();(root/'configuration.json').write_text(json.dumps(provenance,indent=2))
model.train(**config)
(root/'TRAINING_COMPLETE').write_text(str(time.time()))

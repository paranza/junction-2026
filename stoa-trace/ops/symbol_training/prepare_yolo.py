"""Prepare external train/validation only; never open confirmation annotations."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).parent))
from data import load_sample

def prepare(root,output,runtime_root=None,rgb=False):
 root,output=Path(root),Path(output)
 if output.exists():raise ValueError('Use a fresh export directory')
 selection=json.loads((root/'selection.json').read_text())
 if set(selection['train'])&set(selection['validation']):raise ValueError('Split overlap')
 records=[]
 for source_split,dest_split in [('train','train'),('validation','val')]:
  for kind in ['images','labels']:(output/kind/dest_split).mkdir(parents=True,exist_ok=True)
  for folder in selection[source_split]:
   image,objects=load_sample(root,folder)
   name=hashlib.sha256(folder.encode()).hexdigest()[:20]
   # Preserve source pixels and line geometry. PNGs are converted to RGB only.
   if rgb:
    with Image.open(root/folder/'F1_scaled.png') as original:original.convert('RGB').save(output/'images'/dest_split/(name+'.png'))
   else:image.convert('RGB').save(output/'images'/dest_split/(name+'.png'))
   rows=[]
   for obj in objects:
    x0,y0,x1,y1=obj['bbox'];w,h=image.size
    rows.append(f"{obj['category']} {(x0+x1)/2/w:.9f} {(y0+y1)/2/h:.9f} {(x1-x0)/w:.9f} {(y1-y0)/h:.9f}")
   (output/'labels'/dest_split/(name+'.txt')).write_text('\n'.join(rows)+'\n')
   records.append({'split':dest_split,'name':name,'source_folder':folder,'image_sha256':hashlib.sha256((root/folder/'F1_scaled.png').read_bytes()).hexdigest(),'annotation_sha256':hashlib.sha256((root/folder/'model.svg').read_bytes()).hexdigest(),'derived_image_sha256':hashlib.sha256((output/'images'/dest_split/(name+'.png')).read_bytes()).hexdigest(),'derived_label_sha256':hashlib.sha256((output/'labels'/dest_split/(name+'.txt')).read_bytes()).hexdigest(),'objects':len(objects)})
 (output/'data.yaml').write_text(f'path: {runtime_root or output.resolve()}\ntrain: images/train\nval: images/val\nnames:\n  0: door\n  1: window\n')
 (output/'provenance.json').write_text(json.dumps({'selection_sha256':hashlib.sha256((root/'selection.json').read_bytes()).hexdigest(),'source':selection['source'],'license':selection['license'],'color_mode':'rgb' if rgb else 'grayscale','confirmation_exported':False,'records':records},indent=2))
 (output/'READY').write_text(hashlib.sha256((output/'provenance.json').read_bytes()).hexdigest()+'\n')
 print(json.dumps({'train':len(selection['train']),'validation':len(selection['validation']),'confirmation_exported':False}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',required=True);p.add_argument('--output',required=True);p.add_argument('--runtime-root');p.add_argument('--rgb',action='store_true');a=p.parse_args();prepare(a.data,a.output,a.runtime_root,a.rgb)

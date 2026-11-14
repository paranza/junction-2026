"""Train a bounded visual detector; select checkpoints on external validation only."""
import argparse
import hashlib
import json
import random
import time
from pathlib import Path
import sys

import numpy as np
import torch
from torch.nn import functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import SymbolNet
from data import TrainingData, load_sample


def loss_for(model, tensors):
    image, target, sizes, mask, segmentation = tensors
    logits, predicted_size, semantic = model(image)
    probability = logits.sigmoid().clamp(1e-5, 1-1e-5)
    positive = target.eq(1).float()
    negative = target.lt(1).float()
    count = positive.sum().clamp(min=1)
    center_loss = -(positive * (1-probability).pow(2) * probability.log()
                    + negative * (1-target).pow(4) * probability.pow(2) * (1-probability).log()).sum()/count
    size_mask = mask.repeat_interleave(2, dim=1)
    size_loss = (F.smooth_l1_loss(predicted_size, sizes, reduction='none')*size_mask).sum()/size_mask.sum().clamp(min=1)
    weights = torch.tensor([.1,1.,1.],device=image.device)
    semantic_loss = F.cross_entropy(semantic,segmentation,weight=weights)
    return center_loss+.2*size_loss+.2*semantic_loss, center_loss, size_loss


def infer(model, image, device='cpu', threshold=.35, size=320, core=192, maximum=1200):
    from PIL import Image
    source = image.convert('L').copy()
    source.thumbnail((maximum,maximum),Image.Resampling.LANCZOS)
    width,height=source.size
    values=1-np.asarray(source,dtype=np.float32)/255
    heat=np.zeros((2,height,width),np.float32)
    sizes=np.zeros((4,height,width),np.float32)
    jobs=[]
    margin=(size-core)//2
    for top in range(0,height,core):
        for left in range(0,width,core):
            tile=np.zeros((1,size,size),np.float32)
            ya,xa=max(0,top-margin),max(0,left-margin)
            yb,xb=min(height,top+core+margin),min(width,left+core+margin)
            # At outer boundaries keep the same context position as the padded page.
            oy,ox=ya-(top-margin),xa-(left-margin)
            tile[:,oy:oy+yb-ya,ox:ox+xb-xa]=values[ya:yb,xa:xb]
            jobs.append((top,left,tile))
    with torch.inference_mode():
        for start in range(0,len(jobs),4):
            batch=jobs[start:start+4]
            prediction,extent,_=model(torch.from_numpy(np.stack([j[2] for j in batch])).to(device))
            probability=prediction.sigmoid().cpu().numpy();extent=extent.clamp(0,7).exp().cpu().numpy()
            for k,(top,left,_) in enumerate(batch):
                h,w=min(core,height-top),min(core,width-left)
                heat[:,top:top+h,left:left+w]=probability[k,:,margin:margin+h,margin:margin+w]
                sizes[:,top:top+h,left:left+w]=extent[k,:,margin:margin+h,margin:margin+w]
    maxima=F.max_pool2d(torch.from_numpy(heat)[None],5,1,2)[0].numpy()
    points=np.argwhere((heat==maxima)&(heat>=threshold))
    if len(points)>3000: raise ValueError('Too many detector candidates')
    objects=[]
    for category,y,x in points:
        w,h=sizes[category*2:category*2+2,y,x]
        box=[max(0,(x-w/2)/width),max(0,(y-h/2)/height),min(1,(x+w/2)/width),min(1,(y+h/2)/height)]
        objects.append({'category':int(category),'bbox':[float(v) for v in box],'score':float(heat[category,y,x])})
    return objects


def validate(model, root, folders, device):
    complete=[f for f in folders if (root/f/'model.svg').exists() and (root/f/'F1_scaled.png').exists()]
    if len(complete)!=len(folders):return None
    totals={str(t):{'exact':0,'absolute_error':0,'cases':0} for t in (.05,.1,.15,.25,.35,.5)}
    model.eval()
    for folder in complete:
        image,truth=load_sample(root,folder)
        found=infer(model,image,device,.05)
        for threshold in (.05,.1,.15,.25,.35,.5):
            for category in (0,1):
                expected=sum(o['category']==category for o in truth)
                actual=sum(o['category']==category and o['score']>=threshold for o in found)
                m=totals[str(threshold)];m['cases']+=1;m['exact']+=int(expected==actual);m['absolute_error']+=abs(expected-actual)
    model.train()
    threshold=max(totals,key=lambda k:(totals[k]['exact'],-totals[k]['absolute_error']))
    return {'threshold':float(threshold),'metrics':totals,'selected':totals[threshold]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--steps',type=int,default=1600)
    parser.add_argument('--batch',type=int,default=2)
    parser.add_argument('--validate-every',type=int,default=400)
    parser.add_argument('--seed',type=int,default=8127)
    args=parser.parse_args()
    if (args.output/'configuration.json').exists():
        raise ValueError('Use a fresh output directory for a new training run')
    args.output.mkdir(parents=True,exist_ok=True)
    selection=json.loads((args.data/'selection.json').read_text())
    for folder in selection['train']+selection['validation']:
        if not (args.data/folder/'F1_scaled.png').exists() or not (args.data/folder/'model.svg').exists():
            raise ValueError('The frozen external training and validation files must all be present before training.')
    assert not set(selection['train'])&set(selection['validation'])
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed);torch.set_num_threads(2)
    device='cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')
    model=SymbolNet().to(device)
    dataset=TrainingData(args.data,selection['train'],seed=args.seed)
    optimizer=torch.optim.AdamW(model.parameters(),lr=4e-4,weight_decay=1e-4)
    configuration={**vars(args),'data':str(args.data),'output':str(args.output),'device':device,
                   'selection_sha256':hashlib.sha256((args.data/'selection.json').read_bytes()).hexdigest(),
                   'training_source':'CubiCasa5K external annotations, all Junction preview IDs excluded',
                   'source_code_sha256':{name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in ('model.py','data.py','train.py')},
                   'pretrained':False,'classes':['door','window'],'model_parameters':sum(p.numel() for p in model.parameters())}
    (args.output/'configuration.json').write_text(json.dumps(configuration,indent=2))
    best=(-1,float('-inf'));started=time.monotonic();model.train();history=[]
    for step in range(1,args.steps+1):
        samples=[dataset.sample() for _ in range(args.batch)]
        tensors=[torch.stack([s[i] for s in samples]).to(device) for i in range(5)]
        optimizer.zero_grad(set_to_none=True)
        loss,center,size=loss_for(model,tensors)
        if not torch.isfinite(loss):raise ValueError('Non-finite training loss')
        loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),10);optimizer.step()
        if step%25==0:
            print(json.dumps({'step':step,'loss':round(loss.item(),3),'center_loss':round(center.item(),3),'size_loss':round(size.item(),3),'available_training_images':len(dataset.available()),'seconds':round(time.monotonic()-started)}),flush=True)
        if step%args.validate_every==0 or step==args.steps:
            checkpoint={'model_state':{k:v.detach().cpu() for k,v in model.state_dict().items()},'step':step,'configuration':configuration}
            torch.save(checkpoint,args.output/'latest.pt')
            result=validate(model,args.data,selection['validation'],device)
            if result:
                history.append({'step':step,**result})
                metric=(result['selected']['exact'],-result['selected']['absolute_error'])
                if metric>best:
                    best=metric;checkpoint['validation']=result;torch.save(checkpoint,args.output/'best.pt')
                (args.output/'validation.json').write_text(json.dumps(history,indent=2))
                print(json.dumps({'validation_step':step,**result}),flush=True)
    if not (args.output/'best.pt').exists():raise ValueError('External validation did not finish; candidate is not frozen')
    print('Training and external selection complete',flush=True)


if __name__=='__main__':main()

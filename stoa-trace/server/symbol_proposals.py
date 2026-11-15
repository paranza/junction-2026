"""Source-example symbol discovery, never an automatically accepted count.

Examples come from objects located on the current drawing. Rotated visual
similarity proposes missing locations for a semantic source audit. There are
no stored drawing profiles, class templates, learned answers or target counts.
"""
from dataclasses import dataclass
import math
import numpy as np
from PIL import Image


@dataclass
class Example:
    image: Image.Image
    label: str
    feature: np.ndarray


def valid_box(value):
    return (isinstance(value,list) and len(value)==4 and
        all(type(v) in (int,float) and math.isfinite(v) for v in value) and
        0<=value[0]<value[2]<=1 and 0<=value[1]<value[3]<=1)


def examples(image,items,source_scale=1):
    import cv2
    result=[]
    for item in items:
        b=item.get('bbox')
        if not valid_box(b):continue
        x,y,r,s=[round(v*(image.width if i%2==0 else image.height)) for i,v in enumerate(b)]
        w,h=r-x,s-y
        if min(w,h)<6 or max(w,h)*source_scale>180 or not .25<=w/h<=4:continue
        pad=max(5,round(max(w,h)*.45))
        left,top=max(0,x-pad),max(0,y-pad)
        patch=image.crop((left,top,min(image.width,r+pad),min(image.height,s+pad))).convert('L');gray=np.asarray(patch)
        if gray.std()<8:continue
        ink=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]
        count,labels,stats,_=cv2.connectedComponentsWithStats(ink,connectivity=8)
        candidates=[]
        for index in range(1,count):
            xx,yy,ww,hh,area=stats[index]
            # A misplaced model box can contain just a table edge. It must not
            # turn that line into a high-scoring "chair" template everywhere.
            if min(ww,hh)<6 or max(ww,hh)*source_scale>180 or not .25<=ww/hh<=4:continue
            if xx==0 or yy==0 or xx+ww>=gray.shape[1] or yy+hh>=gray.shape[0]:continue
            inside=int(np.sum(labels[max(0,y-top):s-top,max(0,x-left):r-left]==index))
            if inside and inside>=.3*area:candidates.append((inside,index))
        if not candidates:continue
        _,chosen=max(candidates);xx,yy,ww,hh,_=stats[chosen]
        mask=cv2.dilate((labels==chosen).astype(np.uint8),np.ones((3,3),np.uint8))
        isolated=np.where(mask,gray,255).astype(np.uint8)
        patch=Image.fromarray(isolated).crop((max(0,xx-2),max(0,yy-2),
                                             min(gray.shape[1],xx+ww+2),min(gray.shape[0],yy+hh+2)))
        native=patch.resize((max(6,round(patch.width*source_scale)),max(6,round(patch.height*source_scale))),Image.Resampling.LANCZOS)
        side=max(native.size)+4;square=Image.new('L',(side,side),255)
        square.paste(native,((side-native.width)//2,(side-native.height)//2))
        feature=(np.asarray(square.resize((32,32),Image.Resampling.BILINEAR))<220).astype(np.uint8)
        points=cv2.findNonZero(feature)
        if points is None:continue
        filled=np.zeros_like(feature);cv2.fillConvexPoly(filled,cv2.convexHull(points),1)
        feature=filled.astype(bool)
        # Quarter turns of the same glyph are one bank exemplar, not four.
        feature=min((np.rot90(feature,k).copy() for k in range(4)),key=lambda a:np.packbits(a).tobytes())
        result.append(Example(native,str(item.get('label') or 'Source symbol'),feature))
    return result


def diverse_bank(existing,additional,maximum=12):
    bank=list(existing)
    distance=lambda a,b:float(np.mean(a.feature!=b.feature))
    for candidate in additional:
        distances=[distance(candidate,e) for e in bank]
        if distances and min(distances)<.035:continue
        if len(bank)<maximum:bank.append(candidate);continue
        # Keep a rare alternative rather than eight versions of a common seat.
        nearest=[min(distance(e,other) for j,other in enumerate(bank) if i!=j) for i,e in enumerate(bank)]
        replace=int(np.argmin(nearest))
        if min(distances)>nearest[replace]:bank[replace]=candidate
    return bank


def overlap(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return intersection/max(1e-12,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)


def discover(image,items,bank,source_scale=1,maximum=32,threshold=.84):
    import cv2
    if image.width*image.height>14_000_000:return []
    gray=np.asarray(image.convert('L')).copy()
    known=[item['bbox'] for item in items if valid_box(item.get('bbox'))]
    for b in known:
        x,y,r,s=[round(v*(image.width if i%2==0 else image.height)) for i,v in enumerate(b)]
        gray[max(0,y-2):min(image.height,s+2),max(0,x-2):min(image.width,r+2)]=255
    found=[]
    for example in bank:
        for turn in range(4):
            rotated=np.ascontiguousarray(np.rot90(np.asarray(example.image),turn))
            for scale in (.9,1.,1.1):
                sample=cv2.resize(rotated,None,fx=scale/source_scale,fy=scale/source_scale,interpolation=cv2.INTER_AREA)
                h,w=sample.shape
                if min(w,h)<5 or h>gray.shape[0] or w>gray.shape[1] or sample.std()<8:continue
                scores=cv2.matchTemplate(gray,sample,cv2.TM_CCOEFF_NORMED)
                # One dilation finds local maxima without repeatedly scanning
                # the complete high-resolution score map for every candidate.
                peaks=(scores>=threshold)&(scores==cv2.dilate(scores,np.ones((max(3,h//2),max(3,w//2)),np.uint8)))
                yy,xx=np.where(peaks)
                order=np.argsort(scores[yy,xx])[-maximum:][::-1]
                for index in order:
                    x,y=int(xx[index]),int(yy[index]);b=[x/image.width,y/image.height,(x+w)/image.width,(y+h)/image.height]
                    if any(overlap(b,k)>.2 for k in known):continue
                    found.append({'bbox':b,'label':'Visual similarity proposal: '+example.label,
                                  'similarity':float(scores[y,x]),'proposal_only':True})
    selected=[]
    for item in sorted(found,key=lambda e:-e['similarity']):
        if not any(overlap(item['bbox'],e['bbox'])>.3 for e in selected):selected.append(item)
        if len(selected)>=maximum:break
    return selected


def source_style(image,items):
    """Estimate this drawing's object line style, without a class color prior."""
    hist=np.zeros(256,dtype=np.int64);spans=[];unsupported=[]
    for index,item in enumerate(items):
        b=item.get('bbox')
        if not valid_box(b):continue
        x,y,r,s=[round(v*(image.width if i%2==0 else image.height)) for i,v in enumerate(b)]
        if min(r-x,s-y)<3:continue
        gray=np.asarray(image.crop((x,y,r,s)).convert('L'))
        yy,xx=np.where(gray<245)
        if not len(xx) or np.ptp(xx)<.3*(r-x) or np.ptp(yy)<.3*(s-y):
            unsupported.append(index);continue
        hist+=np.bincount(gray[gray<245],minlength=256)
        spans.append(max(r-x,s-y))
    level=int(np.searchsorted(np.cumsum(hist),hist.sum()/2)) if hist.sum() else 0
    return {'ink_level':level,'span':float(np.median(spans)) if spans else 40.,'unsupported_ids':unsupported}


def unclaimed_components(image,items,style,source_scale=1,maximum=32):
    """Propose novel compact shapes, including styles absent from the examples.

    Components are merely source locators. A table pedestal, text character or
    furniture outline still needs the question's semantic audit before counting.
    """
    import cv2
    gray=np.asarray(image.convert('L'));span=style['span']/source_scale
    level=style['ink_level'];low=max(0,level-45) if level>70 else 0
    mask=((gray>=low)&(gray<245)).astype(np.uint8)
    count,_,stats,_=cv2.connectedComponentsWithStats(mask,connectivity=8)
    known=[e['bbox'] for e in items if valid_box(e.get('bbox'))];found=[]
    def add(x,y,w,h,area,kind):
        long=max(w,h)
        if min(w,h)<max(5,span*.15) or not span*.45<=long<=span*2.2 or not .3<=w/h<=3.3:return
        if area<12 or (kind=='source_component' and area/(w*h)>.7):return
        if level>70:
            patch=gray[max(0,y-3):min(image.height,y+h+3),max(0,x-3):min(image.width,x+w+3)]
            drawn=patch[patch<245]
            # Antialias fringes of black walls/stair grids can match a gray
            # furniture palette. Inspect the actual neighboring ink as well.
            if len(drawn) and np.mean(drawn<low)>.35:return
        b=[x/image.width,y/image.height,(x+w)/image.width,(y+h)/image.height]
        cx,cy=x+w/2,y+h/2
        if any(overlap(b,k)>.2 or math.hypot(cx-(k[0]+k[2])/2*image.width,cy-(k[1]+k[3])/2*image.height)
               <.65*max(long,(k[2]-k[0])*image.width,(k[3]-k[1])*image.height) for k in known):return
        magnitude=area if kind=='source_component' else 2*math.sqrt(area)
        score=float(magnitude*min(long,span)/max(long,span))
        found.append({'bbox':b,'label':'Unclaimed compact source form','proposal_kind':kind,
                      'proposal_only':True,'proposal_score':score})
    for index in range(1,count):add(*map(int,stats[index]),'source_component')
    # A chair can touch its desk, making both one connected ink component.
    # Enclosed source forms preserve the distinct outlined bodies in that case.
    contours,hierarchy=cv2.findContours(mask,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    for index,contour in enumerate(contours):
        if hierarchy[0,index,3]<0:continue
        x,y,w,h=cv2.boundingRect(contour)
        if max(w,h)>span*2.2 or min(w,h)<max(5,span*.15):continue
        local=np.zeros((h,w),np.uint8);cv2.drawContours(local,[contour-np.array([[[x,y]]])],-1,1,cv2.FILLED)
        pixels=gray[y:y+h,x:x+w][local>0]
        if not len(pixels) or np.mean(pixels>=245)<.6:continue
        add(x,y,w,h,float(cv2.contourArea(contour)),'enclosed_source_form')
    selected=[]
    for item in sorted(found,key=lambda e:-e['proposal_score']):
        if not any(overlap(item['bbox'],e['bbox'])>.5 for e in selected):selected.append(item)
        if len(selected)>=maximum:break
    return selected

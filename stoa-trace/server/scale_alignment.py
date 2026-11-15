"""Locate a nearby checker scale's pixel endpoints, without inferring its units.

Only a unique enclosed, complementary two-band checker pattern qualifies. Plain
lines, dimensions, text and ambiguous neighbouring bars retain the model's
original reference and its visual-review requirement.
"""
import math
from pathlib import Path
import numpy as np
from . import rendering


def checker_endpoints(image, points):
    import cv2
    a,b=np.asarray(points,dtype=float)
    length=float(np.linalg.norm(b-a))
    if length<40:return None
    delta=np.abs(b-a)
    vertical=delta[1]>delta[0]
    if min(delta)/max(delta)>.035:return None
    mask=(np.asarray(image.convert('L'))<160).astype(np.uint8)
    if vertical:mask=mask.T;a=a[::-1];b=b[::-1]
    _,_,stats,_=cv2.connectedComponentsWithStats(mask,connectivity=8)
    found=[]
    for x,y,w,h,area in stats[1:]:
        if x<=0 or y<=0 or x+w>=mask.shape[1] or y+h>=mask.shape[0]:continue
        if not .85*length<=w<=1.15*length or not max(4,.005*w)<=h<=.15*w:continue
        if not .15<=area/(w*h)<=.9:continue
        patch=mask[y:y+h,x:x+w]
        if min(patch[:3].mean(axis=1).max(),patch[-3:].mean(axis=1).max(),
               patch[:,:3].mean(axis=0).max(),patch[:,-3:].mean(axis=0).max())<.85:continue
        upper=patch[max(1,int(h*.15)):max(2,int(h*.45)),3:-3].mean(axis=0)
        lower=patch[int(h*.55):min(h-1,max(int(h*.55)+1,int(h*.85))),3:-3].mean(axis=0)
        supported=((upper>.85)&(lower<.15))|((upper<.15)&(lower>.85))
        transitions=np.flatnonzero(np.diff((upper>.5).astype(np.int8)))
        if supported.mean()<.8 or len(transitions)<2:continue
        ends=np.array([[x,y+(h-1)/2],[x+w-1,y+(h-1)/2]],dtype=float)
        if a[0]>b[0]:ends=ends[::-1]
        if np.max(np.linalg.norm(ends-np.array([a,b]),axis=1))>.08*length:continue
        if vertical:ends=ends[:,::-1]
        found.append({'points':ends.tolist(),'pattern_support':float(supported.mean()),
                      'method':'source_checker_bar_edges'})
    return found[0] if len(found)==1 else None


def align_reference(path, page, points):
    path=Path(path)
    if path.suffix.lower() not in rendering.RASTER_SUFFIXES:return None
    meta=rendering.raster_metadata(path)[0][page-1];width,height=meta['width'],meta['height']
    pixels=np.asarray(points)*[width,height]
    length=float(np.linalg.norm(pixels[1]-pixels[0]));margin=max(12,length*.12)
    left=max(0,math.floor(pixels[:,0].min()-margin));right=min(width,math.ceil(pixels[:,0].max()+margin))
    top=max(0,math.floor(pixels[:,1].min()-margin));bottom=min(height,math.ceil(pixels[:,1].max()+margin))
    if min(right-left,bottom-top)<4:return None
    region=[left/width,top/height,right/width,bottom/height]
    image=rendering.render_region(path,page,region,1800)
    factor=np.array([image.width/(right-left),image.height/(bottom-top)])
    aligned=checker_endpoints(image,(pixels-[left,top])*factor)
    if aligned is None:return None
    corrected=(np.asarray(aligned['points'])/factor+[left,top])/[width,height]
    return {**aligned,'points':corrected.tolist(),'original_points':points,
            'source_span_pixels':float(np.linalg.norm((corrected[1]-corrected[0])*[width,height]))}

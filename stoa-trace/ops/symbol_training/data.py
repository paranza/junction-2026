"""External training annotations only. Junction question labels are never read."""
import json
import math
import random
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance
import torch


def load_sample(root, folder):
    source = Path(root) / folder
    image = Image.open(source/'F1_scaled.png').convert('L')
    svg = ET.parse(source/'model.svg').getroot()
    # These annotations use F1_scaled pixel coordinates. Their SVG artboard
    # dimensions can differ from that raster. Follow the publisher's House /
    # get_points loader; rescaling through viewBox would move the labels.
    objects = []
    for group in svg.iter():
        category = {'Door': 0, 'Window': 1}.get(group.get('id'))
        if category is None: continue
        polygon = next((e for e in group if e.tag.split('}')[-1] == 'polygon'), None)
        if polygon is None: raise ValueError('Opening has no direct polygon')
        points = np.array([float(v) for v in re.split(r'[ ,]+', polygon.get('points', '').strip())]).reshape(-1, 2)
        if not np.isfinite(points).all(): raise ValueError('Non-finite opening polygon')
        box = [max(0,float(points[:, 0].min())), max(0,float(points[:, 1].min())),
               min(image.width,float(points[:, 0].max())), min(image.height,float(points[:, 1].max()))]
        if box[2] <= box[0] or box[3] <= box[1]: continue
        objects.append({'category': category, 'bbox': box})
    return image, objects


def targets(objects, size):
    heat = np.zeros((2, size, size), np.float32)
    extents = np.zeros((4, size, size), np.float32)
    mask = np.zeros((2, size, size), np.float32)
    segmentation = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(segmentation)
    for obj in objects:
        c = obj['category']; x0, y0, x1, y1 = obj['bbox']
        draw.rectangle([x0, y0, x1, y1], fill=c+1)
        x, y = int((x0+x1)/2), int((y0+y1)/2)
        if not 0 <= x < size or not 0 <= y < size: continue
        radius = max(3, min(10, int(max(x1-x0,y1-y0)*.06)))
        sigma = max(1.5, radius/2)
        xa, xb = max(0, x-radius), min(size, x+radius+1)
        ya, yb = max(0, y-radius), min(size, y+radius+1)
        yy, xx = np.mgrid[ya:yb, xa:xb]
        gaussian = np.exp(-((xx-x)**2+(yy-y)**2)/(2*sigma*sigma))
        heat[c, ya:yb, xa:xb] = np.maximum(heat[c, ya:yb, xa:xb], gaussian)
        extents[c*2:c*2+2, y, x] = np.log([max(1,x1-x0), max(1,y1-y0)])
        mask[c, y, x] = 1
    return torch.from_numpy(heat), torch.from_numpy(extents), torch.from_numpy(mask), torch.from_numpy(np.asarray(segmentation).astype(np.int64))


class TrainingData:
    def __init__(self, root, selection, size=320, seed=8127):
        self.root, self.selection, self.size = Path(root), selection, size
        self.rng = random.Random(seed)
        self.cache = {}

    def available(self):
        return [folder for folder in self.selection if (self.root/folder/'model.svg').exists() and (self.root/folder/'F1_scaled.png').exists()]

    def sample(self):
        folder = self.rng.choice(self.available())
        if folder not in self.cache: self.cache[folder] = load_sample(self.root, folder)
        original, annotations = self.cache[folder]
        scale = self.rng.uniform(.65, 1.3)
        # Keep source aspect ratio. Positive crops teach rare symbols without
        # changing labels or manufacturing objects; negative crops remain.
        image = original.resize((max(1,round(original.width*scale)), max(1,round(original.height*scale))), Image.Resampling.BILINEAR)
        size = self.size
        if annotations and self.rng.random() < .8:
            anchor = self.rng.choice(annotations)['bbox']
            left = round((anchor[0]+anchor[2])/2*scale-self.rng.uniform(.2,.8)*size)
            top = round((anchor[1]+anchor[3])/2*scale-self.rng.uniform(.2,.8)*size)
        else:
            left = self.rng.randrange(-size//2, max(1,image.width-size//2))
            top = self.rng.randrange(-size//2, max(1,image.height-size//2))
        crop = Image.new('L', (size,size), 255)
        xa,ya,xb,yb = max(0,left),max(0,top),min(image.width,left+size),min(image.height,top+size)
        if xa < xb and ya < yb:
            crop.paste(image.crop((xa,ya,xb,yb)), (xa-left,ya-top))
        objects = [{'category':o['category'],'bbox':[v*scale-(left if i%2==0 else top) for i,v in enumerate(o['bbox'])]} for o in annotations]
        turns = self.rng.randrange(4)
        if turns:
            crop = crop.rotate(90*turns)
            for obj in objects:
                x0,y0,x1,y1 = obj['bbox']
                for _ in range(turns): x0,y0,x1,y1 = y0,size-x1,y1,size-x0
                obj['bbox'] = [x0,y0,x1,y1]
        crop = ImageEnhance.Contrast(crop).enhance(self.rng.uniform(.7,1.4))
        image_tensor = torch.from_numpy(1-np.asarray(crop,dtype=np.float32)/255)[None]
        return (image_tensor, *targets(objects,size))

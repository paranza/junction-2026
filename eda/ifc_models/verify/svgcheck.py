import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import re, sys, pickle, collections, numpy as np, pandas as pd, pymupdf
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon
D=_ROOT + "/eda/ifc_models/verify/files/"
svgf=sys.argv[1]; ifc=sys.argv[2]; storey=sys.argv[3]
NS="{http://www.w3.org/2000/svg}"
root=ET.parse(D+svgf).getroot()
vb=[float(x) for x in root.get("viewBox").split()]
print("viewBox",vb,"width",root.get("width"),"height",root.get("height"))
groups=[g for g in root.iter(NS+"g") if g.get("data-guid")]
print("groups with guid",len(groups),collections.Counter(g.get("class") for g in groups))
arcs=collections.Counter(g.get("class") for g in groups for p in g.iter(NS+"path") if re.search(r"[Aa]",p.get("d")))
print("groups whose paths contain arcs",arcs)
F=pickle.load(open(f"facts_{ifc}.pkl","rb"))
prod={p["guid"]:p for p in F["products"]}
st={s["name"]:s for s in F["storeys"]}[storey]
st_space_guids={x["guid"] for x in F["spaces"] if x["id"] in set(st["space_ids"])}
st_direct={g for _,_,g in st["direct"]}
miss=[g.get("data-guid") for g in groups if g.get("data-guid") not in prod]
print("guids missing from IFC",len(miss))
cls_mismatch=sum(1 for g in groups if g.get("data-guid") in prod and prod[g.get("data-guid")]["cls"]!=g.get("class"))
print("class attr != IFC class:",cls_mismatch)
# storey ownership of drawn elements
own=collections.Counter()
for g in groups:
    gu=g.get("data-guid"); c=g.get("class")
    if c=="IfcSpace": own[(c,"on storey" if gu in st_space_guids else "OTHER")]+=1
    else:
        p=prod.get(gu)
        if gu in st_direct: own[(c,"direct on storey")]+=1
        elif p and p["dec"]: own[(c,"part of "+p["dec"][0][0]+":"+str(p["dec"][0][1]))]+=1
        else: own[(c,"OTHER: "+str(p["cont"] if p else None))]+=1
for k,v in sorted(own.items()): print("  ",v,k)
# areas: SVG polygon area *0.01 vs IFC floor area
def parse_d(d):
    toks=re.findall(r"[MLZz]|-?\d+\.?\d*(?:e-?\d+)?",d)
    rings=[];cur=[];cmd=None;i=0
    while i<len(toks):
        t=toks[i]
        if t in "MLZz":
            cmd=t; i+=1
            if t=="M":
                if cur: rings.append(cur)
                cur=[]
            if t in "Zz":
                if cur: rings.append(cur); cur=[]
            continue
        cur.append((float(toks[i]),float(toks[i+1]))); i+=2
    if cur: rings.append(cur)
    return rings
sp={x["guid"]:x for x in F["spaces"]}
rel=[]; cents=[]
for g in groups:
    if g.get("class")!="IfcSpace": continue
    acc=None
    for p in g.iter(NS+"path"):
        for r in parse_d(p.get("d")):
            if len(r)>=3:
                P=Polygon(r); acc=P if acc is None else acc.symmetric_difference(P)
    x=sp[g.get("data-guid")]
    ifc_a=x["q"].get(("BaseQuantities","NetFloorArea"),(None,None))[1] or x["g_down_at_min"]
    rel.append(abs(acc.area*0.01-x["g_down_at_min"])/x["g_down_at_min"])
    cents.append((g.get("data-guid"),acc.centroid.x,acc.centroid.y,acc.bounds))
print("space polygons: max rel diff SVG area*0.01 vs IFC floor-face area: %.2e (n=%d)"%(max(rel),len(rel)))
pickle.dump(cents,open(f"svg_cents_{svgf}.pkl","wb"))
# text labels
texts=[t.text for t in root.iter(NS+"text")]
print("n text",len(texts),texts[:4],texts[-4:])

import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pickle, numpy as np, pymupdf, ifcopenshell, ifcopenshell.util.placement as up
from shapely.geometry import Polygon, Point
D=_ROOT + "/eda/ifc_models/verify/files/"
DS=_DATA + "/data/ifc_models/"
svgf="bsc-esplanades_1807-ep-ar-v18_plan-04-4-korrus.svg"; pdff=svgf.replace(".svg",".pdf")
cents=pickle.load(open(f"svg_cents_{svgf}.pkl","rb"))
vb=(112.23,66.49)
# PDF space polygons
p=pymupdf.open(D+pdff)[0]
pdfpolys=[]
for d in p.get_drawings():
    if d.get("fill") and tuple(round(c,3) for c in d["fill"])==(0.89,0.929,0.969):
        pdfpolys.append(d["rect"])
k=72/25.4
errs=[]
for gu,cx,cy,(x0,y0,x1,y1) in cents:
    R=pymupdf.Rect((x0-vb[0])*k,(y0-vb[1])*k,(x1-vb[0])*k,(y1-vb[1])*k)
    best=min(pdfpolys,key=lambda r:abs(r.x0-R.x0)+abs(r.y0-R.y0)+abs(r.x1-R.x1)+abs(r.y1-R.y1))
    errs.append(max(abs(best.x0-R.x0),abs(best.y0-R.y0),abs(best.x1-R.x1),abs(best.y1-R.y1)))
print("PDF bbox vs mapped SVG bbox: max abs diff pt %.3f over %d spaces"%(max(errs),len(errs)))
# world centroid of the space floor face
f=ifcopenshell.open(DS+"bsc-esplanades_1807-ep-ar-v18.ifc")
W=[];S=[]
for gu,cx,cy,_ in cents:
    s=f.by_guid(gu); M=up.get_local_placement(s.ObjectPlacement)
    rep=[r for r in s.Representation.Representations if r.RepresentationIdentifier=="Body"][0]
    best=None
    for fc in rep.Items[0].Outer.CfsFaces:
        b=[x for x in fc.Bounds if x.is_a("IfcFaceOuterBound")] or list(fc.Bounds)
        pts=np.array([list(q.Coordinates) for q in b[0].Bound.Polygon],float)
        w=(M@np.c_[pts,np.ones(len(pts))].T).T[:,:3]/1000
        if np.ptp(w[:,2])<1e-6 and (best is None or w[0,2]<best[0,2]-1e-9 or (abs(w[0,2]-best[0,2])<1e-9 and Polygon(w[:,:2]).area>Polygon(best[:,:2]).area)):
            best=w
    c=Polygon(best[:,:2]).centroid
    W.append((c.x,c.y)); S.append((cx,cy))
W=np.array(W); S=np.array(S)
A=np.c_[W,np.ones(len(W))]
cx,res_x,_,_=np.linalg.lstsq(A,S[:,0],rcond=None); cy,res_y,_,_=np.linalg.lstsq(A,S[:,1],rcond=None)
pred=np.c_[A@cx,A@cy]
print("affine x' = %.6f x + %.6f y + %.4f ; y' = %.6f x + %.6f y + %.4f"%(*cx,*cy))
print("max residual (svg mm): %.2e"%np.abs(pred-S).max())

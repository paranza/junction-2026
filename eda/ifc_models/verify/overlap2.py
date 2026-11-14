import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pickle, numpy as np, ifcopenshell, ifcopenshell.util.placement as up
from shapely.geometry import Polygon
from shapely.ops import unary_union
DS=_DATA + "/data/ifc_models/"
for m in ["bsc-molio_molio-with-uris.ifc","bsc-esplanades_1807-ep-ar-v18.ifc"]:
    f=ifcopenshell.open(DS+m); F=pickle.load(open(f"facts_{m}.pkl","rb"))
    polys={}
    for s in f.by_type("IfcSpace"):
        M=up.get_local_placement(s.ObjectPlacement)
        rep=[r for r in s.Representation.Representations if r.RepresentationIdentifier=="Body"][0]
        faces=[]
        for fc in rep.Items[0].Outer.CfsFaces:
            outer=None; inner=[]
            for b in fc.Bounds:
                pts=np.array([list(q.Coordinates) for q in b.Bound.Polygon],float)
                w=(M@np.c_[pts,np.ones(len(pts))].T).T[:,:3]/1000
                if b.is_a("IfcFaceOuterBound"): outer=w
                else: inner.append(w)
            if outer is None: outer=inner.pop(0)
            faces.append((outer,inner))
        zmin=min(o[:,2].min() for o,_ in faces)
        fl=[Polygon(o[:,:2],[i[:,:2] for i in ins]).buffer(0) for o,ins in faces if np.ptp(o[:,2])<1e-6 and abs(o[0,2]-zmin)<1e-6]
        polys[s.id()]=(f"{s.LongName} ({s.Name})",unary_union(fl))
    n=0
    for st in F["storeys"]:
        ids=st["space_ids"]
        for i in ids:
            for j in ids:
                if i<j:
                    a=polys[i][1]; b=polys[j][1]; inter=a.intersection(b).area
                    if inter>0.01: n+=1; print(m[:14],st["name"],polys[i][0],round(a.area,2),"|",polys[j][0],round(b.area,2),"overlap m2",round(inter,2))
    print(m,"overlapping pairs",n)

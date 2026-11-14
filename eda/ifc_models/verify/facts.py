"""Independent per-model fact extraction (no ifcopenshell.geom, no util.shape)."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import sys, collections, pickle, time, resource
import numpy as np, ifcopenshell, ifcopenshell.util.placement as up, ifcopenshell.util.unit as uu
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union, polygonize
DS=_DATA + "/data/ifc_models/"
fn=sys.argv[1]
t0=time.time(); f=ifcopenshell.open(DS+fn); t_open=time.time()-t0
L=uu.calculate_unit_scale(f)  # project length unit -> metre
def unit_scale(utype):
    for ua in f.by_type("IfcUnitAssignment"):
        for u in ua.Units:
            if getattr(u,"UnitType",None)==utype and u.is_a("IfcSIUnit"):
                p={None:1,"MILLI":1e-3,"CENTI":1e-2,"DECI":1e-1,"KILO":1e3}[u.Prefix]
                return p**(2 if utype=="AREAUNIT" else 3 if utype=="VOLUMEUNIT" else 1)
    return 1.0
A=unit_scale("AREAUNIT"); V=unit_scale("VOLUMEUNIT")
print("scales L,A,V",L,A,V, file=sys.stderr)

def qsets(o):
    """{(setname, qtyname): value} from IfcElementQuantity attached by IfcRelDefinesByProperties; raw units."""
    out={}
    for r in getattr(o,"IsDefinedBy",[]) or []:
        if not r.is_a("IfcRelDefinesByProperties"): continue
        d=r.RelatingPropertyDefinition
        if d.is_a("IfcElementQuantity"):
            for q in d.Quantities:
                for attr in ("LengthValue","AreaValue","VolumeValue","CountValue","WeightValue"):
                    if hasattr(q,attr):
                        out[(d.Name,q.Name)]=(attr,getattr(q,attr))
        elif d.is_a("IfcPropertySet"):
            for p in d.HasProperties:
                if p.is_a("IfcPropertySingleValue"):
                    v=p.NominalValue.wrappedValue if p.NominalValue is not None else None
                    out[(d.Name,p.Name)]=("prop",v)
    return out

def newell(pts):
    n=np.zeros(3)
    for i in range(len(pts)):
        a=pts[i]; b=pts[(i+1)%len(pts)]
        n+=np.array([(a[1]-b[1])*(a[2]+b[2]),(a[2]-b[2])*(a[0]+b[0]),(a[0]-b[0])*(a[1]+b[1])])
    return n  # |n|/2 = area, direction = normal (by loop orientation)

def brep_faces(prod):
    """world-coordinate faces (list of (outer_pts, [inner_pts])) of Body FacetedBrep items, metres"""
    M=up.get_local_placement(prod.ObjectPlacement)  # 4x4 in project length units
    faces=[]
    if not prod.Representation: return faces
    for rep in prod.Representation.Representations:
        if rep.RepresentationIdentifier!="Body": continue
        for it in rep.Items:
            if not it.is_a("IfcFacetedBrep"): return None
            for fc in it.Outer.CfsFaces:
                outer=None; inners=[]
                for b in fc.Bounds:
                    pts=np.array([list(p.Coordinates)+[0.0]*(3-len(p.Coordinates)) for p in b.Bound.Polygon],float)
                    if not b.Orientation: pts=pts[::-1]
                    w=(M@np.c_[pts,np.ones(len(pts))].T).T[:,:3]*L
                    if b.is_a("IfcFaceOuterBound") and outer is None: outer=w
                    else: inners.append(w)
                if outer is None and inners: outer=inners.pop(0)
                faces.append((outer,inners))
    return faces

def floor_metrics(prod):
    faces=brep_faces(prod)
    if not faces: return {}
    zmin=min(o[:,2].min() for o,_ in faces); zmax=max(o[:,2].max() for o,_ in faces)
    down_at_min=0.0; down_all=0.0; up_at_max=0.0; horiz_at_min_abs=0.0; polys=[]
    for o,ins in faces:
        n=newell(o); a=np.linalg.norm(n)/2
        if a<=0: continue
        nz=n[2]/np.linalg.norm(n)
        ai=sum(np.linalg.norm(newell(i))/2 for i in ins)
        area=a-ai
        if abs(nz)>0.999:
            if nz<0: down_all+=area
            if abs(o[:,2].mean()-zmin)<1e-3:
                horiz_at_min_abs+=area
                if nz<0: down_at_min+=area
            if nz>0 and abs(o[:,2].mean()-zmax)<1e-3: up_at_max+=area
        if abs(nz)>1e-6:
            try:
                p=Polygon(o[:,:2],[i[:,:2] for i in ins])
                if not p.is_valid: p=p.buffer(0)
                polys.append(p)
            except Exception: pass
    proj=unary_union(polys).area if polys else None
    return {"down_at_min":down_at_min,"down_all":down_all,"horiz_at_min_abs":horiz_at_min_abs,"up_at_max":up_at_max,"proj":proj,"zmin":zmin,"zmax":zmax,"nfaces":len(faces)}

def footprint_curve_area(prod):
    if not prod.Representation: return None
    for rep in prod.Representation.Representations:
        if rep.RepresentationIdentifier!="FootPrint": continue
        M=up.get_local_placement(prod.ObjectPlacement)
        lines=[]
        for it in rep.Items:
            els=it.Elements if it.is_a("IfcGeometricCurveSet") else [it]
            for c in els:
                if c.is_a("IfcPolyline"):
                    pts=np.array([list(p.Coordinates)+[0.0]*(3-len(p.Coordinates)) for p in c.Points],float)
                    w=(M@np.c_[pts,np.ones(len(pts))].T).T[:,:2]*L
                    lines.append(LineString(w))
                else:
                    return ("unsupported",c.is_a())
        polys=list(polygonize(unary_union(lines)))
        if not polys: return None
        # area enclosed: union minus holes by even-odd: use symmetric difference accumulation
        acc=None
        for p in polys:
            acc=p if acc is None else acc.symmetric_difference(p)
        return acc.area
    return None

storeys={s.id():s for s in f.by_type("IfcBuildingStorey")}
# aggregation children of each spatial element
def agg_children(o):
    out=[]
    for r in getattr(o,"IsDecomposedBy",[]) or []:
        out+=list(r.RelatedObjects)
    return out
def contained(o):
    out=[]
    for r in getattr(o,"ContainsElements",[]) or []:
        out+=list(r.RelatedElements)
    return out

facts={"file":fn,"schema":f.schema,"t_open":t_open,"scales":(L,A,V)}
sto=[]
for s in f.by_type("IfcBuildingStorey"):
    sp=[c for c in agg_children(s) if c.is_a("IfcSpace")]
    direct=contained(s)
    in_spaces=[e for x in sp for e in contained(x)]
    sto.append({"id":s.id(),"name":s.Name,"elev":s.Elevation,"space_ids":[x.id() for x in sp],
                "direct":[(e.id(),e.is_a(),e.GlobalId) for e in direct],
                "in_spaces":[(e.id(),e.is_a(),e.GlobalId) for e in in_spaces]})
facts["storeys"]=sto
# spaces
spaces=[]
for x in f.by_type("IfcSpace"):
    parent=[r.RelatingObject for r in (x.Decomposes or [])]
    d={"id":x.id(),"guid":x.GlobalId,"Name":x.Name,"LongName":x.LongName,"parent":[(p.is_a(),p.Name) for p in parent],
       "q":qsets(x)}
    d.update({"g_"+k:v for k,v in floor_metrics(x).items()})
    d["fp_curve"]=footprint_curve_area(x)
    spaces.append(d)
facts["spaces"]=spaces
# walls and slabs with quantities
el=[]
for cls in ("IfcWall","IfcSlab"):
    for e in f.by_type(cls):
        cont=[r.RelatingStructure for r in (e.ContainedInStructure or [])]
        dec=[r.RelatingObject for r in (e.Decomposes or [])]
        el.append({"id":e.id(),"cls":e.is_a(),"guid":e.GlobalId,"name":e.Name,"cont":[(c.is_a(),c.Name,c.id()) for c in cont],
                   "dec":[(c.is_a(),c.Name) for c in dec],"q":qsets(e),
                   "has_body":bool(e.Representation and any(r.RepresentationIdentifier=="Body" for r in e.Representation.Representations)),
                   "n_parts":sum(len(r.RelatedObjects) for r in (e.IsDecomposedBy or []))})
facts["walls_slabs"]=el
# all products: class, containment, decomposition parent
prods=[]
for e in f.by_type("IfcProduct"):
    if e.is_a("IfcSpatialStructureElement") or e.is_a("IfcOpeningElement") or e.is_a("IfcAnnotation") or e.is_a("IfcGrid"): pass
    cont=[r.RelatingStructure for r in (getattr(e,"ContainedInStructure",None) or [])]
    dec=[r.RelatingObject for r in (e.Decomposes or [])] if hasattr(e,"Decomposes") else []
    typ=None
    for r in (getattr(e,"IsDefinedBy",None) or []):
        if r.is_a("IfcRelDefinesByType"): typ=r.RelatingType.is_a()
    if typ is None and hasattr(e,"IsTypedBy"):
        for r in e.IsTypedBy or []: typ=r.RelatingType.is_a()
    prods.append({"id":e.id(),"cls":e.is_a(),"guid":e.GlobalId,"name":e.Name,
                  "cont":[(c.is_a(),c.Name,c.id()) for c in cont],"dec":[(c.is_a(),c.Name,c.id()) for c in dec],"type":typ})
facts["products"]=prods
facts["maxrss_MB"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6
facts["t_total"]=time.time()-t0
pickle.dump(facts,open(f"facts_{fn}.pkl","wb"))
print(fn,"open",round(t_open,2),"total",round(facts["t_total"],1),"maxrssMB",round(facts["maxrss_MB"]), "spaces",len(spaces),"walls/slabs",len(el),"products",len(prods))

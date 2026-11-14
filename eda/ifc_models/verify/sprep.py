import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import sys, collections, ifcopenshell
DS=_DATA + "/data/ifc_models/"
f=ifcopenshell.open(DS+sys.argv[1])
c=collections.Counter()
ex=None
for s in f.by_type("IfcSpace"):
    reps=[]
    if s.Representation:
        for r in s.Representation.Representations:
            items=[i.is_a() for i in r.Items]
            sub=[]
            for i in r.Items:
                if i.is_a("IfcExtrudedAreaSolid"): sub.append(i.SweptArea.is_a())
                if i.is_a("IfcBooleanResult") or i.is_a("IfcBooleanClippingResult"): sub.append("bool:"+i.FirstOperand.is_a())
            reps.append((r.RepresentationIdentifier,r.RepresentationType,tuple(items),tuple(sub)))
    c[tuple(reps)]+=1
for k,v in c.most_common(): print(v,k)
s=f.by_type("IfcSpace")[0]
print(s)
print("CompositionType",s.CompositionType,"InteriorOrExteriorSpace",s.InteriorOrExteriorSpace,"ElevationWithFlooring",s.ElevationWithFlooring)
print(collections.Counter(x.CompositionType for x in f.by_type("IfcSpace")))

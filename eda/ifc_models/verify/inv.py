import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import sys, time, resource, os, collections, json
import ifcopenshell
DS=_DATA + "/data/ifc_models/"
fn=sys.argv[1]
t=time.time(); f=ifcopenshell.open(DS+fn); dt=time.time()-t
rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6  # macOS bytes -> MB
out={"file":fn,"schema":f.schema,"bytes":os.path.getsize(DS+fn),"open_s":round(dt,2),"maxrss_MB_after_open":round(rss)}
# header
h=f.header
try:
    out["originating_system"]=h.file_name.originating_system; out["preprocessor"]=h.file_name.preprocessor_version
    out["description"]=list(h.file_description.description)
except Exception as e: out["hdr_err"]=str(e)
# counts
n=0
for e in f: n+=1
out["n_entities"]=n
classes=["IfcProject","IfcSite","IfcBuilding","IfcBuildingStorey","IfcSpace","IfcDoor","IfcWindow","IfcWall","IfcWallStandardCase","IfcSlab","IfcColumn","IfcBeam","IfcStair","IfcStairFlight","IfcRailing","IfcRoof","IfcCovering","IfcFurnishingElement","IfcBuildingElementProxy","IfcBuildingElementPart","IfcFlowTerminal","IfcFlowSegment","IfcFlowFitting","IfcOpeningElement","IfcCurtainWall","IfcPlate","IfcMember","IfcZone"]
cnt={}
for c in classes:
    try: cnt[c+"(incl sub)"]=len(f.by_type(c))
    except Exception as e: cnt[c]="n/a"
out["counts"]=cnt
# exact class counts for walls
out["wall_exact"]=collections.Counter(e.is_a() for e in f.by_type("IfcWall"))
# units
ua=f.by_type("IfcUnitAssignment")
units=[]
for u in ua:
    for x in u.Units:
        if x.is_a("IfcSIUnit"): units.append((x.UnitType,x.Prefix,x.Name))
        elif x.is_a("IfcConversionBasedUnit"): units.append((x.UnitType,"conv",x.Name))
        else: units.append((x.is_a(),))
out["units"]=units
proj=f.by_type("IfcProject")[0]
out["project"]=(proj.Name,proj.LongName)
out["storeys"]=[(s.Name,s.Elevation) for s in f.by_type("IfcBuildingStorey")]
# property set / qto names on spaces
ps=collections.Counter()
for r in f.by_type("IfcRelDefinesByProperties"):
    d=r.RelatingPropertyDefinition
    for o in r.RelatedObjects:
        if o.is_a("IfcSpace"): ps[(d.is_a(),d.Name)]+=1
out["space_psets"]=ps.most_common(40)
print(json.dumps(out,default=str,indent=1,ensure_ascii=False))

"""Time ifcopenshell.draw for one storey and check which storeys the drawn GUIDs belong to."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import faulthandler, time, re, collections, sys
faulthandler.dump_traceback_later(300, exit=True)
import ifcopenshell, ifcopenshell.draw as d, ifcopenshell.util.element as ue
DS=_DATA + "/data/ifc_models/"
f=ifcopenshell.open(DS+"bsc-esplanades_1807-ep-ar-v18.ifc")
t=time.time()
s=d.draw_settings(auto_floorplan=True,include_projection=False,storey_filter="4.korrus",space_names=True,exclude_entities="IfcOpeningElement")
out=d.main(s,[f])
dt=time.time()-t
txt=out.decode() if isinstance(out,bytes) else out
open("drawrun/draw_esplanades_4korrus_rerun.svg","w").write(txt)
g=set(re.findall(r'ifc:guid="([^"]*)"',txt))
own=collections.Counter()
for x in g:
    try: e=f.by_guid(x)
    except Exception: own["not found"]+=1; continue
    c=ue.get_container(e) or (e.Decomposes[0].RelatingObject if getattr(e,"Decomposes",None) else None)
    own[(e.is_a() if e.is_a("IfcSpatialStructureElement") else "element", getattr(c,"Name",None))]+=1
print("draw seconds %.1f"%dt,"chars",len(txt),"unique ifc:guid",len(g))
for k,v in own.most_common(): print("  ",v,k)

import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import faulthandler, time, sys, re, collections
faulthandler.dump_traceback_later(420, exit=True)
import ifcopenshell, ifcopenshell.draw as d
DS=_DATA + "/data/ifc_models/"
t=time.time()
f=ifcopenshell.open(DS+"bsc-esplanades_1807-ep-ar-v18.ifc")
s=d.draw_settings(auto_floorplan=True,include_projection=False,storey_filter="4.korrus",space_names=True,exclude_entities="IfcOpeningElement")
out=d.main(s,[f.wrapped_data] if hasattr(f,"wrapped_data") else [f])
print("draw seconds %.1f"%(time.time()-t),"bytes",len(out))
open("draw_esplanades_4korrus.svg","wb").write(out if isinstance(out,bytes) else out.encode())
txt=out.decode() if isinstance(out,bytes) else out
cls=collections.Counter(re.findall(r'class="([^"]*)"',txt))
print(cls.most_common(15))
print("guids:",len(set(re.findall(r'data-guid="([^"]*)"',txt))), "ifc-guid like:",len(set(re.findall(r'ifc:guid="([^"]*)"',txt))))

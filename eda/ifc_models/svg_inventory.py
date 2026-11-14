import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Count IFC classes drawn in each SVG plan, list space labels, compare with IFC storey membership by GUID.
import re, os, sys, collections, pickle, json
import xml.etree.ElementTree as ET
import pandas as pd
DS = _DATA + "/data/ifc_models/"
NS = "{http://www.w3.org/2000/svg}"
out = {}
for fn in sorted(os.listdir(DS)):
    if not fn.endswith(".svg"): continue
    root = ET.parse(DS + fn).getroot()
    gs = [g for g in root.iter(NS + "g") if g.get("class")]
    cnt = collections.Counter(g.get("class") for g in gs)
    guids = collections.defaultdict(set)
    for g in gs: guids[g.get("class")].add(g.get("data-guid"))
    texts = [t.text for t in root.iter(NS + "text")]
    storeys = collections.Counter(re.match(r"storey-([0-9a-f-]+)-product", g.get("id") or "").group(1) if re.match(r"storey-([0-9a-f-]+)-product", g.get("id") or "") else None for g in gs)
    out[fn] = {"viewBox": root.get("viewBox"), "width": root.get("width"), "height": root.get("height"), "n_groups": len(gs), "class_counts": dict(cnt.most_common()),
               "unique_guid_counts": {k: len(v) for k, v in guids.items()}, "n_text": len(texts), "texts_sample": texts[:12], "storey_ids": dict(storeys)}
    sp = [(g.get("data-name"), g.get("data-guid")) for g in gs if g.get("class") == "IfcSpace"]
    out[fn]["spaces"] = sp
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "spaces"} for k, v in out.items()}, indent=1, ensure_ascii=False))
pickle.dump(out, open("svg_inventory.pkl", "wb"))

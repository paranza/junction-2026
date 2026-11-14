import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, glob, os, collections, re
import pandas as pd
DS = _DATA + "/data/swiss_dwellings"
WD = _ROOT + "/eda/swiss_dwellings"
rows = []; layer_types = collections.Counter(); ann = collections.Counter(); open_outl = 0
for f in sorted(glob.glob(f"{DS}/*.dxf")):
    doc = ezdxf.readfile(f); msp = doc.modelspace()
    c = collections.Counter(f"{e.dxf.layer}:{e.dxftype()}" for e in msp)
    layer_types.update(c)
    texts = [e for e in msp.query("TEXT")]
    rt = [e.dxf.text for e in texts if e.dxf.layer == "ROOM_TEXT"]
    for e in texts:
        if e.dxf.layer == "ANNOTATION": ann[e.dxf.text] += 1
    outl = list(msp.query("LWPOLYLINE[layer=='ROOM_OUTLINE']"))
    open_outl += sum(1 for e in outl if not e.closed)
    r = dict(file=os.path.basename(f)[:-4], insunits=doc.header.get("$INSUNITS"),
             n_outline=len(outl), n_roomnum=sum(1 for t in rt if re.fullmatch(r"[A-Z]?\d*\.\d+", t)),
             n_area_txt=sum(1 for t in rt if t.endswith("m²")), n_unit_outline=len(list(msp.query("*[layer=='UNIT_OUTLINE']"))),
             n_unit_tag=sum(1 for t in rt if re.match(r"(App\.|Whg\.|Gewerbe|Comm|Unit)", t)))
    r.update(c); rows.append(r)
s = pd.DataFrame(rows).fillna(0)
pd.set_option("display.width", 250, "display.max_rows", 200, "display.max_columns", 50)
print(s.describe().T.to_string())
print("open room outlines:", open_outl)
print("layer:type totals", layer_types.most_common())
print("ANNOTATION texts (top)", ann.most_common(30))
s.to_csv(f"{WD}/dxf_survey.csv", index=False)
print((s.n_outline - s.n_roomnum).describe())

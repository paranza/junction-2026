import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, glob, os, re, collections
import pandas as pd
DS = _DATA + "/data/swiss_dwellings"
WD = _ROOT + "/eda/swiss_dwellings"
rows = []
for f in sorted(glob.glob(f"{DS}/*.pdf")):
    p = pymupdf.open(f)[0]
    spans = [sp for b in p.get_text("dict")["blocks"] for l in b.get("lines", []) for sp in l["spans"]]
    txt = [s["text"] for s in spans]
    n_area = sum(1 for t in txt if re.fullmatch(r"\d+\.\d\d m²", t))
    n_num = sum(1 for s in spans if "Bold" in s["font"] and re.fullmatch(r"[A-Z]?\d*\.\d+", s["text"]))
    unit_tags = [t for t in txt if re.match(r"^(App\.|Whg\.|Appart\.|Gewerbe|Commerce|Commercio|Unità|Unité|Logement|Wohnung)", t)]
    bold_tags = [s["text"] for s in spans if "Bold" in s["font"] and not re.fullmatch(r"[A-Z]?\d*\.\d+", s["text"]) and s["bbox"][1] < p.rect.height*0.82]
    scale = next((t for t in txt if re.fullmatch(r"1:\d+ \(A\d\)", t)), None)
    note = next((t for t in txt if "²" in t and "m²" in t and not re.fullmatch(r"\d+\.\d\d m²", t)), None)
    rows.append(dict(file=os.path.basename(f)[:-4], n_area=n_area, n_roomnum=n_num, scale=scale, area_note=note, bold_tags="|".join(bold_tags), w=round(p.rect.width), h=round(p.rect.height)))
s = pd.DataFrame(rows)
pd.set_option("display.width", 250, "display.max_colwidth", 120, "display.max_rows", 200)
print(s.to_string())
print("files with printed areas:", (s.n_area>0).sum(), "of", len(s))
print(s.groupby([s.n_area>0, "scale"]).size())
s.to_csv(f"{WD}/pdf_text_stats.csv", index=False)

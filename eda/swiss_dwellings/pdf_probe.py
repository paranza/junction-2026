import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, glob, os, collections, sys
DS = _DATA + "/data/swiss_dwellings"
files = sorted(glob.glob(f"{DS}/*.pdf"))
print("n pdf", len(files))
stats = []
for f in files:
    d = pymupdf.open(f)
    p = d[0]
    words = p.get_text("words")
    dr = p.get_drawings()
    imgs = p.get_images()
    fonts = p.get_fonts()
    stats.append((os.path.basename(f), d.page_count, round(p.rect.width,1), round(p.rect.height,1), len(words), len(dr), len(imgs), len(fonts), d.metadata.get("producer"), d.metadata.get("creator")))
import pandas as pd
s = pd.DataFrame(stats, columns=["file","pages","w","h","words","drawings","images","fonts","producer","creator"])
print(s.describe(include="all").to_string())
print(s.groupby(["w","h"]).size())
print(s.producer.value_counts(), s.creator.value_counts())
# Look at one in detail
f = f"{DS}/site1102_bldg2242_floor10281.pdf"
d = pymupdf.open(f); p = d[0]
print(p.rect, d.metadata)
for b in p.get_text("dict")["blocks"][:80]:
    for l in b.get("lines", []):
        for sp in l["spans"]:
            print(round(sp["bbox"][0],1), round(sp["bbox"][1],1), sp["font"], round(sp["size"],2), repr(sp["text"]))

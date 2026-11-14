import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, glob, os, re, collections, json
D = _DATA + "/data/swiss_dwellings"
pdfs = sorted(glob.glob(D + "/*.pdf"))
print("n pdf", len(pdfs))
stats = []
for p in pdfs:
    doc = pymupdf.open(p)
    pg = doc[0]
    words = pg.get_text("words")
    dr = pg.get_drawings()
    txt = pg.get_text()
    scales = re.findall(r"1:\s?\d+[^\n]*", txt)
    fonts = collections.Counter(f[3] for f in pg.get_fonts())
    m2 = len(re.findall(r"m²|m2", txt))
    stats.append(dict(f=os.path.basename(p), pages=len(doc), w=round(pg.rect.width,1), h=round(pg.rect.height,1),
        producer=doc.metadata.get("producer"), creator=doc.metadata.get("creator"), imgs=len(pg.get_images()),
        words=len(words), drawings=len(dr), scales=scales, fonts=sorted(fonts), m2=m2, rot=pg.rotation))
print(collections.Counter(s["pages"] for s in stats))
print(collections.Counter((s["w"], s["h"]) for s in stats))
print(collections.Counter((s["producer"], s["creator"]) for s in stats))
print("imgs", collections.Counter(s["imgs"] for s in stats), "rotation", collections.Counter(s["rot"] for s in stats))
print("words min/max", min(s["words"] for s in stats), max(s["words"] for s in stats))
print("drawings min/max", min(s["drawings"] for s in stats), max(s["drawings"] for s in stats))
print("scale strings", collections.Counter(tuple(s["scales"]) for s in stats))
print("fonts", collections.Counter(tuple(s["fonts"]) for s in stats))
print("files with any m² text", sum(1 for s in stats if s["m2"] > 0), "total m2 tokens", sum(s["m2"] for s in stats))
json.dump(stats, open("pdfprobe.json", "w"), indent=1)

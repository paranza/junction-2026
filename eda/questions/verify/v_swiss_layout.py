import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, os, collections, json
DS = _DATA + "/data/swiss_dwellings"
c = collections.Counter(); leg = []
for fn in sorted(os.listdir(DS)):
    if not fn.endswith(".pdf"): continue
    pg = pymupdf.open(os.path.join(DS, fn))[0]; W, H = pg.rect.width, pg.rect.height
    c[(round(W), round(H))] += 1
    ys = [s["bbox"][1] for b in pg.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"] if s["text"].strip() in ("Legende", "Légende", "Legenda")]
    leg.append((fn, round(min(ys) / H, 3) if ys else None))
print(c)
print(sorted(collections.Counter(x[1] for x in leg).items(), key=lambda kv: (kv[0] is None, kv[0])))

import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, sys, collections
D = _DATA + "/data/swiss_dwellings"
R = lambda c: tuple(round(v, 3) for v in c) if c else None
for stem in sys.argv[1:]:
    pg = pymupdf.open(f"{D}/{stem}.pdf")[0]
    dr = pg.get_drawings()
    c = collections.Counter()
    for d in dr:
        kinds = collections.Counter(it[0] for it in d["items"])
        c[(d["type"], R(d.get("color")), R(d.get("fill")), round(d.get("width") or 0, 3), d.get("dashes") not in (None, "[] 0", "[] 0.0"), tuple(sorted(kinds)), d.get("closePath"))] += 1
    print("==", stem, len(dr))
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]): print(v, k)
    spans = [sp for b in pg.get_text("dict")["blocks"] for l in b.get("lines", []) for sp in l["spans"]]
    print(collections.Counter((sp["font"], round(sp["size"], 2)) for sp in spans).most_common(20))

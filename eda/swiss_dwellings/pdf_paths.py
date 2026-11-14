import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, sys, collections
DS = _DATA + "/data/swiss_dwellings"
p = pymupdf.open(f"{DS}/{sys.argv[1]}.pdf")[0]
dr = p.get_drawings()
def sig(d):
    kinds = "".join(it[0] for it in d["items"])
    col = tuple(round(c, 3) for c in d["color"]) if d.get("color") else None
    fill = tuple(round(c, 3) for c in d["fill"]) if d.get("fill") else None
    return (d["type"], col, fill, round(d["width"], 3) if d.get("width") else None, d.get("dashes"), kinds[:12] + ("..." if len(kinds) > 12 else ""), len(d["items"]))
c = collections.Counter((s[0], s[1], s[2], s[3], s[4]) for s in map(sig, dr))
for k, v in c.most_common(): print(v, k)
print("total", len(dr))

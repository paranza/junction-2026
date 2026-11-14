import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, sys
D = _DATA + "/data/swiss_dwellings"
stem, longside = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2000
clip = [float(v) for v in sys.argv[3].split(",")] if len(sys.argv) > 3 else None
pg = pymupdf.open(f"{D}/{stem}.pdf")[0]
r = pymupdf.Rect(*clip) if clip else pg.rect
z = longside / max(r.width, r.height)
pix = pg.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=r)
out = f"img/{stem}{'_crop' if clip else ''}.png"
pix.save(out); print(out, pix.width, pix.height)

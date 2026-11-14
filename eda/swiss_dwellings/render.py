import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, sys, os
DS = _DATA + "/data/swiss_dwellings"
WD = _ROOT + "/eda/swiss_dwellings/img"
os.makedirs(WD, exist_ok=True)
for name in sys.argv[1:]:
    d = pymupdf.open(f"{DS}/{name}.pdf"); p = d[0]
    z = 2000 / max(p.rect.width, p.rect.height)
    pix = p.get_pixmap(matrix=pymupdf.Matrix(z, z))
    pix.save(f"{WD}/{name}_pdf.png"); print(name, pix.width, pix.height)

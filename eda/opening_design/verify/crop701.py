import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf
D=_DATA + "/data/opening_design/Sports_Complex/Sheets - Current Set/A-701 - Restrooms.pdf"
pg=pymupdf.open(D)[0]
for tag,r in (("6A",(150,1420,900,2015)),("6B",(150,785,900,1430))):
    R=pymupdf.Rect(r)
    pix=pg.get_pixmap(matrix=pymupdf.Matrix(2.6,2.6),clip=R)
    pix.save(f"my_{tag}.png"); print(tag,pix.width,pix.height)

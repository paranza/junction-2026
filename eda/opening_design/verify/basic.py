import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, sys
D=_DATA + "/"
P={"A801":"data/opening_design/Sports_Complex/Sheets - Current Set/A-801 - Door and Finish Schedules & Wall Types.pdf",
"A701":"data/opening_design/Sports_Complex/Sheets - Current Set/A-701 - Restrooms.pdf",
"A700":"data/opening_design/CTR/Most Current Set/Full size sheets/A700 - SCHEDULES.pdf"}
print(pymupdf.__version__ if hasattr(pymupdf,'__version__') else pymupdf.VersionBind)
for k,p in P.items():
    d=pymupdf.open(D+p); pg=d[0]
    print(k, d.page_count, pg.rotation, pg.mediabox, pg.rect, round(pg.rect.width/72,2), round(pg.rect.height/72,2), len(pg.get_text("words")), len(pg.get_drawings()), len(pg.get_images()), d.metadata.get('producer'), d.metadata.get('creator'))
    pix=pg.get_pixmap(dpi=40); pix.save(f"{k}_view.png"); print(pix.width,pix.height)

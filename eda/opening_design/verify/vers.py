import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf
D=_DATA + "/data/opening_design/Sports_Complex/Transfer/_Archive/"
for tag,p in [("permit","20150814 - Issued for Permit/XSC - A-801 - Door and Finish Schedules & Wall Types.pdf"),("transfer","20150720 - Door Schedule to Door Consultant/20150720 - XSC - floor plan and door schedule.pdf")]:
    d=pymupdf.open(D+p)
    for i,pg in enumerate(d):
        print(tag,i,pg.rotation,pg.rect,len(pg.get_text("words")))
        M=pg.rotation_matrix
        for w in pg.get_text("words"):
            if w[4] in ("Schedule","SCHEDULE"):
                print("   ",[round(v) for v in (pymupdf.Rect(w[:4])*M)],w[4])
        pg.get_pixmap(dpi=40).save(f"{tag}_{i}.png")

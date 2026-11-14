import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, time
D=_DATA + "/"
P={"A801":"data/opening_design/Sports_Complex/Sheets - Current Set/A-801 - Door and Finish Schedules & Wall Types.pdf",
"A700":"data/opening_design/CTR/Most Current Set/Full size sheets/A700 - SCHEDULES.pdf"}
for k,p in P.items():
    d=pymupdf.open(D+p); pg=d[0]; pg.set_rotation(0)  # in-memory only, never saved
    t=time.time()
    tabs=pg.find_tables()
    print(k,"find_tables rot0:",len(tabs.tables),"in",round(time.time()-t,1),"s",flush=True)
    for i,tb in enumerate(tabs.tables):
        ex=tb.extract()
        print(" ",i,[round(v) for v in tb.bbox],tb.row_count,tb.col_count, str(ex[:3])[:400],flush=True)

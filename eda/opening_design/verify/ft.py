import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pymupdf, time
D=_DATA + "/"
P={"A801":"data/opening_design/Sports_Complex/Sheets - Current Set/A-801 - Door and Finish Schedules & Wall Types.pdf",
"A700":"data/opening_design/CTR/Most Current Set/Full size sheets/A700 - SCHEDULES.pdf"}
for k,p in P.items():
    d=pymupdf.open(D+p); pg=d[0]
    t=time.time()
    try:
        tabs=pg.find_tables()
        print(k,"find_tables:",len(tabs.tables),"in",round(time.time()-t,1),"s")
        for i,tb in enumerate(tabs.tables):
            print(" ",i,tb.bbox,tb.row_count,tb.col_count, str(tb.extract()[:2])[:300])
    except Exception as e:
        print(k,"ERR",repr(e))

import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Independent table rebuild: words and vertical rules mapped to display coords, rows by y-clustering.
import pymupdf, re, collections
D=_DATA + "/"
P={"A801":"data/opening_design/Sports_Complex/Sheets - Current Set/A-801 - Door and Finish Schedules & Wall Types.pdf",
"A701":"data/opening_design/Sports_Complex/Sheets - Current Set/A-701 - Restrooms.pdf",
"A700":"data/opening_design/CTR/Most Current Set/Full size sheets/A700 - SCHEDULES.pdf"}
def load(k):
    d=pymupdf.open(D+P[k]); pg=d[0]; M=pg.rotation_matrix
    W=[]
    for w in pg.get_text("words"):
        r=pymupdf.Rect(w[:4])*M
        W.append((r.x0,r.y0,r.x1,r.y1,w[4]))
    V=[]; H=[]
    for dr in pg.get_drawings():
        for it in dr["items"]:
            if it[0]=="l":
                a=it[1]*M; b=it[2]*M
                if abs(a.x-b.x)<0.5 and abs(a.y-b.y)>3: V.append((round((a.x+b.x)/2,1),min(a.y,b.y),max(a.y,b.y)))
                elif abs(a.y-b.y)<0.5 and abs(a.x-b.x)>3: H.append((round((a.y+b.y)/2,1),min(a.x,b.x),max(a.x,b.x)))
            elif it[0]=="re":
                r=it[1]*M
                for x in (r.x0,r.x1):
                    if r.height>3: V.append((round(x,1),r.y0,r.y1))
                for y in (r.y0,r.y1):
                    if r.width>3: H.append((round(y,1),r.x0,r.x1))
    return pg,W,V,H
def table(W,V,region,ytol=2.0,minlen=20):
    x0,y0,x1,y1=region
    ws=[w for w in W if x0<=(w[0]+w[2])/2<=x1 and y0<=(w[1]+w[3])/2<=y1]
    xs=sorted({v[0] for v in V if x0-2<=v[0]<=x1+2 and min(v[2],y1)-max(v[1],y0)>=minlen})
    cols=[]
    for x in xs:
        if not cols or x-cols[-1]>1.5: cols.append(x)
    ws.sort(key=lambda w:((w[1]+w[3])/2,w[0]))
    rows=[]
    for w in ws:
        yc=(w[1]+w[3])/2
        if rows and abs(rows[-1][0]-yc)<=ytol: rows[-1][1].append(w)
        else: rows.append([yc,[w]])
    out=[]
    for yc,rw in rows:
        cells=collections.defaultdict(list)
        for w in sorted(rw,key=lambda w:w[0]):
            xc=(w[0]+w[2])/2
            ci=sum(1 for c in cols if c<xc)
            cells[ci].append(w[4])
        out.append((round(yc,1),{c:" ".join(v) for c,v in cells.items()}))
    return cols,out

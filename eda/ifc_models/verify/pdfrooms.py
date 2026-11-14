"""Independent PDF-only room area measurement: filled space paths + text labels, scale from the printed scale bar."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import pymupdf, collections, re, pandas as pd, numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
D=_ROOT + "/eda/ifc_models/verify/files/"
SPACE=(0.89,0.929,0.969)
def rings_of(d):
    rings=[];cur=[]
    for it in d["items"]:
        if it[0]=="l":
            a,b=it[1],it[2]
            if cur and (abs(cur[-1][0]-a.x)>1e-6 or abs(cur[-1][1]-a.y)>1e-6):
                rings.append(cur); cur=[]
            if not cur: cur=[(a.x,a.y)]
            cur.append((b.x,b.y))
        elif it[0]=="qu":
            if cur: rings.append(cur); cur=[]
            q=it[1]; rings.append([(q.ul.x,q.ul.y),(q.ur.x,q.ur.y),(q.lr.x,q.lr.y),(q.ll.x,q.ll.y)])
        elif it[0]=="re":
            if cur: rings.append(cur); cur=[]
            r=it[1]; rings.append([(r.x0,r.y0),(r.x1,r.y0),(r.x1,r.y1),(r.x0,r.y1)])
        else: raise ValueError(it[0])
    if cur: rings.append(cur)
    return [r for r in rings if len(r)>=3]
def poly_of(d):
    acc=None
    for r in rings_of(d):
        p=Polygon(r)
        if not p.is_valid: p=p.buffer(0)
        acc=p if acc is None else acc.symmetric_difference(p)   # even-odd
    return acc
def scalebar(page):
    # find text '0' and '5 m' and the bar between them
    w=page.get_text("words")
    z=[x for x in w if x[4]=="0"]; f=[x for x in w if x[4]=="m"]
    return z,f
rows=[]
for fn in ["bsc-esplanades_1807-ep-ar-v18_plan-04-4-korrus.pdf","bsc-molio_molio-with-uris_plan-02-klder.pdf","kit-fzk-haus_ac20-fzk-haus_plan-02-dachgeschoss.pdf"]:
    p=pymupdf.open(D+fn)[0]
    dr=p.get_drawings()
    polys=[poly_of(d) for d in dr if d.get("fill") and tuple(round(c,3) for c in d["fill"])==SPACE]
    # scale bar: black filled rects near the '0' and '5 m' labels
    bars=[d for d in dr if d.get("fill") and tuple(round(c,3) for c in d["fill"]) in ((0.0,0.0,0.0),(1.0,1.0,1.0)) and d["type"]=="fs" and d["rect"].height<10]
    xs=[(d["rect"].x0,d["rect"].x1,d["rect"].height) for d in bars]
    z,f=scalebar(p)
    print(fn,"space polys",len(polys),"scale-bar-like rects",[(round(a,2),round(b,2),round(h,2)) for a,b,h in xs][:8],"'0' x",[round(x[0],2) for x in z],"'m' x",[round(x[0],2) for x in f])
    if xs:
        x0=min(a for a,_,_ in xs); x1=max(b for _,b,_ in xs); L=x1-x0
        print("   bar length pt",round(L,3),"-> metres per pt if 5 m:",5/L, " vs 1:100 nominal",0.0254/72*100)
    # labels: spans at label font size 5.67, consecutive pairs LongName / Name
    spans=[(s["text"],pymupdf.Rect(s["bbox"])) for b in p.get_text("dict")["blocks"] if b["type"]==0 for l in b["lines"] for s in l["spans"] if abs(s["size"]-5.67)<0.01 and not s["text"].startswith("©") and not s["text"].startswith("http")]
    # pair: name line directly below long-name line with same centre x
    used=set(); labels=[]
    for i,(t,r) in enumerate(spans):
        if i in used: continue
        best=None
        for j,(t2,r2) in enumerate(spans):
            if j==i or j in used: continue
            if abs((r.x0+r.x1)/2-(r2.x0+r2.x1)/2)<1.0 and 0<r2.y0-r.y0<12:
                if best is None or r2.y0<spans[best][1].y0: best=j
        if best is not None:
            used|={i,best}; r2=spans[best][1]
            labels.append((f"{t} ({spans[best][0]})",((r.x0+r.x1)/2,(r.y0+r2.y1)/2)))
    m=0.0254/72*100
    for lab,(cx,cy) in labels:
        cont=[q for q in polys if q.contains(Point(cx,cy))]
        a=min(q.area for q in cont)*m*m if cont else None
        rows.append({"file":fn,"room":lab,"pdf_area":a,"n_cont":len(cont)})
    rows.append({"file":fn,"room":"__TOTAL__","pdf_area":sum(q.area for q in polys)*m*m,"n_cont":len(polys)})
    rows.append({"file":fn,"room":"__NSPACES__","pdf_area":len(polys),"n_cont":len(labels)})
R=pd.DataFrame(rows); R.to_csv("pdf_rooms_verify.csv",index=False)
print(R.groupby("file").size())
Q=pd.read_pickle("qp.pkl")
Q=Q[Q.path.str.endswith(".pdf")]
Q["file"]=Q.path.str.split("/").str[-1]
res=[]
for _,r in Q.iterrows():
    pred=None
    if r.fam=="room_area":
        x=R[(R.file==r.file)&(R.room==r.room)]; pred=x.pdf_area.iloc[0] if len(x)==1 else None
    elif r.fam=="storey_space_area":
        pred=R[(R.file==r.file)&(R.room=="__TOTAL__")].pdf_area.iloc[0]
    elif r.fam=="storey_count" and r.elem=="space":
        pred=R[(R.file==r.file)&(R.room=="__NSPACES__")].pdf_area.iloc[0]
    if pred is None: res.append((r.fam,None,None,None)); continue
    ok=(int(pred)==r.answer) if r.type=="count" else abs(pred-r.answer)<=0.02*r.answer
    ex=(round(pred,2)==round(r.answer,2)) if r.type!="count" else ok
    res.append((r.fam,ok,ex,(pred-r.answer)/r.answer if r.type!="count" else 0))
X=pd.DataFrame(res,columns=["fam","ok","exact","rel"])
print(X.groupby("fam").agg(n=("fam","size"),attempted=("ok",lambda s:s.notna().sum()),ok=("ok",lambda s:int(s.fillna(False).astype(bool).sum())),exact=("exact",lambda s:int(s.fillna(False).astype(bool).sum())),maxrel=("rel",lambda s:np.nanmax(np.abs(s.astype(float))) if s.notna().any() else np.nan)))

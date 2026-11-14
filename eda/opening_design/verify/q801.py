import sys, json, re
sys.path.insert(0,".")
from mytab import *
import pymupdf
QS=[json.loads(l) for l in open(D+"questions.jsonl")]
Q801=[q for q in QS if "A-801" in q["path"]]
def norm(s): return re.sub(r"\s+","",str(s)).replace("’","'").replace("”",'"').lower()
def tables(path, page=0, door_reg=(130,105,930,770), fin_reg=(130,775,1325,1420), key_reg=(130,1430,830,1715), kn_reg=(945,105,1555,430)):
    d=pymupdf.open(D+path); pg=d[page]; M=pg.rotation_matrix
    global W,V
    W=[];V=[]
    for w in pg.get_text("words"):
        r=pymupdf.Rect(w[:4])*M; W.append((r.x0,r.y0,r.x1,r.y1,w[4]))
    for dr in pg.get_drawings():
        for it in dr["items"]:
            if it[0]=="l":
                a=it[1]*M; b=it[2]*M
                if abs(a.x-b.x)<0.5 and abs(a.y-b.y)>3: V.append((round((a.x+b.x)/2,1),min(a.y,b.y),max(a.y,b.y)))
            elif it[0]=="re":
                r=it[1]*M
                if r.height>3: V+= [(round(r.x0,1),r.y0,r.y1),(round(r.x1,1),r.y0,r.y1)]
    _,dr_=table(W,V,door_reg); _,fr=table(W,V,fin_reg); _,kr=table(W,V,key_reg); _,knr=table(W,V,kn_reg)
    doors=[c for y,c in dr_ if re.fullmatch(r"\d{3}\.[A-Z]\d?",c.get(1,""))]
    rooms=[]
    for y,c in fr:
        if re.fullmatch(r"\d{3}",c.get(2,"")): rooms.append(dict(c))
        elif rooms and set(c)=={1}: rooms[-1][1]=rooms[-1].get(1,"")+" "+c[1]  # wrapped 'Redundant Room'
    key={c[1]:c[2] for y,c in kr if 1 in c and 2 in c and re.fullmatch(r"[A-Z]\d",c[1])}
    return doors,rooms,key
def area(r):
    m=re.fullmatch(r"(\d+) SF",r.get(1,"")); return int(m.group(1)) if m else None
def answers(doors,rooms,key):
    A={}
    g=lambda d,i:d.get(i,"").strip()
    A[0]=len(doors)
    for i,t in zip(range(1,7),["A1","A2","B1","B2","B3","C1"]): A[i]=sum(g(d,6)==t for d in doors)
    A[7]=sum(g(d,7)=="WD-1" for d in doors)
    A[8]=sum(g(d,8)=="STL-1" for d in doors)
    A[9]=sum(g(d,8) in("AL-1","AL-2") for d in doors)
    for i,n in zip((10,11,12),"ABC"): A[i]=sum(n in [x.strip() for x in g(d,11).split(",")] for d in doors)
    A[13]=sum(norm(g(d,4))==norm("3'-0\"") for d in doors)
    A[14]=sum(norm(g(d,5))==norm("7'-0\"") for d in doors)
    A[15]=sum(g(d,3)=="118" for d in doors); A[16]=sum(g(d,3)=="128" for d in doors)
    A["16prefix"]=sum(g(d,1).startswith("128.") for d in doors)
    by={g(d,1):d for d in doors}
    A[17]=g(by.get("121.A",{}),4)
    t=g(by.get("121.A",{}),6); A[18]=t
    b=by.get("128.B",{}); A[19]=f'{g(b,4)} wide x {g(b,5)} high'
    A[20]=g(by.get("107.A",{}),10); A[21]=g(by.get("115.A",{}),7)
    A[22]=sorted({g(by[k],5) for k in ("118.A1","118.A2","118.B1","118.B2") if k in by})
    A[23]=len(rooms)
    R={r[2]:r for r in rooms}
    for i,n in zip((24,25,26,27),("128","118","122","121")): A[i]=area(R[n]) if n in R else None
    A[28]=sum(area(r) for r in rooms if area(r))
    A[29]=sum(area(r) or 0 for r in rooms if r.get(3)=="OFFICE")
    A[30]=sum(area(r) or 0 for r in rooms if r.get(3)=="RESTROOM")
    A[31]=sum(area(r) or 0 for r in rooms if "LOCKER" in r.get(3,""))
    f0=[r for r in rooms if r.get(4)=="F0"]; A[32]=f"{len(f0)} rooms, {sum(area(r) or 0 for r in f0)} SF"
    A[33]=sum(area(r) or 0 for r in rooms if r.get(4)=="F4")
    A[34]=sum(r.get(5)=="B2" for r in rooms)
    A[35]=sum(all(r.get(i)=="W1" for i in (6,7,8,9)) for r in rooms)
    A[36]=(R.get("113",{}).get(4), key.get(R.get("113",{}).get(4)))
    f=R.get("128",{}).get(4,""); A[37]=(f,[key.get(c.strip()) for c in f.split("&")])
    c=R.get("128",{}).get(10); A[38]=(c,key.get(c))
    w=R.get("118",{}).get(6); A[39]=(w,key.get(w))
    mx=max(rooms,key=lambda r:area(r) or 0); A[40]=f"Room {mx[2]} {mx.get(3)} ({area(mx)} SF)"
    return A
def score(q,a):
    gt=q["answer"]
    if q["type"]=="count": return a==gt
    if q["type"]=="area": return a is not None and abs(a-gt)<=0.02*abs(gt)
    # text: every number/code token in GT must appear in computed answer
    toks=re.findall(r"[A-Z]+-?\d+|\d+(?:'|\")?(?:-\d+)?(?: \d+/\d+)?\"?",str(gt).upper().replace(" ",""))
    s=norm(json.dumps(a)).upper()
    return all(norm(t).upper() in s for t in toks) and len(toks)>0
if __name__=="__main__":
    cur="data/opening_design/Sports_Complex/Sheets - Current Set/A-801 - Door and Finish Schedules & Wall Types.pdf"
    per="data/opening_design/Sports_Complex/Transfer/_Archive/20150814 - Issued for Permit/XSC - A-801 - Door and Finish Schedules & Wall Types.pdf"
    res={}
    for tag,p in (("current",cur),("permit",per)):
        doors,rooms,key=tables(p)
        A=answers(doors,rooms,key); res[tag]=A
        print(tag,"doors",len(doors),"rooms",len(rooms),"key",len(key),"room128prefix",A["16prefix"])
    ok={"current":0,"permit":0}
    for i,q in enumerate(Q801):
        line=[str(i),q["type"],str(q["answer"])]
        for tag in ("current","permit"):
            s=score(q,res[tag][i]); ok[tag]+=s; line+= [tag[:3],str(res[tag][i]),"OK" if s else "XX"]
        print(" | ".join(line))
    print(ok, "of", len(Q801))

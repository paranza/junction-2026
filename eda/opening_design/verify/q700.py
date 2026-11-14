import sys, json, re
sys.path.insert(0,".")
from mytab import *
QS=[json.loads(l) for l in open(D+"questions.jsonl")]
Q=[q for q in QS if "A700" in q["path"]]
pg,W,V,H=load("A700")
_,tr=table(W,V,(125,860,1225,1290)); _,wr=table(W,V,(2145,80,2535,232))
T=[c for y,c in tr if re.fullmatch(r"\d+",c.get(1,"")) and c.get(2)]
Wn=[c for y,c in wr if re.fullmatch(r"[A-Z]{2}",c.get(1,""))]
n=lambda c:int(c[1]); ty=lambda c:c.get(3,"")
by={c[2]:c for c in T}; wb={c[1]:c for c in Wn}
def calc(sumf):
    A={}
    A[44]=sumf([by["U01"]]); A[45]=sumf([by["U02"]])
    A[46]=sumf([c for c in T if "MARVIN ESSENTIAL SLIDING" in ty(c)])
    A[47]=sumf([c for c in T if "MARVIN ESSENTIAL SLIDING" in ty(c) and "3RD FLOOR" in ty(c)])
    A[48]=sumf([c for c in T if "VISTAGRANDE" in ty(c) and "1ST FLOOR" in ty(c)])
    A[49]=sumf([by["U41"]]); A[50]=sumf(T)
    A[51]=sumf([c for c in T if ty(c).startswith("SWING")])
    A[52]=sumf([by["U06"],by["U44"]])
    A[53]=by["U01"].get(6); A[54]=by["U01"].get(10)
    A[55]=sumf([by["U22"]]); A[56]=sumf(Wn)
    for i,k in zip((57,58,59,60),("SS","RR","QQ","VV")): A[i]=sumf([wb[k]])
    A[61]=sumf([wb[k] for k in ("SS","TT","UU")])
    A[62]=sum(int(re.match(r"(\d)-WIDE",c[2]).group(1))*int(c[3]) for c in Wn) if sumf is S else len(Wn)
    A[63]=f'{wb["SS"][4]} wide x {wb["SS"][5]} high'
    return A
S=lambda rows:sum(int(r[1]) if re.fullmatch(r"\d+",r.get(1,"")) and r.get(1) and len(r.get(1))<5 and r is not None and r in T else int(r[3]) for r in rows)
R=lambda rows:len(rows)
print("type rows",len(T),"window rows",len(Wn),"sum Count",sum(n(c) for c in T))
for tag,f in (("sum",S),("rows",R)):
    A=calc(f); k=0; m=0
    for i,q in enumerate(Q):
        idx=44+i; a=A[idx]
        if q["type"]=="count":
            ok=a==q["answer"]; m+=1
        else:
            ok=re.sub(r"\s","",str(a))==re.sub(r"\s","",str(q["answer"]))
        k+=ok
        if tag=="sum" or q["type"]=="count": print(tag,idx,q["type"],"GT=",q["answer"],"calc=",a,"OK" if ok else "XX")
    print(tag,"total",k,"/",len(Q))
# double-leaf check for Q51
sw=[c for c in T if ty(c).startswith("SWING")]
print("SWING rows",[(c[2],c[1],ty(c)) for c in sw])
print("leaves if DOUBLE=2:",sum(int(c[1])*(2 if "DOUBLE" in ty(c) else 1) for c in sw))

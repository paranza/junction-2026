import sys, re; sys.path.insert(0,".")
from mytab import *
d=pymupdf.open(D+P["A801"]); pg=d[0]
t=pg.get_text()
i=t.find("122.B"); print("DEFAULT get_text around 122.B:",repr(t[i:i+120]))
ts=pg.get_text(sort=True)
lines=[l for l in ts.splitlines() if l.count(".A")>=5 or l.count("100.A")]
print("sort=True: lines containing >=5 door numbers:",len([l for l in ts.splitlines() if len(re.findall(r"\b\d{3}\.[A-Z]\d?\b",l))>=5]))
l=max(ts.splitlines(),key=lambda l:len(re.findall(r"\b\d{3}\.[A-Z]\d?\b",l))); print("max door numbers on one sort=True line:",len(re.findall(r"\b\d{3}\.[A-Z]\d?\b",l)), repr(l[:150]))
# legend label under DOOR TYPE B3
pgW,W2,_,_=load("A801")
for w in W2:
    if w[4] in ("ALUMINIUM","ALUMINUM"): print("label word",w[4],[round(v) for v in w[:4]])
print("ALUMINIUM SLIDING DOOR" in t.upper(), "ALUMINIUM SLIDING" in t.upper())
# images on question sheets
for k in ("A801","A701","A700"):
    pg2=pymupdf.open(D+P[k])[0]; M=pg2.rotation_matrix
    infos=pg2.get_image_info()
    print(k,"images",len(infos),[ [round(v) for v in (pymupdf.Rect(i["bbox"])*M)] for i in infos][:11])
# transfer A-801 version (page 3)
tp="data/opening_design/Sports_Complex/Transfer/_Archive/20150720 - Door Schedule to Door Consultant/20150720 - XSC - floor plan and door schedule.pdf"
pg3=pymupdf.open(D+tp)[2]; M=pg3.rotation_matrix
Wt=[(pymupdf.Rect(w[:4])*M, w[4]) for w in pg3.get_text("words")]
dn=[s for r,s in Wt if re.fullmatch(r"\d{3}\.[A-Z]\d?",s) and r.x0<300]
print("transfer p3 door-number words in left column:",len(dn), "unique",len(set(dn)))
print("transfer date words:",[s for r,s in Wt if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}",s)])

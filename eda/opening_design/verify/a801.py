import sys; sys.path.insert(0,".")
from mytab import *
pg,W,V,H=load("A801")
for name,reg in [("door",(130,105,930,665)),("finish",(130,775,1325,1395)),("key",(130,1430,830,1715)),("keynote",(945,105,1555,430))]:
    cols,rows=table(W,V,reg)
    print("==",name,"cols",len(cols),[round(c) for c in cols])
    for yc,cells in rows: print(yc,"|".join(f"{c}:{t}" for c,t in sorted(cells.items())))

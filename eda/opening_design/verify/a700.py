import sys; sys.path.insert(0,".")
from mytab import *
pg,W,V,H=load("A700")
for name,reg in [("type",(125,860,1225,1290)),("window",(2145,80,2535,232)),("number",(125,85,1440,820))]:
    cols,rows=table(W,V,reg)
    print("==",name,"cols",len(cols),[round(c) for c in cols])
    for yc,cells in rows: print(yc,"|".join(f"{c}:{t}" for c,t in sorted(cells.items())))

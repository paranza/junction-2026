import pandas as pd, numpy as np
Q=pd.read_pickle("solved.pkl")
Q=Q[Q.model_file!="kit-fzk-haus_ac20-fzk-haus.ifc"]
okc=[c for c in Q.columns if c.startswith("ok_c_")]
for (m,fam),g in Q.groupby(["model_file","fam"]):
    print("==",m,fam,len(g))
    for c in okc:
        s=g[c].dropna()
        if len(s): print("   %-40s %d/%d (n_avail %d)"%(c[5:],int(s.astype(bool).sum()),len(g),len(s)))

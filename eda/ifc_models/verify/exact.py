import pandas as pd, numpy as np
Q=pd.read_pickle("solved.pkl")
Q=Q[Q.model_file!="kit-fzk-haus_ac20-fzk-haus.ifc"]
for (m,fam),g in Q[Q.fam.isin(["room_area","storey_space_area"])].groupby(["model_file","fam"]):
    print("==",m,fam,len(g))
    for c in [c for c in g.columns if c.startswith("c_") and g[c].notna().any() and not c.startswith("c_n")]:
        s=g[[c,"answer"]].dropna()
        ex=(s[c].round(2)==s.answer.round(2)).sum()
        err=((s[c]-s.answer)/s.answer)
        print("   %-38s exact2dp %d/%d  max|rel err| %.4f%%  max|abs err| %.4f"%(c[2:],ex,len(s),100*err.abs().max(),(s[c]-s.answer).abs().max()))

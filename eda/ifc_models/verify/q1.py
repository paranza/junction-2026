import pandas as pd
q=pd.read_pickle("q.pkl")
pd.set_option("display.width",250); pd.set_option("display.max_colwidth",200)
for p,g in q.groupby("path"):
    print("=====",p,len(g))
    for t,gg in g.groupby("type"):
        print("--",t,len(gg))
        for _,r in gg.head(6).iterrows():
            print("   ",repr(r.question),"->",r.answer,r.unit)

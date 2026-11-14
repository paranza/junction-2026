import pandas as pd, re
q=pd.read_pickle("q.pkl")
# mask quoted strings to get surface templates
def tmpl(s):
    s=re.sub(r"'[^']*'(?=[ ,?])","<Q>",s)   # straight quotes
    s=re.sub(r"„[^“]*“","<Q>",s)
    s=re.sub(r"«[^»]*»","<Q>",s)
    s=re.sub(r"\"[^\"]*\"","<Q>",s)
    return s
q["tmpl"]=q.question.map(tmpl)
vc=q.groupby(["tmpl","type"]).size().reset_index(name="n").sort_values("n",ascending=False)
print(len(vc),"surface templates")
for _,r in vc.iterrows(): print(r.n, r.type, r.tmpl)
q.to_pickle("q.pkl")

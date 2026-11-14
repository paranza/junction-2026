import pickle, collections, pandas as pd, re
Q=pd.read_pickle("solved.pkl")
for m in ["bsc-esplanades_1807-ep-ar-v18.ifc","bsc-molio_molio-with-uris.ifc"]:
    F=pickle.load(open(f"facts_{m}.pkl","rb"))
    sid2st={i:s["name"] for s in F["storeys"] for i in s["space_ids"]}
    labels=collections.Counter((f'{x["LongName"]} ({x["Name"]})',sid2st.get(x["id"])) for x in F["spaces"])
    asked=collections.Counter((r.room,r.storey) for _,r in Q[(Q.model_file==m)&(Q.fam=="room_area")&(Q.lang=="en")].iterrows())
    print(m,"spaces",len(F["spaces"]),"distinct (label,storey)",len(labels),"asked",len(asked),"spaces not asked",len(set(labels)-set(asked)),"asked not found",len(set(asked)-set(labels)))
    lab_only=collections.Counter(f'{x["LongName"]} ({x["Name"]})' for x in F["spaces"])
    print("  labels duplicated model-wide:",[k for k,v in lab_only.items() if v>1][:5])
    nm=collections.Counter(x["Name"] for x in F["spaces"]); print("  Name duplicated model-wide:",sum(v>1 for v in nm.values()), list(nm.items())[:6])
    print("  LongName None:",sum(x["LongName"] is None for x in F["spaces"]),"Name None:",sum(x["Name"] is None for x in F["spaces"]))
    # Name formats
    pats=collections.Counter(re.sub(r"\d+","9",x["Name"]) for x in F["spaces"]); print("  name patterns",pats.most_common(8))
# quote chars per language
for lang,g in Q.groupby("lang"):
    print(lang, "straight",g.question.str.contains("'").sum(),"typographic",g.question.str.contains("„").sum(),"n",len(g))

import pickle, collections
for m in ["bsc-esplanades_1807-ep-ar-v18.ifc","bsc-molio_molio-with-uris.ifc"]:
    F=pickle.load(open(f"facts_{m}.pkl","rb"))
    print("=====",m)
    for s in F["storeys"]:
        dc=collections.Counter(c for _,c,_ in s["direct"]); sc=collections.Counter(c for _,c,_ in s["in_spaces"])
        print(s["name"],s["elev"],"spaces",len(s["space_ids"]),"direct",dict(dc),"in_spaces",dict(sc))
    sp=F["spaces"]
    print("space parents",collections.Counter(str(x["parent"]) for x in sp).most_common(12))
    keys=collections.Counter(k for x in sp for k in x["q"] if any(w in k[1].lower() for w in ("area","areal","pindala","flade")))
    print("area-like keys on spaces",keys.most_common(30))

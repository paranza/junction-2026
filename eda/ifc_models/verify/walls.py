import pickle, collections, pandas as pd
F=pickle.load(open("facts_bsc-molio_molio-with-uris.ifc.pkl","rb"))
W=[e for e in F["walls_slabs"]]
keys=collections.Counter((e["cls"],k[0],k[1]) for e in W for k,v in e["q"].items() if v[0]!="prop")
for k,v in sorted(keys.items()): print(v,k)
print(collections.Counter((e["cls"],tuple(c[1] for c in e["cont"]),bool(e["dec"])) for e in W))
# per storey: walls missing BaseQuantities
for s in F["storeys"]:
    ids={i for i,c,_ in s["direct"] if c in ("IfcWall","IfcSlab")}
    ws=[e for e in W if e["id"] in ids]
    miss=collections.Counter(e["cls"] for e in ws if not any(k[0]=="BaseQuantities" for k in e["q"]))
    print(s["name"], collections.Counter(e["cls"] for e in ws), "missing BQ:",dict(miss), "no own body:",collections.Counter(e["cls"] for e in ws if not e["has_body"]), "with parts:",collections.Counter(e["cls"] for e in ws if e["n_parts"]))

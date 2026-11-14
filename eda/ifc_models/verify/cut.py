import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pickle, collections, pandas as pd, numpy as np, ifcopenshell, ifcopenshell.util.placement as up
DS=_DATA + "/data/ifc_models/"
Q=pd.read_pickle("qp.pkl")
Q["model_file"]=Q.path.map(lambda p:(p.split("/")[-1].split("_plan-")[0] if "_plan-" in p else p.split("/")[-1].rsplit(".",1)[0])+".ifc")
CLS={"door":("IfcDoor",),"window":("IfcWindow",),"wall":("IfcWall","IfcWallStandardCase"),"column":("IfcColumn",),"stair":("IfcStair",),"space":("IfcSpace",)}
rows=[]
for m in ["bsc-esplanades_1807-ep-ar-v18.ifc","bsc-molio_molio-with-uris.ifc"]:
    F=pickle.load(open(f"facts_{m}.pkl","rb")); Z=pickle.load(open(f"zr_{m}.pkl","rb"))
    f=ifcopenshell.open(DS+m)
    P={p["id"]:p for p in F["products"]}
    kids=collections.defaultdict(list)
    for p in F["products"]:
        for d in p["dec"]: kids[d[2]].append(p["id"])
    def zr(pid):
        out=[Z[P[pid]["guid"]][:2]] if P[pid]["guid"] in Z else []
        for k in kids.get(pid,[]): out+=zr(k)
        return out
    asked=set((r.storey,r.elem) for _,r in Q[(Q.model_file==m)&(Q.fam=="storey_count")].iterrows())
    for s in F["storeys"]:
        se=f.by_id(s["id"]); zpl=up.get_local_placement(se.ObjectPlacement)[2,3]/1000
        for el,cls in CLS.items():
            ids=s["space_ids"] if el=="space" else [i for i,c,_ in s["direct"] if c in cls]
            n=len(ids)
            for base,label in ((s["elev"]/1000,"elev"),(zpl,"placement")):
                cut=base+1.2
                ncut=0
                for i in ids:
                    rr=zr(i)
                    if rr and min(a for a,_ in rr)<=cut<=max(b for _,b in rr): ncut+=1
                rows.append({"model":m[:14],"storey":s["name"],"elem":el,"n_ifc":n,"basis":label,"z0":round(base,3),"n_cut":ncut,"asked":(s["name"],el) in asked})
R=pd.DataFrame(rows)
for basis,g in R.groupby("basis"):
    g=g.assign(equal=(g.n_cut==g.n_ifc)&(g.n_ifc>0))
    print("== basis",basis)
    print(pd.crosstab(g.asked,g.equal,margins=True))
    print(g[g.asked!=g.equal][["model","storey","elem","n_ifc","n_cut","asked","z0"]].to_string())
R.to_csv("cut_verify.csv",index=False)

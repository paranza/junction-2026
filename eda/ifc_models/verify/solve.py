"""Independent solver: computes several candidate conventions per question and scores them."""
import pickle, collections, math, pandas as pd, numpy as np
q=pd.read_pickle("qp.pkl")
def model_of(path):
    b=path.split("/")[-1]
    b=b.split("_plan-")[0] if "_plan-" in b else b.rsplit(".",1)[0]
    return b+".ifc"
q["model_file"]=q.path.map(model_of)
FACTS={}
for m in q.model_file.unique():
    try: FACTS[m]=pickle.load(open(f"facts_{m}.pkl","rb"))
    except FileNotFoundError: FACTS[m]=None
print({k:(v is not None) for k,v in FACTS.items()})

CLS={"door":["IfcDoor"],"window":["IfcWindow"],"wall":["IfcWall","IfcWallStandardCase"],"column":["IfcColumn"],
     "stair":["IfcStair"],"beam":["IfcBeam"],"space":["IfcSpace"]}
def ok(pred,ans,typ):
    if pred is None or (isinstance(pred,float) and math.isnan(pred)): return False
    if typ=="count": return int(round(pred))==int(ans)
    return abs(pred-ans)<=0.02*abs(ans)
def qv(d,keys,scale):
    for k in keys:
        if k in d["q"] and d["q"][k][1] is not None: return d["q"][k][1]*scale
    return None

def space_area_candidates(F,sp):
    L,A,V=F["scales"]
    c={}
    c["qto_net"]=qv(sp,[("BaseQuantities","NetFloorArea"),("Qto_SpaceBaseQuantities","NetFloorArea")],A)
    c["qto_gross"]=qv(sp,[("BaseQuantities","GrossFloorArea"),("Qto_SpaceBaseQuantities","GrossFloorArea")],A)
    for k in ["down_at_min","down_all","horiz_at_min_abs","up_at_max","proj"]:
        c["geom_"+k]=sp.get("g_"+k)
    c["fp_curve"]=sp.get("fp_curve") if isinstance(sp.get("fp_curve"),float) else None
    v=sp["q"].get(("AR_Ruum","120_Pindala"))
    try: c["pset_pindala"]=float(str(v[1]).replace(",",".")) if v else None
    except: c["pset_pindala"]=None
    for k in ["Measured Area","Measured Net Area","Calculated Area","Reduced Area"]:
        v=sp["q"].get(("AC_Pset_Zone_Stamp_02_25",k)); c["ac_"+k]=v[1] if v else None
    # convention under test: Qto net if present else floor-face geometry
    c["CONV"]=c["qto_net"] if c["qto_net"] is not None else c["geom_down_at_min"]
    return c

rows=[]
for i,r in q.iterrows():
    F=FACTS[r.model_file]; out={"i":i}
    if F is None: rows.append(out); continue
    L,A,V=F["scales"]
    st={s["name"]:s for s in F["storeys"]}
    spaces={x["id"]:x for x in F["spaces"]}
    if r.fam in ("room_area","storey_space_area"):
        s=st[r.storey]
        sps=[spaces[k] for k in s["space_ids"]]
        if r.fam=="room_area":
            hits=[x for x in sps if f'{x["LongName"]} ({x["Name"]})'==r.room]
            hits_model=[x for x in F["spaces"] if f'{x["LongName"]} ({x["Name"]})'==r.room]
            out["n_match_storey"]=len(hits); out["n_match_model"]=len(hits_model)
            if len(hits)==1:
                c=space_area_candidates(F,hits[0]); out.update({"c_"+k:v for k,v in c.items()}); out["guid"]=hits[0]["guid"]
        else:
            cs=[space_area_candidates(F,x) for x in sps]
            for k in cs[0]:
                vals=[c[k] for c in cs]
                if all(v is not None for v in vals):
                    out["c_"+k]=sum(vals); out["c_"+k+"_sumrounded"]=sum(round(v,2) for v in vals)
    elif r.fam=="storey_count":
        s=st[r.storey]; cls=CLS[r.elem]
        if r.elem=="space": out["c_CONV"]=len(s["space_ids"])
        else:
            out["c_CONV"]=sum(1 for _,c,_ in s["direct"] if c in cls)
            out["c_direct_plus_inspace"]=out["c_CONV"]+sum(1 for _,c,_ in s["in_spaces"] if c in cls)
            if r.elem=="stair": out["c_stairflight_direct"]=sum(1 for _,c,_ in s["direct"] if c=="IfcStairFlight")
    elif r.fam=="model_count":
        P=F["products"]
        if r.elem=="sanitary":
            out["c_CONV"]=sum(1 for p in P if p["cls"]=="IfcFlowTerminal" and p["type"]=="IfcSanitaryTerminalType")
            out["c_all_flowterminal"]=sum(1 for p in P if p["cls"]=="IfcFlowTerminal")
        elif r.elem=="space":
            out["c_CONV"]=sum(1 for p in P if p["cls"]=="IfcSpace")
        else:
            cls=CLS[r.elem]
            out["c_bytype"]=sum(1 for p in P if p["cls"] in cls)
            out["c_CONV"]=sum(1 for p in P if p["cls"] in cls and p["cont"])  # directly contained in spatial structure
            out["c_not_decomposed"]=sum(1 for p in P if p["cls"] in cls and not p["dec"])
    else:  # wall/slab quantities per storey
        s=st[r.storey]
        cls={"wall_length":["IfcWall","IfcWallStandardCase"],"wall_side_area":["IfcWall","IfcWallStandardCase"],
             "wall_volume":["IfcWall","IfcWallStandardCase"],"slab_volume":["IfcSlab"]}[r.fam]
        ids={e for e,c,_ in s["direct"] if c in cls}
        els=[e for e in F["walls_slabs"] if e["id"] in ids]
        out["n_el"]=len(els)
        qn={"wall_length":[("Length",L),("Width",L)],"wall_side_area":[("NetSideArea",A),("GrossSideArea",A)],
            "wall_volume":[("NetVolume",V),("GrossVolume",V)],"slab_volume":[("NetVolume",V),("GrossVolume",V)]}[r.fam]
        for name,sc in qn:
            vals=[qv(e,[("BaseQuantities",name)],sc) for e in els]
            out["n_missing_"+name]=sum(v is None for v in vals)
            out["c_bq_"+name]=sum(v for v in vals if v is not None)
        out["c_CONV"]=out["c_bq_"+qn[0][0]]
    rows.append(out)
R=pd.DataFrame(rows).set_index("i")
Q=q.join(R)
cand=[c for c in R.columns if c.startswith("c_")]
for c in cand:
    Q["ok_"+c]=[ok(p,a,t) if pd.notna(p) else np.nan for p,a,t in zip(Q[c],Q.answer,Q.type)]
Q.to_pickle("solved.pkl")
avail=Q[Q.model_file.map(lambda m:FACTS[m] is not None)]
print("questions with IFC available:",len(avail),"of",len(Q))
print("CONV overall: %d/%d"%(avail.ok_c_CONV.fillna(False).astype(bool).sum(),len(avail)))
# exactness after rounding
def exact(p,a,t,fam):
    if pd.isna(p): return False
    if t=="count": return int(round(p))==a
    nd=2 if fam in ("room_area","storey_space_area") else 3
    return round(p,nd)==round(a,nd)
avail=avail.assign(exact=[exact(p,a,t,f) for p,a,t,f in zip(avail.c_CONV,avail.answer,avail.type,avail.fam)])
print(avail.groupby("fam").agg(n=("answer","size"),ok=("ok_c_CONV",lambda s:int(s.fillna(False).astype(bool).sum())),exact=("exact","sum")))
print(avail.groupby(["model_file","fam"]).agg(n=("answer","size"),ok=("ok_c_CONV",lambda s:int(s.fillna(False).astype(bool).sum())),exact=("exact","sum")))

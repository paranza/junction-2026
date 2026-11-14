import pickle, collections, pandas as pd, numpy as np
Q=pd.read_pickle("solved.pkl")
F=pickle.load(open("facts_bsc-esplanades_1807-ep-ar-v18.ifc.pkl","rb"))
v=[x["q"].get(("AR_Ruum","120_Pindala")) for x in F["spaces"]]
print("pindala value types",collections.Counter(type(a[1]).__name__ for a in v))
vals=[a[1] for a in v]
print("examples",vals[:8])
def num(s):
    try: return float(str(s).replace(",","."))
    except: return None
nums=[num(a) for a in vals]
print("unparseable",[a for a,n in zip(vals,nums) if n is None][:5],"zeros",sum(1 for n in nums if n==0.0))
dec=collections.Counter(len(str(a).split(".")[1]) if "." in str(a) else 0 for a in vals); print("decimals",dec)
E=Q[(Q.model_file=="bsc-esplanades_1807-ep-ar-v18.ifc")&(Q.fam=="room_area")&(Q.lang=="en")]
bad=E[E["ok_c_pset_pindala"]!=True][["room","storey","answer","c_pset_pindala","c_CONV"]]
print(bad.to_string())
M=Q[(Q.model_file=="bsc-molio_molio-with-uris.ifc")&(Q.fam=="room_area")&(Q.lang=="en")]
print("Molio: projected footprint failures"); print(M[M.ok_c_geom_proj!=True][["room","storey","answer","c_geom_proj","c_qto_net","c_geom_down_at_min"]].to_string())
print("Molio: FootPrint curve failures/NA"); print(M[M.ok_c_fp_curve!=True][["room","storey","answer","c_fp_curve"]].to_string())
print("Molio: down_at_min not exact"); x=M[M.c_geom_down_at_min.round(2)!=M.answer]; print(x[["room","storey","answer","c_geom_down_at_min","c_qto_net"]].to_string())

import pickle, collections, pandas as pd
Q=pd.read_pickle("solved.pkl")
pd.set_option("display.width",250)
C=Q[Q.fam.isin(["storey_count","model_count"])&(Q.lang=="en")]
cols=["path","fam","elem","storey","answer","c_CONV","c_bytype","c_not_decomposed","c_direct_plus_inspace","c_stairflight_direct","c_all_flowterminal"]
C=C.assign(path=C.path.str.replace("data/ifc_models/",""))
print(C[cols].to_string())
for m in ["bsc-esplanades_1807-ep-ar-v18.ifc","bsc-molio_molio-with-uris.ifc"]:
    F=pickle.load(open(f"facts_{m}.pkl","rb"))
    P=F["products"]
    for cls in ["IfcStair","IfcStairFlight","IfcRailing","IfcBeam","IfcColumn","IfcDoor","IfcWindow","IfcWall","IfcWallStandardCase","IfcSlab","IfcBuildingElementPart","IfcFlowTerminal"]:
        ps=[p for p in P if p["cls"]==cls]
        print(m[:14],cls,"total",len(ps),"contained",sum(1 for p in ps if p["cont"]),"decomposed_by",collections.Counter(p["dec"][0][0] for p in ps if p["dec"]),"neither",sum(1 for p in ps if not p["cont"] and not p["dec"]))

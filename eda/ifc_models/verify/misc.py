import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pickle, collections, pandas as pd, ifcopenshell, ifcopenshell.util.placement as up
DS=_DATA + "/data/ifc_models/"
F=pickle.load(open("facts_bsc-esplanades_1807-ep-ar-v18.ifc.pkl","rb"))
qs=collections.Counter((e["cls"],k[0]) for e in F["walls_slabs"] for k,v in e["q"].items() if v[0]!="prop")
print("Esplanades wall/slab quantity sets:",qs)
print("walls/slabs with any quantity set:",collections.Counter(e["cls"] for e in F["walls_slabs"] if any(v[0]!="prop" for v in e["q"].values())))
for m in ["bsc-esplanades_1807-ep-ar-v18.ifc","bsc-molio_molio-with-uris.ifc"]:
    f=ifcopenshell.open(DS+m)
    print(m)
    for s in f.by_type("IfcBuildingStorey"):
        print("   %-10s Elevation(m)=%8.3f  world z=%8.3f  diff=%7.3f"%(s.Name,s.Elevation/1000,up.get_local_placement(s.ObjectPlacement)[2,3]/1000,up.get_local_placement(s.ObjectPlacement)[2,3]/1000-s.Elevation/1000))
    b=f.by_type("IfcBuilding")[0]; si=f.by_type("IfcSite")[0]
    print("   building ElevationOfRefHeight",b.ElevationOfRefHeight,"site RefElevation",si.RefElevation)
Q=pd.read_pickle("solved.pkl")
ra=Q[(Q.fam=="room_area")&(Q.lang=="en")].answer.astype(float)
print("room EN answers n",len(ra),"min",ra.min(),"median",ra.median(),"max",ra.max(),"under 5",(ra<5).sum(),"distinct",ra.nunique(),"top",ra.value_counts().head(3).to_dict())
# seed-1 random sample of 150
S=Q.sample(150,random_state=1)
av=S[S.model_file!="kit-fzk-haus_ac20-fzk-haus.ifc"]
print("seed-1 sample: n",len(S),"FZK (untestable)",len(S)-len(av),"ok",int(av.ok_c_CONV.fillna(False).astype(bool).sum()),"/",len(av))
print(av.groupby("fam").agg(n=("answer","size"),ok=("ok_c_CONV",lambda s:int(s.fillna(False).astype(bool).sum()))))

import pickle, collections, pandas as pd, numpy as np
F=pickle.load(open("facts_bsc-molio_molio-with-uris.ifc.pkl","rb"))
Q=pd.read_pickle("solved.pkl")
Q=Q[(Q.model_file=="bsc-molio_molio-with-uris.ifc")&Q.fam.isin(["wall_length","wall_side_area","wall_volume","slab_volume"])&(Q.lang=="en")]
print(Q.groupby("fam").storey.apply(list).to_dict())
L=1e-3
W={e["id"]:e for e in F["walls_slabs"]}
alts={"wall_length":[("BaseQuantities","Length",L),("ArchiCADQuantities","Length of Reference Line",L),("ArchiCADQuantities","Length of the Wall on the Inside Face",L),("ArchiCADQuantities","Length of the Wall on the Outside Face",L),("ArchiCADQuantities","Length of the Wall at the Center",L),("ArchiCADQuantities","Average length of the Wall",L),("ArchiCADQuantities","3D Length",L)],
      "wall_side_area":[("BaseQuantities","NetSideArea",1),("BaseQuantities","GrossSideArea",1),("ArchiCADQuantities","Surface Area",1),("ArchiCADQuantities","Surface Area of the Wall Inside Face (Net)",1),("ArchiCADQuantities","Surface Area of the Wall Outside Face (Net)",1),("ArchiCADQuantities","Area",1)],
      "wall_volume":[("BaseQuantities","NetVolume",1),("BaseQuantities","GrossVolume",1),("ArchiCADQuantities","Volume (Net)",1),("ArchiCADQuantities","Volume (Gross)",1)],
      "slab_volume":[("BaseQuantities","NetVolume",1),("BaseQuantities","GrossVolume",1),("ArchiCADQuantities","Volume (Net)",1),("ArchiCADQuantities","Volume (Gross)",1)]}
st={s["name"]:s for s in F["storeys"]}
for fam,g in Q.groupby("fam"):
    print("==",fam)
    cls=("IfcSlab",) if fam=="slab_volume" else ("IfcWall",)
    for key in alts[fam]:
        rel=[];n_ok=0
        for _,r in g.iterrows():
            ids=[i for i,c,_ in st[r.storey]["direct"] if c in cls]
            vals=[W[i]["q"].get(key[:2],(None,None))[1] for i in ids]
            v=sum(x for x in vals if x is not None)*key[2]
            rel.append((v-r.answer)/r.answer); n_ok+=abs(v-r.answer)<=0.02*r.answer
        print("   %-55s %d/%d  mean rel %+.2f%%  range [%+.2f%%, %+.2f%%]"%(key[1],n_ok,len(g),100*np.mean(rel),100*min(rel),100*max(rel)))

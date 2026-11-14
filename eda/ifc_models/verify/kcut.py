import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pickle, collections, ifcopenshell, ifcopenshell.util.placement as up
DS=_DATA + "/data/ifc_models/"
for m,stn in [("bsc-molio_molio-with-uris.ifc","Kælder"),("bsc-esplanades_1807-ep-ar-v18.ifc","4.korrus")]:
    F=pickle.load(open(f"facts_{m}.pkl","rb")); Z=pickle.load(open(f"zr_{m}.pkl","rb"))
    f=ifcopenshell.open(DS+m)
    st={s["name"]:s for s in F["storeys"]}[stn]
    zc=up.get_local_placement(f.by_id(st["id"]).ObjectPlacement)[2,3]/1000+1.2
    P={p["guid"]:p for p in F["products"]}
    # top-level owner storey for each product
    byid={p["id"]:p for p in F["products"]}
    def owner(p):
        while p["dec"]: p=byid[p["dec"][0][2]]
        return p["cont"][0][1] if p["cont"] else (None if p["cls"]!="IfcSpace" else "space")
    cut=collections.Counter()
    for g,(z0,z1,*_) in Z.items():
        p=P.get(g)
        if p and z0<=zc<=z1 and p["cls"] in ("IfcStair","IfcStairFlight","IfcDoor","IfcWindow","IfcWall","IfcWallStandardCase","IfcColumn","IfcSlab","IfcRailing","IfcBuildingElementPart","IfcBeam"):
            o=owner(p); cut[(p["cls"],o)]+=1
    print("==",m,stn,"cut z",round(zc,3))
    for k,v in sorted(cut.items(),key=lambda kv:str(kv[0])): print("  ",v,k)

"""SVG-only storey counts for the PDF storey_count questions (class tags), two stair conventions."""
import collections, pickle, pandas as pd, xml.etree.ElementTree as ET
D="files/"; NS="{http://www.w3.org/2000/svg}"
Q=pd.read_pickle("qp.pkl"); Q=Q[Q.path.str.endswith(".pdf")&(Q.fam=="storey_count")]
CLS={"door":{"IfcDoor"},"window":{"IfcWindow"},"wall":{"IfcWall","IfcWallStandardCase"},"column":{"IfcColumn"},"space":{"IfcSpace"}}
res=collections.Counter(); rows=[]
for p,g in Q.groupby("path"):
    svg=p.split("/")[-1].replace(".pdf",".svg")
    c=collections.Counter(x.get("class") for x in ET.parse(D+svg).getroot().iter(NS+"g") if x.get("data-guid"))
    print(svg, dict(c))
    for _,r in g.iterrows():
        if r.elem=="stair": a=c["IfcStair"]; b=c["IfcStair"]+c["IfcStairFlight"]
        else: a=b=sum(c[k] for k in CLS[r.elem])
        rows.append((svg[:20],r.lang,r.elem,r.answer,a,b)); res["stair_only"]+=a==r.answer; res["stair_or_flight"]+=b==r.answer
print(pd.DataFrame(rows,columns=["svg","lang","elem","answer","n_IfcStair_only","n_with_flights"]).to_string())
print(dict(res),"of",len(rows))
# who owns the 4 IfcStair drawn on the Molio Kaelder plan
F=pickle.load(open("facts_bsc-molio_molio-with-uris.ifc.pkl","rb")); P={x["id"]:x for x in F["products"]}; G={x["guid"]:x for x in F["products"]}
root=ET.parse(D+"bsc-molio_molio-with-uris_plan-02-klder.svg").getroot()
for x in root.iter(NS+"g"):
    if x.get("class")=="IfcStair":
        p=G[x.get("data-guid")]; chain=[]
        while p["dec"]: p=P[p["dec"][0][2]]; chain.append((p["cls"],p["name"]))
        print("drawn IfcStair",x.get("data-name"),"-> top parent",chain[-1] if chain else None,"contained in",p["cont"])

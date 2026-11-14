# Score PDF-targeted storey-count questions using only class tags in the sibling SVG (no IFC).
import pickle, pandas as pd
Q = pd.read_pickle("ifc_q_parsed.pkl"); S = pickle.load(open("svg_inventory.pkl", "rb"))
P = Q[(Q.ext == "pdf") & (Q.family == "storey_count")].copy()
MAP = {"door": ["IfcDoor"], "window": ["IfcWindow"], "wall": ["IfcWall", "IfcWallStandardCase"], "column": ["IfcColumn"], "space": ["IfcSpace"]}
def pred(r, stair_classes):
    cc = S[r.file.replace(".pdf", ".svg")]["class_counts"]
    cls = stair_classes if r.what == "stair" else MAP[r.what]
    return sum(cc.get(c, 0) for c in cls)
for name, sc in [("stair=IfcStair", ["IfcStair"]), ("stair=IfcStair+IfcStairFlight", ["IfcStair", "IfcStairFlight"])]:
    P["pred"] = P.apply(pred, axis=1, stair_classes=sc); P["ok"] = P.pred == P.answer.astype(int)
    print(name, "->", P.ok.sum(), "/", len(P)); print(P.groupby("what").ok.agg(["sum", "size"]).T.to_string())
print(P[["file", "what", "lang", "pred", "answer"]].to_string())

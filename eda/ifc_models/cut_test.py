import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Hypothesis test: storey-count questions are only asked when every contained element of that class crosses the 1.20 m plan cut.
import sys, numpy as np, pandas as pd
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue, ifcopenshell.util.placement as up, ifcopenshell.util.unit as uu
DS = _DATA + "/"
model = sys.argv[1]
f = ifcopenshell.open(DS + f"data/ifc_models/{model}.ifc"); k = uu.calculate_unit_scale(f)
st = ifcopenshell.geom.settings(); st.set("use-world-coords", True)
def zrange(e):
    zs = []
    for x in [e] + list(ue.get_decomposition(e)):
        try:
            v = np.array(ifcopenshell.geom.create_shape(st, x).geometry.verts).reshape(-1, 3); zs += [v[:, 2].min(), v[:, 2].max()]
        except Exception: pass
    return (min(zs), max(zs)) if zs else (None, None)
CLS = {"door": "IfcDoor", "window": "IfcWindow", "wall": "IfcWall", "column": "IfcColumn", "stair": "IfcStair", "space": "IfcSpace"}
Q = pd.read_pickle("ifc_q_parsed.pkl"); Q = Q[(Q.model == model) & (Q.family == "storey_count") & (Q.lang == "en")]
asked = set(zip(Q.storey, Q.what))
rows = []
for s in f.by_type("IfcBuildingStorey"):
    z0 = up.get_local_placement(s.ObjectPlacement)[2, 3] * k
    cut = z0 + 1.2
    kids = [e for r in s.ContainsElements or [] for e in r.RelatedElements] + [e for r in s.IsDecomposedBy or [] for e in r.RelatedObjects]
    for w, c in CLS.items():
        X = [e for e in kids if e.is_a(c)]
        n_cut = 0
        for e in X:
            lo, hi = zrange(e)
            if lo is not None and lo <= cut <= hi: n_cut += 1
        rows.append({"storey": s.Name, "what": w, "n_ifc": len(X), "n_cut": n_cut, "asked": (s.Name, w) in asked})
D = pd.DataFrame(rows); D["all_cut"] = (D.n_ifc == D.n_cut) & (D.n_ifc > 0)
print(D.pivot(index="storey", columns="what", values=["n_ifc", "n_cut", "asked"]).to_string())
print(pd.crosstab(D.asked, D.all_cut, rownames=["asked"], colnames=["n_ifc>0 and all cross the cut"]))
D.to_csv(f"cut_test_{model}.csv", index=False)

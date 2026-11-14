# Reproduce ifc_models answers from IFC facts with several candidate methods; score with the official tolerance.
import pickle, math, numpy as np, pandas as pd
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500); pd.set_option("display.max_colwidth", 80)
Q = pd.read_pickle("ifc_q_parsed.pkl")
F = {}
for m in ["bsc-esplanades_1807-ep-ar-v18", "bsc-molio_molio-with-uris", "bsc-clinic_clinic-plumbing"]:
    d = pickle.load(open(f"facts_{m}.pkl", "rb")); E = pd.DataFrame(d["els"])
    E["top"] = E.direct_container.eq("IfcBuildingStorey") | E.parent.eq("IfcBuildingStorey")  # directly under a storey
    F[m] = E
def ok(pred, ans, typ):
    if pred is None or (isinstance(pred, float) and math.isnan(pred)): return False
    if typ == "count": return round(pred) == int(ans) and abs(pred - round(pred)) < 1e-9
    return abs(pred - float(ans)) <= 0.02 * abs(float(ans))
def col(E, c):
    return pd.to_numeric(E[c], errors="coerce") if c in E else pd.Series(np.nan, index=E.index)
def methods(r):
    E = F.get(r.model)
    if E is None: return {}
    out = {}
    fam, S = r.family, r.storey
    if fam == "room_area":
        sp = E[(E.cls == "IfcSpace") & (E.storey == S)]
        sp = sp[(sp.LongName.astype(str) + " (" + sp.Name.astype(str) + ")") == r.room]
        out["n_label_matches"] = len(sp)
        if len(sp):
            out["geo_footprint"] = col(sp, "g_footprint").iloc[0]
            out["geo_floor_face"] = col(sp, "g_bottom_minz").iloc[0]
            bq = col(sp, "BaseQuantities.NetFloorArea").iloc[0]
            out["qto_else_geo_footprint"] = bq if bq == bq else out["geo_footprint"]
            out["bq_NetFloorArea"] = col(sp, "BaseQuantities.NetFloorArea").iloc[0]
            out["bq_GrossFloorArea"] = col(sp, "BaseQuantities.GrossFloorArea").iloc[0]
            out["ar_120_Pindala"] = pd.to_numeric(sp["AR_Ruum.120_Pindala"].astype(str).str.replace(",", "."), errors="coerce").iloc[0] if "AR_Ruum.120_Pindala" in sp else np.nan
    elif fam == "storey_space_area":
        sp = E[(E.cls == "IfcSpace") & (E.storey == S)]
        out["geo_footprint_sum"] = col(sp, "g_footprint").sum()
        out["geo_footprint_round2_sum"] = col(sp, "g_footprint").round(2).sum()
        out["geo_floor_face_sum"] = col(sp, "g_bottom_minz").sum()
        out["qto_else_geo_footprint_sum"] = col(sp, "BaseQuantities.NetFloorArea").fillna(col(sp, "g_footprint")).sum()
        out["bq_NetFloorArea_sum"] = col(sp, "BaseQuantities.NetFloorArea").sum(min_count=1)
        out["ar_Pindala_sum"] = pd.to_numeric(sp["AR_Ruum.120_Pindala"].astype(str).str.replace(",", "."), errors="coerce").sum(min_count=1) if "AR_Ruum.120_Pindala" in sp else np.nan
    elif fam in ("storey_count", "model_count"):
        cls = {"door": "IfcDoor", "window": "IfcWindow", "wall": "IfcWall", "column": "IfcColumn", "beam": "IfcBeam", "stair": "IfcStair", "space": "IfcSpace", "sanitary": "IfcFlowTerminal"}[r.what]
        X = E[E.cls == cls]
        if fam == "storey_count": X = X[X.storey == S]
        out["all_incl_nested"] = len(X)
        out["top_level_only"] = int(X.top.sum())
    elif fam in ("wall_length", "wall_side_area", "wall_volume", "slab_volume"):
        cls = "IfcSlab" if fam == "slab_volume" else "IfcWall"
        X = E[(E.cls == cls) & (E.storey == S)]
        q = {"wall_length": "BaseQuantities.Length", "wall_side_area": "BaseQuantities.NetSideArea", "wall_volume": "BaseQuantities.NetVolume", "slab_volume": "BaseQuantities.NetVolume"}[fam]
        v = col(X, q)
        if fam == "wall_length": v = v / 1000.0
        out["bq_sum"] = v.sum(min_count=1)
        out["bq_n_missing"] = int(v.isna().sum())
        out["n_elems"] = len(X)
        if fam == "wall_volume" or fam == "slab_volume": out["geo_volume_sum"] = col(X, "g_volume").sum()
        if fam == "wall_side_area": out["geo_maxside_sum"] = col(X, "g_maxside").sum(); out["geo_side_sum"] = col(X, "g_side").sum()
        if fam == "wall_volume": out["bq_gross_sum"] = col(X, "BaseQuantities.GrossVolume").sum()
        if fam == "slab_volume": out["bq_gross_sum"] = col(X, "BaseQuantities.GrossVolume").sum()
        if fam == "wall_side_area": out["bq_gross_sum"] = col(X, "BaseQuantities.GrossSideArea").sum()
    return out
if __name__ == "__main__":
    rows = []
    for r in Q.itertuples():
        m = methods(r)
        for k, v in m.items():
            if k.startswith("n_") or k.endswith("_missing") or k == "n_elems": continue
            rows.append({"idx": r.Index, "file": r.file, "ext": r.ext, "family": r.family, "what": r.what, "method": k, "pred": v, "answer": r.answer, "ok": ok(v, r.answer, r.type)})
    R = pd.DataFrame(rows); R.to_pickle("solve_results.pkl")
    t = R.groupby(["family", "method"]).ok.agg(["sum", "size"]); t["k/n"] = t["sum"].astype(str) + "/" + t["size"].astype(str)
    print(t["k/n"].to_string())
    print("\nquestions with no IFC available (model missing in preview):", Q[~Q.model.isin(F)].shape[0])

# Score PDF-targeted questions using only the PDF (vector polygons + text layer), no IFC.
import pandas as pd, math
Q = pd.read_pickle("ifc_q_parsed.pkl"); A = pd.read_csv("pdf_room_areas.csv")
P = Q[Q.ext == "pdf"].copy()
def pred(r):
    a = A[A.file == r.file]
    if r.family == "room_area":
        m = a[a.label == r.room]; return m.area_m2.iloc[0] if len(m) == 1 else None
    if r.family == "storey_space_area": return a.area_m2.sum()
    if r.family == "storey_count" and r.what == "space": return float(len(a))
    return None  # not attempted from the PDF alone
P["pred"] = P.apply(pred, axis=1)
P["ok"] = [p is not None and not (isinstance(p, float) and math.isnan(p)) and (round(p) == a if t == "count" else abs(p - a) <= 0.02 * abs(a)) for p, a, t in zip(P.pred, P.answer.astype(float), P.type)]
P["attempted"] = P.pred.notna()
t = P.groupby(["family", "what"], dropna=False).agg(n=("ok", "size"), attempted=("attempted", "sum"), correct=("ok", "sum"))
print(t.to_string()); print("total", P.ok.sum(), "/", len(P))
x = P[P.family == "room_area"]; rel = ((x.pred - x.answer.astype(float)).abs() / x.answer.astype(float))
print("room_area from PDF: max rel err %.4f, median %.5f" % (rel.max(), rel.median()))
print("exact after rounding to 2 dp:", (x.pred.round(2) == x.answer.astype(float)).sum(), "/", len(x))
P.to_csv("pdf_only_results.csv", index=False)

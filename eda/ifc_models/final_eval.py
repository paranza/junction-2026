# Score final_solver on: all ifc_models questions, a seed-0 random sample of 150, and every length/volume question.
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from final_solver import answer
Q = pd.read_pickle("ifc_q_parsed.pkl")
t0 = time.time(); res = []
for r in Q.itertuples():
    v, gids, how = answer(r.path, r.question)
    a = float(r.answer)
    ok = v is not None and ((v == a) if r.type == "count" else abs(v - a) <= 0.02 * abs(a))
    exact = v is not None and round(v, 3) == round(a, 3)
    res.append({"idx": r.Index, "file": r.file, "ext": r.ext, "family": r.family, "what": r.what, "lang": r.lang, "type": r.type,
                "answer": a, "pred": v, "ok": ok, "exact": exact, "how": how, "n_guids": len(gids), "question": r.question})
R = pd.DataFrame(res); R.to_csv("final_eval_results.csv", index=False)
print("runtime %.1f s for %d questions" % (time.time() - t0, len(R)))
def kn(x): return f"{int(x.ok.sum())}/{len(x)}"
avail = R[R.how != "model IFC not available"]
print("ALL questions:", kn(R), "| with IFC available:", kn(avail), "| exact after rounding:", int(avail.exact.sum()), "/", len(avail))
print(avail.groupby(["family", "what"], dropna=False).apply(kn, include_groups=False).to_string())
print(avail.groupby(["family", "lang"]).apply(kn, include_groups=False).to_string())
print("how:", avail.groupby(["family", "how"]).size().to_string())
S = R.sample(n=150, random_state=0)
print("\nRANDOM SAMPLE n=150 seed=0:", kn(S), "| excluding preview-missing IFC:", kn(S[S.how != "model IFC not available"]), "| missing IFC in sample:", int((S.how == "model IFC not available").sum()))
print(S.groupby("family").apply(kn, include_groups=False).to_string())
LV = R[R.type.isin(["length", "volume"])]
print("\nALL length+volume:", kn(LV), "| with IFC:", kn(LV[LV.how != "model IFC not available"]))
print(LV.groupby(["family", "file"]).apply(kn, include_groups=False).to_string())
print("\nfailures:"); print(avail[~avail.ok][["file", "question", "pred", "answer", "how"]].to_string())

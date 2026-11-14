"""Answer every English swiss_dwellings question from the DXF and score with the official rules."""
import sys, os, re, collections, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dxf_model as M, fixtures as FX
import fixtures_eval as FE  # reuse kind()
import pandas as pd
WD = os.path.dirname(os.path.abspath(__file__))
OUTDOOR = {"Balkon", "Balcon", "Balcone", "Loggia", "Terrasse", "Terrazza", "Terrazzo", "Veranda", "Sitzplatz", "Gartensitzplatz"}
SHAFT_VOID = {"Schacht", "Luftraum", "Gaine", "Vide", "Cavedio", "Vuoto", "Gaine technique", "Shaft", "Void"}
RESIDENTIAL_TAG = re.compile(r"^(App\.|Whg\.|Appart\.)\s")

cache = {}
def model(name):
    if name not in cache:
        m = M.load(name)
        msp = m["msp"]
        m["doors"] = sum(1 for e in msp.query("LWPOLYLINE[layer=='DOOR']") if len(e) == 5)
        m["windows"] = sum(1 for e in msp.query("LWPOLYLINE[layer=='WINDOW']") if e.closed)
        m["fix"] = collections.Counter(FE.kind(g) for g in FX.groups(msp))
        cache[name] = m
    return cache[name]

def answer(fam, q, m, variant="base"):
    rooms = m["rooms"]
    if fam == "count_label":
        lab = re.search(r"labelled '(.*)' are there", q).group(1)
        return sum(1 for r in rooms if r["label"] == lab)
    if fam == "count_apartments":
        return sum(1 for u in m["units"] if u["tag"] and RESIDENTIAL_TAG.match(u["tag"]))
    if fam == "count_doors": return m["doors"]
    if fam == "count_windows": return m["windows"]
    if fam == "count_wc": return m["fix"].get("wc", 0)
    if fam == "count_washbasins": return m["fix"].get("washbasin", 0)
    if fam == "count_bathtubs": return m["fix"].get("bathtub", 0)
    if fam == "count_showers": return m["fix"].get("shower", 0)
    if fam == "area_room":
        num = re.search(r"room ([A-Z]?\d*\.\d+) \(", q).group(1)
        r = [r for r in rooms if r["num"] == num]
        return round(r[0]["net"], 2) if r else None
    if fam == "area_label_total":
        lab = re.search(r"labelled '(.*)' on this floor", q).group(1)
        return round(sum(r["net"] for r in rooms if r["label"] == lab), 2)
    if fam == "area_apartment":
        a = re.search(r"apartment ([A-Z]+) in", q).group(1)
        rr = [r for r in rooms if r["unit"] and r["unit"].split()[-1] == a and RESIDENTIAL_TAG.match(r["unit"]) and r["label"] not in OUTDOOR]
        return round(sum(r["net"] for r in rr), 2)
    if fam == "area_total_indoor":
        rr = [r for r in rooms if r["label"] not in OUTDOOR and r["label"] not in SHAFT_VOID]
        return round(sum(r["net"] for r in rr), 2)

def correct(fam, pred, gold):
    if pred is None: return False
    if fam.startswith("count"): return int(pred) == int(gold)
    return abs(pred - gold) <= 0.02 * abs(gold)

if __name__ == "__main__":
    en = pd.read_csv(f"{WD}/questions_en_families.csv")
    preds = []
    for _, row in en.iterrows():
        name = os.path.basename(row.path)[:-4]
        p = answer(row.family, row.question, model(name))
        preds.append(p)
    en["pred"] = preds
    en["ok"] = [correct(f, p, g) for f, p, g in zip(en.family, en.pred, en.answer)]
    en["relerr"] = [(abs(p - g) / g if (p is not None and g) else None) for p, g in zip(en.pred, en.answer)]
    print(en.groupby("family").ok.agg(["sum", "count"]).to_string())
    print("TOTAL", en.ok.sum(), "/", len(en))
    en.to_csv(f"{WD}/eval_dxf.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 90)
    print(en[~en.ok][["path", "family", "question", "answer", "pred"]].assign(path=lambda d: d.path.str[21:-4]).to_string())

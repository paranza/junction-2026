"""Baselines that use less of the PDF: (1) text layer only, (2) printed-area lookup coverage, (3) visual-count proxies."""
import os, sys, re
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_solver as S

WD = os.path.dirname(os.path.abspath(__file__))
OUT = {"Balkon", "Balcon", "Balcone", "Loggia", "Terrasse", "Terrazza"}
en = pd.read_csv(f"{WD}/eval_pdf.csv")
dw = pd.read_csv(f"{WD}/doors_windows.csv").set_index("file")
cache = {}
res = []
for _, r in en.iterrows():
    name = os.path.basename(r.path)[:-4]
    if name not in cache: cache[name] = S.load(name)
    m = cache[name]; rooms = m["rooms"]; fam = r.family; q = r.question
    pred = None
    if fam == "count_label":
        lab = re.search(r"labelled '(.*)' are there", q).group(1)
        pred = sum(1 for x in rooms if x["label"] == lab)
    elif fam == "count_apartments":  # count residential tags in the text layer
        pred = sum(1 for x in m["units"] if x["tag"] and S.RES_TAG.match(x["tag"]))
    elif fam == "area_room":
        num = re.search(r"room ([A-Z]?\d*\.\d+) \(", q).group(1)
        pred = next((x["printed"] for x in rooms if x["num"] == num), None)
    elif fam == "area_label_total":
        lab = re.search(r"labelled '(.*)' on this floor", q).group(1)
        sel = [x for x in rooms if x["label"] == lab]
        pred = round(sum(x["printed"] for x in sel), 2) if sel and all(x["printed"] is not None for x in sel) else None
    elif fam == "area_total_indoor":  # label-based exclusion, printed areas only
        sel = [x for x in rooms if x["label"] not in OUT]
        pred = round(sum(x["printed"] for x in sel), 2) if all(x["printed"] is not None for x in sel) else None
    elif fam == "count_doors":  # what a perfect visual count would see: unique door frames
        pred = dw.loc[name, "frames_unique"]
    elif fam == "count_windows":
        pred = dw.loc[name, "win_unique"]
    res.append(pred)
en["pred_text"] = res
en["ok_text"] = [S.correct(f, p, g) if pd.notna(p) else False for f, p, g in zip(en.family, en.pred_text, en.answer)]
en["answerable_text"] = en.pred_text.notna()
print(en.groupby("family")[["answerable_text", "ok_text"]].sum().join(en.groupby("family").size().rename("n")).to_string())
print("NOTE: count_doors/count_windows rows here = a perfect visual count of distinct symbols (unique geometry), not text.")
files_printed = sum(1 for m in cache.values() if any(x["printed"] is not None for x in m["rooms"]))
print("files with printed areas:", files_printed, "/", len(cache))
ar = en[en.family.str.startswith("area")]
print("area questions on files with printed areas:", ar.path.map(lambda p: any(x["printed"] is not None for x in cache[os.path.basename(p)[:-4]]["rooms"])).sum(), "/", len(ar))
# unlabelled rooms: are they ever printed? what categories?
import collections
c = collections.Counter((x["cat"], x["printed"] is not None) for m in cache.values() for x in m["rooms"] if x["label"] is None)
print("unlabelled rooms by fill category and printed-area presence:", dict(c))
c2 = collections.Counter((x["cat"]) for m in cache.values() for x in m["rooms"])
print("all numbered rooms by fill category:", dict(c2))
c3 = collections.Counter((x["label"]) for m in cache.values() for x in m["rooms"] if x["cat"] == "outdoor")
print("labels of outdoor-filled rooms:", dict(c3))
c4 = collections.Counter((x["label"]) for m in cache.values() for x in m["rooms"] if x["cat"] == "common")
print("labels of common-filled rooms:", dict(c4))
c5 = collections.Counter((x["label"]) for m in cache.values() for x in m["rooms"] if x["cat"] == "shaft")
print("labels of shaft-filled numbered rooms:", dict(c5))
en.to_csv(f"{WD}/eval_text_only.csv", index=False)

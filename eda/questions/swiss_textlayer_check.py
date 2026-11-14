"""Grounding check for swiss_dwellings: are question labels, room ids and areas present in the PDF text layer,
and do text-only answers reproduce the ground truth (counts exact, areas within 2%)?
English rows only (twins share the answer). Run: python -I swiss_textlayer_check.py"""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
import sys, re
sys.path.insert(0, _ROOT + "/eda/questions")
import pymupdf
import pandas as pd
from qlib import DATASET, WORK

q = pd.read_csv(WORK + "questions_annotated.csv")
q = q[(q.source == "swiss_dwellings") & (q.lang == "en")].copy()
NUM = re.compile(r"^[A-Z]?\d+\.\d{2}$")
AREA = re.compile(r"^(\d+(?:\.\d+)?) m²$")
APT = re.compile(r"^(Whg\.|App\.|Appt\.|Apt\.|Wohnung|Appartement|Appartamento)\s*([A-Z])$")
OUTDOOR = re.compile(r"^(Balkon|Balcon|Balcone|Loggia|Terrasse|Terrazza|Terrazzo|Sitzplatz|Gartensitzplatz|Veranda|Dachterrasse)$", re.I)


def rooms_from_pdf(path):
    page = pymupdf.open(DATASET + path)[0]
    spans = []
    for bl in page.get_text("dict")["blocks"]:
        for ln in bl.get("lines", []):
            for sp in ln["spans"]:
                t = sp["text"].strip()
                if t:
                    spans.append(dict(t=t, x=(sp["bbox"][0] + sp["bbox"][2]) / 2, y0=sp["bbox"][1], y1=sp["bbox"][3],
                                      bold="Bold" in sp["font"], size=sp["size"]))
    nums = [s for s in spans if s["bold"] and NUM.match(s["t"])]
    areas = [s for s in spans if AREA.match(s["t"])]
    apts = [s for s in spans if APT.match(s["t"])]
    labels = [s for s in spans if not s["bold"] and not AREA.match(s["t"]) and not APT.match(s["t"])]
    rooms = []
    for n in nums:
        tol = 1.6 * n["size"]
        lab = [l for l in labels if abs(l["x"] - n["x"]) < 3 * n["size"] and 0 <= n["y0"] - l["y1"] < tol]
        ar = [a for a in areas if abs(a["x"] - n["x"]) < 3 * n["size"] and 0 <= a["y0"] - n["y1"] < tol]
        lab = min(lab, key=lambda l: n["y0"] - l["y1"]) if lab else None
        ar = min(ar, key=lambda a: a["y0"] - n["y1"]) if ar else None
        rooms.append(dict(num=n["t"], label=lab["t"] if lab else None, area=float(AREA.match(ar["t"]).group(1)) if ar else None))
    return pd.DataFrame(rooms), [a["t"] for a in apts], [s["t"] for s in spans]


def ok(pred, truth, fam):
    if pred is None:
        return False
    if fam.startswith("count"):
        return int(pred) == int(truth)
    return abs(pred - truth) <= 0.02 * abs(truth)


res = []
summary_files = []
for path, g in q.groupby("path"):
    rooms, apts, alltext = rooms_from_pdf(path)
    summary_files.append(dict(path=path, rooms=len(rooms), rooms_with_label=rooms.label.notna().sum(), rooms_with_area=rooms.area.notna().sum(),
                              apt_labels=len(apts)))
    for r in g.itertuples():
        slot = r.slots if isinstance(r.slots, str) else ""
        pred, note = None, ""
        if r.family == "count_rooms_by_label":
            pred = int((rooms.label == slot).sum())
            note = f"raw text hits={sum(t == slot for t in alltext)}"
        elif r.family == "area_room_by_id":
            rid = re.search(r"room ([A-Z]?\d+\.\d{2})", r.question).group(1)
            m = rooms[rooms.num == rid]
            if len(m):
                pred = m.area.iloc[0] if pd.notna(m.area.iloc[0]) else None
                note = f"label_in_pdf={m.label.iloc[0]!r} label_matches={m.label.iloc[0] == slot}"
            else:
                note = "room id not found"
        elif r.family == "area_rooms_by_label":
            m = rooms[rooms.label == slot]
            pred = m.area.sum() if len(m) and m.area.notna().all() else None
            note = f"n_rooms={len(m)} missing_area={m.area.isna().sum()}"
        elif r.family == "area_floor_total":
            m = rooms[rooms.area.notna() & ~rooms.label.fillna("").str.match(OUTDOOR)]
            pred = m.area.sum()
            note = f"summed={len(m)} rooms_without_area={rooms.area.isna().sum()}"
        elif r.family == "count_apartments":
            pred = len(apts)
        elif r.family == "area_apartment":
            note = "needs apartment membership (geometry); not tested"
        else:
            note = "symbol count; not a text-layer question"
        res.append(dict(line=r.line, path=path, family=r.family, slot=slot, answer=r.answer, pred=pred,
                        correct=ok(pred, float(r.answer), r.family) if pred is not None else None, note=note))

res = pd.DataFrame(res)
res.to_csv(WORK + "swiss_textlayer_check.csv", index=False)
sf = pd.DataFrame(summary_files)
print("files:", len(sf), " numbered rooms:", sf.rooms.sum(), " with label:", sf.rooms_with_label.sum(), " with printed area:", sf.rooms_with_area.sum())
print("files where every numbered room has a printed area:", (sf.rooms == sf.rooms_with_area).sum())
t = res[res.correct.notna()]
print(t.groupby("family").correct.agg(["sum", "size"]).assign(rate=lambda d: (d["sum"] / d["size"]).round(3)))
print("not testable from text:", res[res.correct.isna()].groupby("family").size().to_dict())
for fam in ["count_rooms_by_label", "area_room_by_id", "area_rooms_by_label", "area_floor_total", "count_apartments"]:
    bad = res[(res.family == fam) & (res.correct == False)]
    print(f"--- failures {fam}: {len(bad)}")
    print(bad.head(12).to_string(index=False))

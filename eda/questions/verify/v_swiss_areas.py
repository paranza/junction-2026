import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Whole-page printed-area checks (F8) on locally materialized swiss PDFs.
import json, os, re, collections
import pymupdf
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
DATALESS = 0x40000000
ID_RE = re.compile(r"^U?\d+\.\d+$"); AREA_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*m²$")
OUTDOOR = {"Balkon", "Balcon", "Balcone", "Loggia", "Terrasse", "Terrazza"}
files = sorted(set(r["path"] for r in rows if r["path"].startswith("data/swiss_dwellings/")))
local = [f for f in files if not (os.stat(os.path.join(DS, f)).st_flags & DATALESS)]
T = collections.Counter(); nrooms = nprinted = 0; allprinted = 0
for f in local:
    pg = pymupdf.open(os.path.join(DS, f))[0]
    sp = []
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                t = s["text"].strip()
                if t: x0, y0, x1, y1 = s["bbox"]; sp.append(dict(t=t, cx=(x0+x1)/2, cy=(y0+y1)/2, h=y1-y0))
    ids = [s for s in sp if ID_RE.match(s["t"])]
    def near(s, pred, below):
        best = None
        for o in sp:
            if o is s or not pred(o["t"]): continue
            dy = (o["cy"] - s["cy"]) if below else (s["cy"] - o["cy"]); dx = abs(o["cx"] - s["cx"])
            if 0 < dy < 2.5 * max(s["h"], o["h"]) and dx < 0.6 * 40:
                d = dx + dy
                if best is None or d < best[0]: best = (d, o)
        return best[1]["t"] if best else None
    room = {}
    for s in ids:
        a = near(s, lambda t: bool(AREA_RE.match(t)), True)
        lab = near(s, lambda t: not ID_RE.match(t) and not AREA_RE.match(t), False)
        room[s["t"]] = (float(AREA_RE.match(a).group(1)) if a else None, lab)
    nrooms += len(room); nprinted += sum(1 for v in room.values() if v[0] is not None)
    full = all(v[0] is not None for v in room.values())
    allprinted += full
    for i, r in enumerate(rows):
        if r["path"] != f or langs[i] != "en": continue
        q, a = r["question"], r["answer"]
        m = re.match(r"What is the net floor area of room (\S+) \('(.*)'\) in m²\?$", q)
        if m:
            v = room.get(m.group(1)); T["room found"] += v is not None
            if v: T["room label match"] += v[1] == m.group(2)
            if v and v[0] is not None: T["room printed"] += 1; T["room printed within2%"] += abs(v[0] - a) <= 0.02 * a
            continue
        m = re.match(r"What is the total net area in m² of all rooms labelled '(.*)' on this floor\?$", q)
        if m and full:
            est = sum(v[0] for v in room.values() if v[1] == m.group(1)); T["labelsum testable"] += 1; T["labelsum within2%"] += abs(est - a) <= 0.02 * a
            continue
        if q.startswith("What is the total net floor area in m² of all numbered") and full:
            est = sum(v[0] for v in room.values() if v[1] not in OUTDOOR); T["floor testable"] += 1; T["floor within2%"] += abs(est - a) <= 0.02 * a
            if abs(est - a) > 0.02 * a: print("floor miss", f, est, a)
print("local files", len(local), "numbered rooms", nrooms, "printed", nprinted, round(100 * nprinted / nrooms, 1), "% ; files with all printed", allprinted)
print(dict(T))

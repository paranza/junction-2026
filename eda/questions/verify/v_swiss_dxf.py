import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Answerability of swiss area/count questions from the DXF twin's semantic layers (ROOM_OUTLINE, UNIT_OUTLINE, ROOM_TEXT, DOOR, WINDOW, FIXTURE).
import json, os, re, collections
import ezdxf
from shapely.geometry import Polygon, Point
DS = _DATA + ""
OUT = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
ID = re.compile(r"^U?\d+\.\d+$"); AREA = re.compile(r"^\d+(\.\d+)?\s*m²$"); APT = re.compile(r"^(Whg\.|App\.)\s*(\S+)$")
OUTDOOR = {"Balkon", "Balcon", "Balcone", "Loggia", "Terrasse", "Terrazza"}
def ok(p, a, t): return p is not None and (p == a if t == "count" else abs(p - a) <= 0.02 * a)
T = collections.Counter(); misses = collections.defaultdict(list); ents = collections.defaultdict(list)
files = sorted(set(r["path"] for r in rows if r["path"].startswith("data/swiss_dwellings/")))
for f in files:
    doc = ezdxf.readfile(os.path.join(DS, f[:-4] + ".dxf")); m = doc.modelspace()
    polys = lambda layer: [Polygon([p[:2] for p in e.get_points()]) for e in m if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == layer and len(e) >= 3]
    rooms = polys("ROOM_OUTLINE"); units = polys("UNIT_OUTLINE")
    texts = [(e.dxf.text.strip(), Point(e.dxf.insert[0], e.dxf.insert[1])) for e in m if e.dxftype() == "TEXT" and e.dxf.layer == "ROOM_TEXT"]
    def poly_at(pt, P):
        c = [p for p in P if p.contains(pt)]
        return min(c, key=lambda p: p.area) if c else None
    room_of = {}  # room polygon index -> (id, label)
    for t, pt in texts:
        p = poly_at(pt, rooms)
        if p is None: continue
        k = rooms.index(p); d = room_of.setdefault(k, {"id": None, "labels": []})
        if ID.match(t): d["id"] = t
        elif not AREA.match(t) and not APT.match(t): d["labels"].append(t)
    by_id = {d["id"]: (rooms[k].area, d["labels"]) for k, d in room_of.items() if d["id"]}
    counts = {L: collections.Counter(e.dxftype() for e in m if e.dxf.layer == L) for L in ("DOOR", "WINDOW", "FIXTURE")}
    for i, r in enumerate(rows):
        if r["path"] != f or langs[i] != "en": continue
        q, a, t = r["question"], r["answer"], r["type"]; pred = None
        mm = re.match(r"What is the net floor area of room (\S+) \('(.*)'\) in m²\?$", q)
        if mm: fam = "room area by id"; v = by_id.get(mm.group(1)); pred = v[0] if v else None
        elif (mm := re.match(r"What is the total net area in m² of all rooms labelled '(.*)' on this floor\?$", q)):
            fam = "label area sum"; pred = sum(rooms[k].area for k, d in room_of.items() if mm.group(1) in d["labels"])
        elif q.startswith("What is the total net floor area in m² of all numbered"):
            fam = "floor total"; pred = sum(rooms[k].area for k, d in room_of.items() if d["id"] and not (set(d["labels"]) & OUTDOOR))
        elif (mm := re.match(r"What is the net floor area of apartment (\S+)", q)):
            fam = "apartment area"; L = mm.group(1)
            pts = [pt for tx, pt in texts if APT.match(tx) and APT.match(tx).group(2) == L]
            u = poly_at(pts[0], units) if pts else None
            if u is not None:
                inside = [k for k, d in room_of.items() if d["id"] and u.contains(rooms[k].representative_point())]
                pred = sum(rooms[k].area for k in inside if not (set(room_of[k]["labels"]) & OUTDOOR))
                T[("apartment area", "unit-outline area within 2%")] += ok(u.area, a, t)
                T[("apartment area", "rooms incl outdoor within 2%")] += ok(sum(rooms[k].area for k in inside), a, t)
        else:
            fam = None
            for key, L in [("doors", "DOOR"), ("windows", "WINDOW"), ("toilets", "FIXTURE"), ("washbasins", "FIXTURE"), ("bathtubs", "FIXTURE"), ("showers", "FIXTURE"), ("labelled", None), ("apartments", None)]:
                if key in q: fam = "count:" + key; break
            ents[fam].append((a, dict(counts["DOOR"]), dict(counts["WINDOW"]), dict(counts["FIXTURE"])))
            continue
        T[(fam, "n")] += 1; T[(fam, "ok")] += ok(pred, a, t)
        if not ok(pred, a, t): misses[fam].append((f[-30:], q[:60], None if pred is None else round(pred, 2), a))
for k, v in sorted(T.items()): print(v, k)
for fam, ms in misses.items():
    print("MISSES", fam, len(ms))
    for x in ms[:6]: print("   ", x)
# simple ratio probe for symbol counts: does any entity-type count equal the answer?
for fam in ("count:doors", "count:windows"):
    v = ents[fam]; L = "DOOR" if "door" in fam else "WINDOW"; idx = 1 if L == "DOOR" else 2
    for typ in ("LWPOLYLINE", "ARC"):
        for div in (1, 2, 3, 4):
            hit = sum(1 for e in v if e[idx].get(typ, 0) / div == e[0])
            if hit: print(fam, typ, "/", div, "matches", hit, "/", len(v))
json.dump({k: v for k, v in ents.items()}, open(os.path.join(OUT, "swiss_dxf_counts.json"), "w"))

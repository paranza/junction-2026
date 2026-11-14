import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Variant exclusion rules for swiss floor totals and apartment areas from DXF; door-count residuals.
import json, os, re, collections, ezdxf
from shapely.geometry import Polygon, Point
DS = _DATA + ""
OUT = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
ID = re.compile(r"^U?\d+\.\d+$"); SKIP = re.compile(r"^(U?\d+\.\d+|.*m²|Whg\..*|App\..*)$")
OUTDOOR = {"Balkon", "Balcon", "Balcone", "Loggia", "Terrasse", "Terrazza"}
LIFT = {"Lift", "Ascenseur", "Ascensore", "Aufzug"}
rules = {
 "outdoor only": lambda labs, hasid: hasid and not (labs & OUTDOOR),
 "outdoor+lift": lambda labs, hasid: hasid and not (labs & (OUTDOOR | LIFT)),
 "outdoor+unlabelled": lambda labs, hasid: hasid and labs and not (labs & OUTDOOR),
 "outdoor+lift+unlabelled": lambda labs, hasid: hasid and labs and not (labs & (OUTDOOR | LIFT)),
}
T = collections.Counter(); door = []
for f in sorted(set(r["path"] for r in rows if r["path"].startswith("data/swiss_dwellings/"))):
    m = ezdxf.readfile(os.path.join(DS, f[:-4] + ".dxf")).modelspace()
    rooms = [Polygon([p[:2] for p in e.get_points()]) for e in m if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "ROOM_OUTLINE" and len(e) >= 3]
    units = [Polygon([p[:2] for p in e.get_points()]) for e in m if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "UNIT_OUTLINE" and len(e) >= 3]
    tx = [(e.dxf.text.strip(), Point(e.dxf.insert[0], e.dxf.insert[1])) for e in m if e.dxftype() == "TEXT" and e.dxf.layer == "ROOM_TEXT"]
    info = []
    for p in rooms:
        inside = [s for s, pt in tx if p.contains(pt)]
        info.append((p, set(s for s in inside if not SKIP.match(s)), any(ID.match(s) for s in inside)))
    arcs = sum(1 for e in m if e.dxf.layer == "DOOR" and e.dxftype() == "ARC")
    for i, r in enumerate(rows):
        if r["path"] != f or langs[i] != "en": continue
        q, a = r["question"], r["answer"]
        if q.startswith("What is the total net floor area in m² of all numbered"):
            for name, rule in rules.items():
                T[("floor total", name)] += abs(sum(p.area for p, l, h in info if rule(l, h)) - a) <= 0.02 * a
        mm = re.match(r"What is the net floor area of apartment (\S+) in m²", q)
        if mm:
            pts = [pt for s, pt in tx if re.match(r"^(Whg\.|App\.)\s*" + re.escape(mm.group(1)) + "$", s)]
            u = [x for x in units if pts and x.contains(pts[0])]
            if not u: T[("apartment", "no unit found")] += 1; continue
            for name, rule in rules.items():
                T[("apartment", name)] += abs(sum(p.area for p, l, h in info if rule(l, h) and u[0].contains(p.representative_point())) - a) <= 0.02 * a
        if q.startswith("How many doors"): door.append(a - arcs)
for k, v in sorted(T.items()): print(v, k)
print("door answer minus DOOR arcs:", sorted(collections.Counter(door).items()))

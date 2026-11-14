import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Independent check of swiss text-layer claims (F7, F8): spatial association of label / room id / area spans.
import json, collections, os, re, math
import pymupdf
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
SW = [(i, r) for i, r in enumerate(rows) if r["path"].startswith("data/swiss_dwellings/") and langs[i] == "en"]
files = sorted(set(r["path"] for _, r in SW))
ID_RE = re.compile(r"^U?\d+\.\d+$")
AREA_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*m²$")
def spans(path):
    d = pymupdf.open(os.path.join(DS, path))
    pg = d[0]
    out = []
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                t = s["text"].strip()
                if t:
                    x0, y0, x1, y1 = s["bbox"]
                    out.append(dict(t=t, cx=(x0+x1)/2, cy=(y0+y1)/2, h=y1-y0, size=s["size"], font=s["font"], bbox=s["bbox"]))
    # also full-line text (some labels may be split across spans)
    lines = []
    for b in pg.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            t = "".join(s["text"] for s in l["spans"]).strip()
            if t: lines.append(t)
    return out, lines, pg
res = []
stats = collections.Counter()
printed_rooms = 0; numbered_rooms = 0; files_all_printed = 0
per_file = {}
for f in files:
    sp, lines, pg = spans(f)
    # title block region: exclude spans in the bottom band (legend/title) using y > 0.8*height
    H = pg.rect.height
    plan = [s for s in sp if s["cy"] < 0.79 * H]
    ids = [s for s in plan if ID_RE.match(s["t"])]
    areas = [s for s in plan if AREA_RE.match(s["t"])]
    # associate area to id: nearest area span below the id within 2.5 * id height and horizontal offset < 15pt
    room = {}
    for s in ids:
        best = None
        for a in areas:
            dy = a["cy"] - s["cy"]; dx = abs(a["cx"] - s["cx"])
            if 0 < dy < 3.0 * max(s["h"], a["h"]) and dx < 20:
                if best is None or dy < best[0]: best = (dy, a)
        lab = None
        for o in plan:
            if o is s or ID_RE.match(o["t"]) or AREA_RE.match(o["t"]): continue
            dy = s["cy"] - o["cy"]; dx = abs(o["cx"] - s["cx"])
            if 0 < dy < 3.0 * max(s["h"], o["h"]) and dx < 25:
                if lab is None or dy < lab[0]: lab = (dy, o)
        room[s["t"]] = dict(area=float(AREA_RE.match(best[1]["t"]).group(1)) if best else None, label=lab[1]["t"] if lab else None)
    numbered_rooms += len(room); printed_rooms += sum(1 for v in room.values() if v["area"] is not None)
    if room and all(v["area"] is not None for v in room.values()): files_all_printed += 1
    per_file[f] = dict(room=room, plan_texts=[s["t"] for s in plan], lines=lines)
    for i, r in [(i, r) for i, r in SW if r["path"] == f]:
        q = r["question"]; a = r["answer"]
        m = re.match(r"How many rooms labelled '(.*)' are there on this floor\?$", q)
        if m:
            L = m.group(1)
            exact = sum(1 for t in per_file[f]["plan_texts"] if t == L)
            sub = sum(1 for t in per_file[f]["plan_texts"] if L in t)
            subci = sum(1 for t in per_file[f]["plan_texts"] if L.lower() in t.lower())
            res.append(dict(i=i, fam="label_count", ans=a, exact=exact, sub=sub, subci=subci, label=L))
            continue
        if q.startswith("How many apartments"):
            n = sum(1 for t in per_file[f]["plan_texts"] if re.match(r"^(Whg\.|App\.)\s*\S+$", t))
            res.append(dict(i=i, fam="apartments", ans=a, exact=n)); continue
        m = re.match(r"What is the net floor area of room (\S+) \('(.*)'\) in m²\?$", q)
        if m:
            rid, L = m.group(1), m.group(2)
            info = room.get(rid)
            res.append(dict(i=i, fam="room_area", ans=a, found=info is not None, label_ok=(info or {}).get("label") == L, printed=(info or {}).get("area")))
            continue
        m = re.match(r"What is the total net area in m² of all rooms labelled '(.*)' on this floor\?$", q)
        if m:
            L = m.group(1)
            members = [v for v in room.values() if v["label"] == L]
            ok = all(v["area"] is not None for v in members) and members
            res.append(dict(i=i, fam="label_area_sum", ans=a, printed_all=bool(ok), est=sum(v["area"] for v in members) if ok else None, n=len(members), label=L))
            continue
        if q.startswith("What is the total net floor area in m² of all numbered indoor rooms"):
            ok = all(v["area"] is not None for v in room.values())
            outdoor = {"Balkon", "Balcon", "Balcone", "Loggia", "Terrasse", "Terrazza"}
            est = sum(v["area"] for v in room.values() if v["label"] not in outdoor) if ok else None
            res.append(dict(i=i, fam="floor_total", ans=a, printed_all=ok, est=est)); continue
        if q.startswith("What is the net floor area of apartment"):
            res.append(dict(i=i, fam="apartment_area", ans=a)); continue
        res.append(dict(i=i, fam="other:" + q[:40], ans=a))
json.dump(res, open(os.path.join(OUT, "swiss_res.json"), "w"), default=str)
json.dump({f: {k: v for k, v in d.items() if k != "lines"} for f, d in per_file.items()}, open(os.path.join(OUT, "swiss_rooms.json"), "w"), ensure_ascii=False)
C = collections.Counter(r["fam"] for r in res); print(C)
lc = [r for r in res if r["fam"] == "label_count"]
print("label count exact", sum(r["exact"] == r["ans"] for r in lc), "/", len(lc), " substring", sum(r["sub"] == r["ans"] for r in lc), " ci-substring", sum(r["subci"] == r["ans"] for r in lc))
for r in lc:
    if r["exact"] != r["ans"]: print("  MISS label", r)
ap = [r for r in res if r["fam"] == "apartments"]
print("apartments exact", sum(r["exact"] == r["ans"] for r in ap), "/", len(ap))
for r in ap:
    if r["exact"] != r["ans"]: print("  MISS apt", rows[r["i"]]["path"], r)
ra = [r for r in res if r["fam"] == "room_area"]
print("room ids found", sum(r["found"] for r in ra), "/", len(ra), " adjacent label equal", sum(r["label_ok"] for r in ra))
pr = [r for r in ra if r["printed"] is not None]
print("asked rooms with printed area", len(pr), "/", len(ra), " within 2%", sum(abs(r["printed"] - r["ans"]) <= 0.02 * r["ans"] for r in pr), " exact", sum(abs(r["printed"] - r["ans"]) < 0.005 for r in pr))
for r in pr:
    if abs(r["printed"] - r["ans"]) >= 0.005: print("  area diff", r["printed"], r["ans"], rows[r["i"]]["question"][:60])
print("numbered rooms", numbered_rooms, "printed", printed_rooms, round(100*printed_rooms/numbered_rooms, 1), "files with all printed", files_all_printed, "/", len(files))
ls = [r for r in res if r["fam"] == "label_area_sum"]
lsp = [r for r in ls if r["printed_all"]]
print("label sums testable", len(lsp), "/", len(ls), " within 2%", sum(abs(r["est"] - r["ans"]) <= 0.02 * r["ans"] for r in lsp))
ft = [r for r in res if r["fam"] == "floor_total"]
ftp = [r for r in ft if r["printed_all"]]
print("floor totals testable", len(ftp), "/", len(ft), " within 2%", sum(abs(r["est"] - r["ans"]) <= 0.02 * r["ans"] for r in ftp))
for r in ftp: print("   floor", round(r["est"], 2), r["ans"], round(r["est"] - r["ans"], 3))
for r in lsp: print("   lsum", r["label"], round(r["est"], 2), r["ans"], round(r["est"] - r["ans"], 3))

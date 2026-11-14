import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Reproduce A-801 finish-room-schedule answers and door-schedule note counts from the PDF text layer; compare to questions.jsonl.
import re, json, os
import pymupdf
DS = _DATA + ""
P = "data/opening_design/Sports_Complex/Sheets - Current Set/A-801 - Door and Finish Schedules & Wall Types.pdf"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
A = {i: r["answer"] for i, r in enumerate(rows) if r["path"] == P}
L = pymupdf.open(os.path.join(DS, P))[0].get_text("text").split("\n")
s = L.index("FINISH ROOM SCHEDULE"); seg = L[s:]
# a row starts at "<n> SF" or "Redundant","Room", followed by a 3-digit room number
starts = [k for k in range(len(seg) - 2) if (re.fullmatch(r"\d+ SF", seg[k]) and re.fullmatch(r"1\d\d", seg[k + 1])) or (seg[k] == "Redundant" and seg[k + 1] == "Room" and re.fullmatch(r"1\d\d", seg[k + 2]))]
R = []
for a, b in zip(starts, starts[1:] + [None]):
    t = seg[a:b] if b else seg[a:a + 12]
    if t[0] == "Redundant": area, t = None, t[2:]
    else: area, t = int(t[0].split()[0]), t[1:]
    R.append(dict(area=area, num=t[0], name=t[1], cells=(t[2:9] + ["?"] * 7)[:7]))
for r in R: print(r)
def by(n): return next(r for r in R if r["num"] == n)
pred = {
 5591: len(R), 5592: by("128")["area"], 5593: by("118")["area"], 5594: by("122")["area"], 5595: by("121")["area"],
 5596: sum(r["area"] for r in R if r["area"]), 5597: sum(r["area"] or 0 for r in R if r["name"] == "OFFICE"),
 5598: sum(r["area"] or 0 for r in R if r["name"] == "RESTROOM"),
 5599: sum(r["area"] for r in R if r["name"] in ("WOMEN'S LOCKER", "MEN'S LOCKER")),
 5601: sum(r["area"] for r in R if r["cells"][0] == "F4"),
 5602: sum(1 for r in R if r["cells"][1] == "B2"),
 5603: sum(1 for r in R if r["cells"][2:6] == ["W1"] * 4),
}
f0 = [r for r in R if r["cells"][0] == "F0"]; pred[5600] = f"{len(f0)} rooms, {sum(r['area'] for r in f0)} SF"
big = max((r for r in R if r["area"]), key=lambda r: r["area"]); pred[5608] = f"Room {big['num']} {big['name']} ({big['area']} SF)"
# door schedule notes (rows parsed as in v_a801.py)
s2 = L.index("KEYNOTE - DOOR SCHEDULE") if "KEYNOTE - DOOR SCHEDULE" in L else len(L)
idx = [k for k, t in enumerate(L[:s2]) if re.fullmatch(r"1[0-3]\d\.[A-Z]\d?", t)]
D = [L[a:b] for a, b in zip(idx, idx[1:] + [s2])]
def notes(r):  # notes are the tokens after the 2-digit hardware group
    k = next((j for j in range(len(r) - 1, 0, -1) if re.fullmatch(r"\d\d", r[j])), None)
    return [x.strip() for t in r[k + 1:] for x in t.split(",")] if k else []
for i, n in [(5578, "A"), (5579, "B"), (5580, "C")]: pred[i] = sum(n in notes(r) for r in D)
ok = 0
for i in sorted(pred):
    g = str(pred[i]).replace(" ", "").lower() == str(A[i]).replace(" ", "").lower()
    ok += g; print("OK " if g else "BAD", i, repr(pred[i]), "| truth", repr(A[i]))
print("finish+notes reproduced", ok, "/", len(pred))

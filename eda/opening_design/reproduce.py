"""Reproduce the 64 opening_design answers from the PDF text layer + ruled-line geometry only.
Tables are auto-detected (tables_auto.find_tables), picked by title, then each question is answered by a small
explicit query over the extracted rows. Every answer keeps the cell boxes it came from (evidence).
Usage: python -I reproduce.py <dataset_dir> <work_dir> [alternate A-801 file to answer from, e.g. an archived revision]"""
import sys, os, re, json
import pymupdf
import pandas as pd

W = sys.argv[2]
sys.path.insert(0, W)
import tables_auto  # noqa: E402

D = sys.argv[1]
OD = os.path.join(D, "data", "opening_design")
A801 = "Sports_Complex/Sheets - Current Set/A-801 - Door and Finish Schedules & Wall Types.pdf"
ALT801 = sys.argv[3] if len(sys.argv) > 3 else None  # answer the A-801 questions from this file instead
A701 = "Sports_Complex/Sheets - Current Set/A-701 - Restrooms.pdf"
A700 = "CTR/Most Current Set/Full size sheets/A700 - SCHEDULES.pdf"


def norm(s):
    """Normalize feet-inch spacing and case: 5' - 10 3/8" -> 5'-10 3/8"."""
    s = s.replace("’", "'").replace("''", '"')
    s = re.sub(r"'\s*-\s*", "'-", s)
    return re.sub(r"\s+", " ", s).strip().upper()


def load(rel):
    doc = pymupdf.open(os.path.join(OD, rel))
    page = doc[0]
    return page, tables_auto.find_tables(page)


def table(tables, title_re, ncols=None):
    for t in tables:
        if re.fullmatch(title_re, t["title"], re.I) and (ncols is None or len(t["rows"][0]) == ncols):
            return t
    raise KeyError(title_re)


def frame(t, names):
    """Data rows = rows after the header; header ends at the first row with a digit in its first two cells."""
    rows, rects = t["rows"], t["rects"]
    start = next(i for i, r in enumerate(rows) if i > 0 and any(re.search(r"\d", c) for c in r[:2]))
    body = [r for r in rows[start:]]
    df = pd.DataFrame(body, columns=names)
    df["_bbox"] = [tuple(round(v, 1) for v in (rr[0] | rr[-1])) for rr in rects[start:]]
    return df


def area(s):
    m = re.match(r"\s*([\d,]+)\s*SF", s)
    return float(m.group(1).replace(",", "")) if m else None


# ---------------- A-801 ----------------
p801, t801 = load(ALT801 or A801)
DS = frame(table(t801, r"Door Schedule"), ["door", "room_name", "room_no", "width", "height", "door_type", "door_matl",
                                           "frame_matl", "frame_type", "hw_group", "notes"])
FR = frame(table(t801, r"FINISH ROOM SCHEDULE"), ["area", "room_no", "room_name", "floor", "base", "wall_n", "wall_s",
                                                  "wall_e", "wall_w", "ceiling", "comments"])
FK = frame(table(t801, r"FINISH KEY"), ["key", "desc"])
FK = dict(zip(FK.key, FK.desc))
# door-type legend: text block right under each 'DOOR TYPE xx' label
m801 = p801.rotation_matrix
blocks = [(pymupdf.Rect(b[:4]) * m801, b[4].strip()) for b in p801.get_text("blocks")]
for r, _ in blocks:
    r.normalize()
DT = {}
for r, txt in blocks:
    mt = re.fullmatch(r"DOOR TYPE (\w+)", txt)
    if mt:
        below = sorted([(r2.y0, t2) for r2, t2 in blocks if abs(r2.x0 - r.x0) < 3 and 0 < r2.y0 - r.y0 < 50],
                       key=lambda x: x[0])
        DT[mt.group(1)] = " ".join(t2 for _, t2 in below)
DS["notes_set"] = DS.notes.apply(lambda s: {x.strip() for x in s.split(",") if x.strip()})
FR["area_sf"] = FR.area.apply(area)
row = lambda df, col, val: df[df[col] == val].iloc[0]  # noqa: E731

A = {}  # question index -> computed answer
q = pd.read_json(os.path.join(D, "questions.jsonl"), lines=True)
q = q[q.path.str.startswith("data/opening_design/")].reset_index(drop=True)


def ans801(text):
    t = text
    if "how many doors (door numbers) are listed" in t: return len(DS)
    m = re.search(r"are door type (\w+) ", t)
    if m: return int((DS.door_type == m.group(1)).sum())
    if "(material WD-1)" in t: return int((DS.door_matl == "WD-1").sum())
    if "(STL-1)" in t: return int((DS.frame_matl == "STL-1").sum())
    if "(AL-1 or AL-2)" in t: return int(DS.frame_matl.isin(["AL-1", "AL-2"]).sum())
    m = re.search(r"carry note (\w) ", t)
    if m: return int(DS.notes_set.apply(lambda s: m.group(1) in s).sum())
    if "are 3'-0\" wide" in t: return int((DS.width.map(norm) == norm("3' - 0\"")).sum())
    if "are 7'-0\" high" in t: return int((DS.height.map(norm) == norm("7' - 0\"")).sum())
    m = re.search(r"list for room (\d+)", t)
    if m: return int((DS.room_no == m.group(1)).sum())
    if "width of door 121.A" in t: return row(DS, "door", "121.A").width
    if "door type is door 121.A" in t:
        ty = row(DS, "door", "121.A").door_type
        return f"{ty} ({DT.get(ty, '?')})"
    if "width and height of door 128.B" in t:
        r = row(DS, "door", "128.B"); return f"{r.width} wide x {r.height} high"
    if "hardware group" in t: return row(DS, "door", "107.A").hw_group
    if "door material is specified for door 115.A" in t: return row(DS, "door", "115.A").door_matl
    if "four doors of type B2 that serve the Fitness Center" in t:
        s = DS[(DS.room_no == "118") & (DS.door_type == "B2")]
        return " / ".join(sorted(set(s.height))) + f" [n={len(s)}]"
    if "how many rooms are listed in the finish room schedule" in t: return len(FR)
    m = re.search(r"area of room (\d+) \(", t)
    if m and "what is the area" in t: return row(FR, "room_no", m.group(1)).area_sf
    if "total area of all rooms that have an area" in t: return FR.area_sf.sum()
    m = re.search(r"total area of the rooms named (\w+)", t)
    if m: return FR[FR.room_name == m.group(1)].area_sf.sum()
    if "women's and men's locker" in t: return FR[FR.room_name.str.contains("LOCKER")].area_sf.sum()
    if "floor finish F0" in t:
        s = FR[FR.floor == "F0"]; return f"{len(s)} rooms, {s.area_sf.sum():.0f} SF"
    if "floor finish F4" in t: return FR[FR.floor == "F4"].area_sf.sum()
    if "ceramic tile base (B2)" in t: return int((FR.base == "B2").sum())
    if "all four walls finished with W1" in t:
        return int(((FR.wall_n == "W1") & (FR.wall_s == "W1") & (FR.wall_e == "W1") & (FR.wall_w == "W1")).sum())
    if "floor finish of room 113" in t:
        f = row(FR, "room_no", "113").floor; return f"{f} - {FK.get(f)}"
    if "floor finishes are scheduled for the Fieldhouse" in t:
        f = row(FR, "room_no", "128").floor
        return f"{f} - " + " and ".join(FK.get(k.strip(), "?") for k in f.split("&"))
    if "ceiling finish of the Fieldhouse" in t:
        f = row(FR, "room_no", "128").ceiling; return f"{f} - {FK.get(f)}"
    if "north wall finish of the Fitness Center" in t:
        f = row(FR, "room_no", "118").wall_n; return f"{f} - {FK.get(f)}"
    if "largest area" in t:
        r = FR.loc[FR.area_sf.idxmax()]; return f"Room {r.room_no} {r.room_name} ({r.area_sf:.0f} SF)"
    return None


# ---------------- A700 ----------------
p700, t700 = load(A700)
TY = frame(table(t700, r"DOOR SCHEDULE - TYPE"), ["count", "mark", "type", "width", "height", "fire", "door_type",
                                                 "door_matl", "frame_type", "frame_matl", "comments", "hw"])
WS = frame(table(t700, r"WINDOW SCHEDULE - SIMPLIFIED"), ["mark", "type", "count", "width", "height"])
TY["n"] = TY["count"].astype(int)
WS["n"] = WS["count"].astype(int)


def ans700(text):
    t = text
    m = re.search(r"\(types? (U\d+)\) are scheduled", t)
    if m: return int(TY[TY.mark == m.group(1)].n.sum())
    if "privacy swing doors (type U02)" in t: return int(TY[TY.mark == "U02"].n.sum())
    if "Marvin Essential sliding patio doors are scheduled in total" in t:
        return int(TY[TY.type.str.contains("MARVIN ESSENTIAL")].n.sum())
    if "Marvin Essential sliding patio doors are scheduled on the 3rd floor" in t:
        return int(TY[TY.type.str.contains("MARVIN ESSENTIAL") & TY.type.str.contains("3RD FLOOR")].n.sum())
    if "Vistagrande" in t:
        return int(TY[TY.type.str.contains("VISTAGRANDE") & TY.type.str.contains("1ST FLOOR")].n.sum())
    if "how many items in total" in t: return int(TY.n.sum())
    if "description starts with 'SWING'" in t: return int(TY[TY.type.str.startswith("SWING")].n.sum())
    if "(types U06 and U44)" in t: return int(TY[TY.mark.isin(["U06", "U44"])].n.sum())
    if "fire rating" in t: return row(TY, "mark", "U01").fire
    if "frame material" in t: return row(TY, "mark", "U01").frame_matl
    if "windows (window assemblies) are listed" in t: return int(WS.n.sum())
    m = re.search(r"windows of type (\w\w) ", t)
    if m: return int(WS[WS.mark == m.group(1)].n.sum())
    if "2-wide window assemblies" in t: return int(WS[WS.type.str.startswith("2-WIDE")].n.sum())
    if "consists of N ESDH3066" in t:
        return int(sum(int(re.match(r"(\d)-WIDE", ty).group(1)) * n for ty, n in zip(WS.type, WS.n)))
    if "width and height of a window unit" in t:
        return " / ".join(sorted(set(WS.width + " wide x " + WS.height + " high")))
    return None


def check(qr, got):
    gt = qr.answer
    if got is None:
        return "not answerable from text layer", False
    if qr.type == "count":
        return "exact", int(got) == int(gt)
    if qr.type == "area":
        return "2%", abs(float(got) - float(gt)) <= 0.02 * abs(float(gt))
    # text: every number/code token of the ground truth must appear in the computed answer (after normalization)
    toks = re.findall(r"[A-Z]+\d+|\d+(?:\s\d+/\d+)?(?:'-\d+(?:\s\d+/\d+)?\")?|\d+'-\d+\"", norm(str(gt)))
    g = norm(str(got))
    ok = all(tk in g for tk in toks) if toks else norm(str(gt)) in g
    return "text tokens " + ",".join(toks), ok


out = []
for i, qr in q.iterrows():
    if qr.path.endswith(A801):
        got = ans801(qr.question)
    elif qr.path.endswith(A700):
        got = ans700(qr.question)
    else:
        got = None  # A-701 fixture counts: symbols only, no text labels in plans 6A/6B
    rule, ok = check(qr, got)
    out.append(dict(i=i, sheet=os.path.basename(qr.path)[:5], type=qr.type, question=qr.question, answer=qr.answer,
                    computed=got, rule=rule, ok=ok))
res = pd.DataFrame(out)
res.to_csv(os.path.join(W, "reproduce_results_alt801.csv" if ALT801 else "reproduce_results.csv"), index=False)
for name, df in [] if ALT801 else [("A801_door_schedule", DS), ("A801_finish_room_schedule", FR), ("A700_door_type_schedule", TY),
                 ("A700_window_schedule", WS)]:
    df.drop(columns=[c for c in df.columns if c in ("notes_set",)]).to_csv(os.path.join(W, f"table_{name}.csv"), index=False)
if not ALT801:
    json.dump({"finish_key": FK, "door_type_legend": DT}, open(os.path.join(W, "A801_legends.json"), "w"), indent=1)

pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 95)
print(res.groupby(["sheet", "type"]).ok.agg(["sum", "count"]))
print("TOTAL", int(res.ok.sum()), "/", len(res))
print(res[["i", "sheet", "type", "answer", "computed", "ok"]].to_string())

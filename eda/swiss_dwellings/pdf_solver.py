"""PDF-only solver for swiss_dwellings: uses only the PDF text layer and vector paths (no DXF, no PNG).

Style conventions were learned by registering DXF entities onto PDF paths (register.py):
  room polygon   fs  stroke 0.541 grey, w 0.369, fill = category (1.0 room, 0.894 outdoor, 0.953 common, 0.812 shaft)
  unit outline   s   stroke (0.69,0.227,0.18) red dash-dot, w 1.276
  door frame     s   stroke 0.267 grey, w 0.369, 'qu' items       (one per door, duplicates kept)
  window/fixture fs  stroke black, fill white, w 0.51            (told apart by their contents)
  window lines   s   black w 0.369 'l' (2 per window); stair treads use the same style
  fixture parts  s   black w 0.51: ellipse = 47 segments, bathtub inner = 68, shower inner = 4, circles = 'c'
"""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import sys, os, re, collections
import pymupdf
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union

DS = _DATA + "/data/swiss_dwellings"
NUM = re.compile(r"[A-Z]?\d*\.\d+")
AREA = re.compile(r"(\d+\.\d+) m²")
TAG = re.compile(r"^(App\.|Whg\.|Appart\.|Gewerbe|Commerce|Commercio|Commercial|Unità|Unité)\s+\S{1,3}$")
RES_TAG = re.compile(r"^(App\.|Whg\.|Appart\.)\s")
RGB = lambda c: tuple(round(v, 3) for v in c) if c else None
FILL_CAT = {(1.0, 1.0, 1.0): "room", (0.894, 0.894, 0.894): "outdoor", (0.953, 0.953, 0.953): "common", (0.812, 0.812, 0.812): "shaft"}


def pts_of(d):
    out = []
    for it in d["items"]:
        if it[0] == "l": seq = [it[1], it[2]]
        elif it[0] == "c": seq = [it[1], it[4]]
        elif it[0] == "re": r = it[1]; seq = [r.tl, r.tr, r.br, r.bl, r.tl]
        elif it[0] == "qu": q = it[1]; seq = [q.ul, q.ur, q.lr, q.ll, q.ul]
        else: seq = []
        for p in seq:
            if not out or abs(out[-1][0] - p.x) > 1e-6 or abs(out[-1][1] - p.y) > 1e-6:
                out.append((p.x, p.y))
    return out


def rings_of(d):
    """Split a path into closed rings: a new ring starts when an item does not continue from the previous end."""
    rings, cur = [], []
    for it in d["items"]:
        if it[0] in ("re", "qu"):
            if cur: rings.append(cur); cur = []
            r = it[1]
            seq = [r.tl, r.tr, r.br, r.bl] if it[0] == "re" else [r.ul, r.ur, r.lr, r.ll]
            rings.append([(p.x, p.y) for p in seq]); continue
        a, b = (it[1], it[2]) if it[0] == "l" else (it[1], it[4])
        if cur and (abs(cur[-1][0] - a.x) > 1e-3 or abs(cur[-1][1] - a.y) > 1e-3):
            rings.append(cur); cur = []
        if not cur: cur.append((a.x, a.y))
        cur.append((b.x, b.y))
    if cur: rings.append(cur)
    return [r for r in rings if len(r) >= 3]


def poly_of(d):
    rings = sorted((Polygon(r).buffer(0) for r in rings_of(d)), key=lambda g: -g.area)
    if not rings: return None
    outer = rings[0]
    holes = [g for g in rings[1:] if outer.contains(g.representative_point())]
    return outer.difference(unary_union(holes)) if holes else outer


def load(name):
    page = pymupdf.open(f"{DS}/{name}.pdf")[0]
    spans = [sp for b in page.get_text("dict")["blocks"] for l in b.get("lines", []) for sp in l["spans"]]
    # drawing area ends above the legend heading (bottom band holds legend, scale bar, title block)
    legend_y = min((s["bbox"][1] for s in spans if s["text"] in ("Legende", "Légende", "Legenda", "Legend")), default=page.rect.height)
    ymax = legend_y - 8
    scale = None
    for s in spans:
        m = re.fullmatch(r"1:(\d+) \(A\d\)", s["text"])
        if m: scale = int(m.group(1)) * 0.0254 / 72.0  # metres per PDF point
    k2 = scale * scale
    spans = [s for s in spans if s["bbox"][3] < ymax]
    ctr = lambda s: ((s["bbox"][0] + s["bbox"][2]) / 2, (s["bbox"][1] + s["bbox"][3]) / 2)

    rooms_poly, units, door_frames, wf_frames, thin_lines, parts = [], [], 0, [], [], []
    for d in page.get_drawings():
        if d["rect"].y1 > ymax: continue
        col, fill, w = RGB(d.get("color")), RGB(d.get("fill")), round(d["width"], 3) if d.get("width") else None
        kinds = "".join(it[0] for it in d["items"])
        ktypes = {it[0] for it in d["items"]}
        if d["type"] == "fs" and col == (0.541, 0.541, 0.541) and fill in FILL_CAT:
            g = poly_of(d)
            if g is not None and not g.is_empty:
                rooms_poly.append(dict(poly=g, cat=FILL_CAT[fill]))
        elif d["type"] == "s" and col == (0.69, 0.227, 0.18) and w == 1.276:
            units.append(dict(poly=Polygon(pts_of(d)).buffer(0), tag=None))
        elif d["type"] == "s" and col == (0.267, 0.267, 0.267) and "qu" in kinds:
            door_frames += 1
        elif d["type"] == "fs" and col == (0.0, 0.0, 0.0) and fill == (1.0, 1.0, 1.0) and w == 0.51:
            p = pts_of(d)
            if len(p) >= 4: wf_frames.append(dict(poly=Polygon(p).buffer(0), pts=p))
            else: parts.append(dict(kind="seg", n=1, geom=LineString(p)))  # rare: fixture X lines rendered filled
        elif d["type"] == "s" and col == (0.0, 0.0, 0.0) and w == 0.369 and ktypes == {"l"}:
            thin_lines.append(LineString(pts_of(d)))
        elif d["type"] == "s" and col == (0.0, 0.0, 0.0) and w == 0.51:
            if ktypes == {"c"}:
                g = Polygon(pts_of(d)).buffer(0) if len(pts_of(d)) >= 3 else LineString(pts_of(d))
                parts.append(dict(kind="circle", n=len(kinds), geom=g, r=(d["rect"].width / 2) * scale))
            elif ktypes == {"l"}:
                parts.append(dict(kind="seg", n=len(kinds), geom=LineString(pts_of(d))))
            elif ktypes <= {"qu", "re"}:  # shower inner square is emitted as a quad
                parts.append(dict(kind="seg", n=4, geom=LineString(pts_of(d))))

    # rooms from text stacks
    nums = [s for s in spans if "Bold" in s["font"] and NUM.fullmatch(s["text"])]
    rooms = []
    for s in nums:
        cx, cy = ctr(s); h = s["size"]
        col_ = [t for t in spans if t is not s and abs(ctr(t)[0] - cx) < 0.6 and abs(ctr(t)[1] - cy) < 2.3 * h]
        above = sorted([t for t in col_ if ctr(t)[1] < cy], key=lambda t: -ctr(t)[1])
        below = [t for t in col_ if ctr(t)[1] > cy]
        label = above[0]["text"] if above and not TAG.fullmatch(above[0]["text"]) and "Bold" not in above[0]["font"] else None
        printed = next((float(AREA.fullmatch(t["text"]).group(1)) for t in below if AREA.fullmatch(t["text"])), None)
        pt = Point(cx, cy)
        cont = [r for r in rooms_poly if r["poly"].contains(pt)]
        rp = min(cont, key=lambda r: r["poly"].area) if cont else None
        net = cat = None
        if rp is not None:
            inner = [o["poly"] for o in rooms_poly if o is not rp and o["poly"].area < rp["poly"].area and rp["poly"].intersection(o["poly"]).area > 0.5 * o["poly"].area]
            net = (rp["poly"].difference(unary_union(inner)).area if inner else rp["poly"].area) * k2
            cat = rp["cat"]
        rooms.append(dict(num=s["text"], label=label, printed=printed, net=net, cat=cat, poly=rp["poly"] if rp else None, bbox=s["bbox"]))
    for s in spans:
        if "Bold" in s["font"] and TAG.fullmatch(s["text"]):
            pt = Point(*ctr(s))
            cont = [u for u in units if u["poly"].contains(pt)]
            if cont: min(cont, key=lambda u: u["poly"].area)["tag"] = s["text"]
    for r in rooms:
        r["unit"] = None
        if r["poly"] is not None:
            cands = [u for u in units if u["poly"].intersection(r["poly"]).area > 0.5 * r["poly"].area]
            if cands: r["unit"] = min(cands, key=lambda u: u["poly"].area)["tag"]

    # windows vs fixtures: classify each white frame by what lies inside it (deduplicated geometry)
    fix = collections.Counter(); windows = 0
    for fr in wf_frames:
        P_ = fr["poly"].buffer(0.3)
        lines_in = {tuple(round(c, 2) for xy in l.coords for c in xy) for l in thin_lines if P_.contains(l)}
        inside = [q for q in parts if P_.contains(q["geom"])]
        uniq = {(q["kind"], q["n"], tuple(round(c, 2) for c in q["geom"].bounds)): q for q in inside}.values()
        segs = collections.Counter(q["n"] for q in uniq if q["kind"] == "seg")
        circ = [q for q in uniq if q["kind"] == "circle"]
        if segs.get(68): fix["bathtub"] += 1
        elif segs.get(47) and any(n == 1 for n in segs): fix["wc"] += 1
        elif segs.get(47) and circ: fix["washbasin"] += 1
        elif segs.get(4) and circ: fix["shower"] += 1
        elif len(circ) >= 4: fix["kitchen"] += 1
        elif not inside and len(lines_in) == 2:  # window: two parallel glazing lines; lift/shaft symbol: two crossing lines
            l1, l2 = [LineString([(t[0], t[1]), (t[-2], t[-1])]) for t in lines_in]
            mrr = fr["poly"].minimum_rotated_rectangle.exterior.coords
            long_side = max(LineString([mrr[i], mrr[i + 1]]).length for i in range(4))
            if l1.intersects(l2): fix["x_box"] += 1
            elif min(l1.length, l2.length) < 0.8 * long_side: fix["stair_bit"] += 1  # treads run across the short side
            else: windows += 1
        else:
            fix["other"] += 1
    return dict(rooms=rooms, units=units, doors=door_frames, windows=windows, fix=fix, scale=scale)


OUTDOOR = {"Balkon", "Balcon", "Balcone", "Loggia", "Terrasse", "Terrazza", "Terrazzo", "Veranda", "Sitzplatz"}


def answer(fam, q, m, use_fill=True):
    rooms = m["rooms"]
    is_out = lambda r: (r["cat"] == "outdoor") if use_fill else (r["label"] in OUTDOOR)
    is_shaft = lambda r: (r["cat"] == "shaft") if use_fill else False
    if fam == "count_label":
        lab = re.search(r"labelled '(.*)' are there", q).group(1)
        return sum(1 for r in rooms if r["label"] == lab)
    if fam == "count_apartments":
        return sum(1 for u in m["units"] if u["tag"] and RES_TAG.match(u["tag"]))
    if fam == "count_doors": return m["doors"]
    if fam == "count_windows": return m["windows"]
    if fam == "count_wc": return m["fix"].get("wc", 0)
    if fam == "count_washbasins": return m["fix"].get("washbasin", 0)
    if fam == "count_bathtubs": return m["fix"].get("bathtub", 0)
    if fam == "count_showers": return m["fix"].get("shower", 0)
    if fam == "area_room":
        num = re.search(r"room ([A-Z]?\d*\.\d+) \(", q).group(1)
        r = [r for r in rooms if r["num"] == num]
        if not r or r[0]["net"] is None: return None
        return r[0]["printed"] if r[0]["printed"] is not None else round(r[0]["net"], 2)
    if fam == "area_label_total":
        lab = re.search(r"labelled '(.*)' on this floor", q).group(1)
        return round(sum(r["net"] for r in rooms if r["label"] == lab and r["net"]), 2)
    if fam == "area_apartment":
        a = re.search(r"apartment ([A-Z]+) in", q).group(1)
        rr = [r for r in rooms if r["unit"] and RES_TAG.match(r["unit"]) and r["unit"].split()[-1] == a and not is_out(r)]
        return round(sum(r["net"] for r in rr if r["net"]), 2)
    if fam == "area_total_indoor":
        rr = [r for r in rooms if not is_out(r) and not is_shaft(r)]
        return round(sum(r["net"] for r in rr if r["net"]), 2)


def correct(fam, pred, gold):
    if pred is None: return False
    if fam.startswith("count"): return int(pred) == int(gold)
    return abs(pred - gold) <= 0.02 * abs(gold)


if __name__ == "__main__":
    import pandas as pd
    WD = os.path.dirname(os.path.abspath(__file__))
    en = pd.read_csv(f"{WD}/questions_en_families.csv")
    cache = {}
    for variant in ["fill", "label_only"]:
        preds = []
        for _, row in en.iterrows():
            name = os.path.basename(row.path)[:-4]
            if name not in cache: cache[name] = load(name)
            preds.append(answer(row.family, row.question, cache[name], use_fill=(variant == "fill")))
        en[f"pred_{variant}"] = preds
        en[f"ok_{variant}"] = [correct(f, p, g) for f, p, g in zip(en.family, preds, en.answer)]
    print(en.groupby("family")[["ok_fill", "ok_label_only"]].agg(["sum", "count"]).to_string())
    print("TOTAL fill:", en.ok_fill.sum(), "/", len(en), " label_only:", en.ok_label_only.sum())
    en.to_csv(f"{WD}/eval_pdf.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 80)
    print(en[~en.ok_fill][["path", "family", "question", "answer", "pred_fill"]].assign(path=lambda d: d.path.str[21:-4]).to_string())

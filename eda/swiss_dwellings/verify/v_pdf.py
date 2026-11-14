import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Independent PDF-only floor model for swiss_dwellings (verification). No DXF, no PNG.
import pymupdf, re, collections, math
from shapely.geometry import Polygon, Point, LineString, MultiPoint
from shapely.ops import unary_union

D = _DATA + "/data/swiss_dwellings"
NUM = re.compile(r"^U?\d+\.\d+$")
AREA = re.compile(r"^(\d+(?:\.\d+)?)\s?m²$")
R3 = lambda c: tuple(round(v, 3) for v in c) if c else None
GREY_ROOM = (0.541, 0.541, 0.541)

def subpaths(d):
    """Split a drawing's items into point sequences, breaking where an item does not start at the previous end."""
    out, cur, last = [], [], None
    for it in d["items"]:
        if it[0] == "re":
            r = it[1]; out.append([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)]); last = None; continue
        if it[0] == "qu":
            q = it[1]; out.append([(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)]); last = None; continue
        pts = [it[1], it[2]] if it[0] == "l" else [it[1], it[2], it[3], it[4]]
        a = (pts[0].x, pts[0].y)
        if last is None or math.dist(a, last) > 1e-3:
            if cur: out.append(cur)
            cur = [a]
        if it[0] == "l":
            cur.append((pts[1].x, pts[1].y))
        else:  # cubic bezier: sample
            p0, p1, p2, p3 = [(p.x, p.y) for p in pts]
            for t in (0.25, 0.5, 0.75, 1.0):
                mt = 1 - t
                cur.append((mt**3*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t**3*p3[0],
                            mt**3*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t**3*p3[1]))
        last = cur[-1]
    if cur: out.append(cur)
    return out

def poly_with_holes(d):
    rings = [Polygon(s).buffer(0) for s in subpaths(d) if len(s) >= 3]
    rings = [g for g in rings if not g.is_empty]
    if not rings: return None
    rings.sort(key=lambda g: -g.area)
    g = rings[0]
    for h in rings[1:]:
        if g.contains(h.representative_point()): g = g.difference(h)
        else: g = g.union(h)
    return g

def load(stem):
    doc = pymupdf.open(f"{D}/{stem}.pdf")
    pg = doc[0]
    spans = [dict(t=sp["text"].strip(), font=sp["font"], size=sp["size"], bbox=sp["bbox"],
                  cx=(sp["bbox"][0]+sp["bbox"][2])/2, cy=(sp["bbox"][1]+sp["bbox"][3])/2)
             for b in pg.get_text("dict")["blocks"] for l in b.get("lines", []) for sp in l["spans"] if sp["text"].strip()]
    leg = [s for s in spans if s["t"] in ("Legende", "Légende", "Legenda", "Legend")]
    ycut = min(s["bbox"][1] for s in leg) - 5 if leg else pg.rect.height
    scale_txt = [re.match(r"^1:(\d+) \(A\d\)$", s["t"]) for s in spans]
    scale_txt = [int(m.group(1)) for m in scale_txt if m]
    scale = scale_txt[0] if scale_txt else None
    mpp = scale * 0.0254 / 72 if scale else None  # metres per PDF point
    plan = [s for s in spans if s["bbox"][3] < ycut]
    drs = [d for d in pg.get_drawings() if d["rect"].y0 < ycut]
    # room-like polygons: grey stroke 0.541, filled
    polys = []
    for d in drs:
        if d["type"] == "fs" and R3(d.get("color")) == GREY_ROOM:
            g = poly_with_holes(d)
            if g is not None and g.area > 0: polys.append(dict(g=g, fill=R3(d.get("fill"))[0]))
    # rooms from bold numbers
    rooms = []
    for s in plan:
        if not ("Bold" in s["font"] and NUM.match(s["t"])): continue
        col = [u for u in plan if u is not s and abs(u["cx"] - s["cx"]) < 1.0]
        above = sorted([u for u in col if 0 < s["cy"] - u["cy"] < 2.0 * s["size"]], key=lambda u: s["cy"] - u["cy"])
        below = sorted([u for u in col if 0 < u["cy"] - s["cy"] < 2.0 * s["size"]], key=lambda u: u["cy"] - s["cy"])
        lab = above[0]["t"] if above and "Bold" not in above[0]["font"] else None
        pr = AREA.match(below[0]["t"]) if below else None
        pt = Point(s["cx"], s["cy"])
        cont = [p for p in polys if p["g"].contains(pt)]
        p = min(cont, key=lambda p: p["g"].area) if cont else None
        rooms.append(dict(num=s["t"], label=lab, printed=float(pr.group(1)) if pr else None, pt=pt, poly=p,
                          size=s["size"], bbox=s["bbox"]))
    # net area = own polygon (compound holes already removed) minus polygons nested inside it
    for r in rooms:
        p = r["poly"]
        if p is None: r["raw"] = r["net"] = None; r["fill"] = None; continue
        inner = [q["g"] for q in polys if q is not p and q["g"].area < p["g"].area and p["g"].buffer(0.05).contains(q["g"])]
        r["fill"] = p["fill"]
        r["raw"] = p["g"].area * mpp**2
        r["net"] = (p["g"].difference(unary_union(inner)).area if inner else p["g"].area) * mpp**2
        r["n_inner"] = len(inner)
    # units: red dash-dot outlines, tags = bold non-number spans
    units = []
    for d in drs:
        c = R3(d.get("color"))
        if d["type"] == "s" and c and abs(c[0]-0.69) < 0.01 and abs(c[1]-0.227) < 0.01:
            pts = [q for sp in subpaths(d) for q in sp]
            g = Polygon(pts).buffer(0) if len(pts) >= 3 else None
            if g is not None and g.area > 0: units.append(dict(g=g, tags=[], w=round(d.get("width") or 0, 3)))
    tags = [s for s in plan if "Bold" in s["font"] and not NUM.match(s["t"])]
    for t in tags:
        cont = [u for u in units if u["g"].contains(Point(t["cx"], t["cy"]))]
        t["unit"] = min(cont, key=lambda u: u["g"].area) if cont else None
        if t["unit"] is not None: t["unit"]["tags"].append(t["t"])
    for r in rooms:
        if r["poly"] is None: r["unit"] = None; continue
        g = r["poly"]["g"]
        cont = [u for u in units if u["g"].buffer(0.5).contains(g.representative_point()) and u["g"].intersection(g).area > 0.5 * g.area]
        r["unit"] = min(cont, key=lambda u: u["g"].area) if cont else None
    # doors: stroke 0.267 grey quads
    doors = [d for d in drs if d["type"] == "s" and R3(d.get("color")) == (0.267, 0.267, 0.267) and any(it[0] == "qu" for it in d["items"])]
    door_keys = collections.Counter(tuple(round(v, 1) for v in d["rect"]) for d in doors)
    # white frames with black stroke (windows and fixtures)
    frames = [d for d in drs if d["type"] == "fs" and R3(d.get("color")) == (0, 0, 0) and R3(d.get("fill")) == (1, 1, 1)]
    blacks = [d for d in drs if d["type"] == "s" and R3(d.get("color")) == (0, 0, 0)]
    return dict(stem=stem, spans=spans, plan=plan, scale=scale, mpp=mpp, polys=polys, rooms=rooms, units=units, tags=tags,
                doors=doors, door_keys=door_keys, frames=frames, blacks=blacks, page=pg.rect, ycut=ycut,
                producer=doc.metadata.get("producer"))

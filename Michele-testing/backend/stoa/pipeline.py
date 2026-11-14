"""Uploaded file -> display image + `facts` (one JSON shape for every input type).

  .dxf          exact vector parse (vector_dxf), rendered to a display image. No ML.
  .pdf          page rendered at 150 dpi -> PlanNet geometry; words come from the
                PDF text layer (exact) instead of the OCR model.
  .png/.jpg     PlanNet (rooms, walls, objects) + GlyphNet (printed labels).

facts = {
  source, width, height, scale{m_per_px, method},
  rooms[{id, number, name, category, area_m2, area_source, area_geom_m2, polygon, centroid,
         unit, outdoor, shaft, confidence}],
  objects[{id, type, x, y, bbox, score, room}],
  units[{id, polygon, area_m2}], words[{text, box, conf}], summary{...}, storeys, warnings[]
}
All coordinates are display-image pixels.
"""
from __future__ import annotations

import os
import math
import re
from collections import Counter

import cv2
import numpy as np

from .vector_dxf import AREA_RE, NUMBER_RE, OUTDOOR, SHAFT_VOID, UNIT_RE, parse_dxf, poly_area

SWISS_M_PER_PX = 0.2 / (150 / 25.4)  # 1:200 sheet at 150 dpi = 0.03387 m/px
WEIGHTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "weights")

CATEGORIES = [
    ("bedroom", r"schlafzimmer|chambre|camera da letto|makuuhuone|\bmh\b|bedroom"),
    ("living", r"wohnen|sejour|soggiorno|pranzo|repas|essen|\boh\b|living"),
    ("kitchen", r"kuche|cuisine|cucina|keittio|\bk\b|\bkt\b|\brt\b|kitchen"),
    ("bathroom", r"\bbad\b|bain|bagno|\bkh\b|kph|\bph\b|pesuh|\bsh\b|bath"),
    ("wc_room", r"^wc$|toilet"),
    ("corridor", r"korridor|couloir|corridoio|\beteinen\b|\bet\b|\bkäytävä\b|hall|aula"),
    ("storage", r"reduit|ripostiglio|\bvar\b|varasto|storage|depot"),
    ("stair", r"treppenhaus|escalier|vano scala|porras|stair"),
    ("elevator", r"lift|ascen"),
    ("balcony", r"balkon|balcon|loggia|terrass|parvek|terassi"),
    ("sauna", r"sauna|\bs\b"),
    ("room", r"zimmer|piece|stanza|room|huone"),
    ("office", r"buro|office|kontor"),
]


def _ascii(s):
    import unicodedata
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()


def categorize(name):
    n = _ascii(name)
    for cat, pat in CATEGORIES:
        if re.search(pat, n):
            return cat
    return "other" if n else "shaft"


def _round_poly(p):
    return [[round(float(x), 1), round(float(y), 1)] for x, y in p]


def _area_sum(rooms):
    """A missing room measurement makes the requested total unknown."""
    values = [r.get("area_m2") for r in rooms]
    return (round(sum(values), 2) if values and all(type(v) in (int, float) and math.isfinite(v) and v >= 0
                                                 for v in values) else None)


def _printed_scale(rooms):
    pairs = [(r.get("area_label"), r.get("pixels")) for r in rooms]
    pairs = [(a, p) for a, p in pairs if type(a) in (int, float) and math.isfinite(a) and a > 0
             and type(p) in (int, float) and math.isfinite(p) and p > 50]
    if len(pairs) < 3:
        return None, "not calibrated"
    ratios = np.array([a / p for a, p in pairs])
    med = float(np.median(ratios))
    good = ratios[np.abs(ratios / med - 1) < 0.15]
    if len(good) < 3:
        return None, "not calibrated"
    return float(np.sqrt(np.median(good))), f"calibrated from {len(good)} printed room areas"


def _raster_areas(rooms, m_per_px, source):
    for room in rooms:
        room["area_px"] = round(room.pop("pixels"), 1)
        room["area_geom_m2"] = round(room["area_px"] * m_per_px ** 2, 2) if m_per_px else None
        printed = room.pop("area_label", None)
        if printed is not None:
            room["area_m2"] = printed
            room["area_source"] = "printed label (read by GlyphNet)" if source == "raster" else "printed label (PDF text)"
        elif m_per_px:
            room["area_m2"], room["area_source"] = room["area_geom_m2"], "segmented geometry x calibrated scale"
        else:
            room["area_m2"], room["area_source"] = None, "set the scale to measure"


def summarize(facts):
    c = Counter(o["type"] for o in facts["objects"])
    rooms = facts["rooms"]
    indoor = [r for r in rooms if not r["outdoor"] and not r["shaft"]]
    facts["summary"] = {
        "rooms": len(rooms), "apartments": len(facts["units"]),
        "net_area_m2": _area_sum(indoor),
        "outdoor_area_m2": _area_sum([r for r in rooms if r["outdoor"]]),
        "objects": dict(c),
        "unit_areas": {u["id"]: u["area_m2"] for u in facts["units"]},
    }
    return facts


# ----------------------------------------------------------------- DXF (exact)
def analyze_dxf(path):
    plan = parse_dxf(path)
    pts = np.concatenate([w for w in plan.walls + plan.wall_hatches] + [r["polygon"] for r in plan.rooms if r["polygon"] is not None])
    lo, hi = pts.min(0), pts.max(0)
    s = 1 / SWISS_M_PER_PX
    margin = 40
    W, H = int((hi[0] - lo[0]) * s) + 2 * margin, int((hi[1] - lo[1]) * s) + 2 * margin
    T = lambda p: np.stack([(np.asarray(p)[..., 0] - lo[0]) * s + margin, (hi[1] - np.asarray(p)[..., 1]) * s + margin], -1)
    img = np.full((H, W, 3), 255, np.uint8)
    ip = lambda p: np.round(T(p)).astype(np.int32)
    for w in plan.wall_hatches + plan.walls:
        cv2.fillPoly(img, [ip(w)], (90, 90, 90))
    for r in plan.rooms:
        if r["polygon"] is not None:
            cv2.polylines(img, [ip(r["polygon"])], True, (150, 150, 150), 1, cv2.LINE_AA)
    for w in plan.windows:
        cv2.polylines(img, [ip(w["polygon"])], True, (60, 60, 60), 1, cv2.LINE_AA)
    for d in plan.doors:
        for dd in [d] + ([d["partner"]] if d.get("double") else []):
            c = T(dd["center"]); r = dd["radius"] * s
            cv2.ellipse(img, (int(c[0]), int(c[1])), (int(r), int(r)), 0, -dd["end"], -dd["start"], (60, 60, 60), 1, cv2.LINE_AA)
    for f in plan.fixtures:
        x0, y0, x1, y1 = f["bbox"]
        q = ip(np.array([[x0, y0], [x1, y1]]))
        cv2.rectangle(img, tuple(q[0]), tuple(q[1]), (70, 70, 70), 1)
    rooms = []
    for i, r in enumerate(plan.rooms):
        poly = T(r["polygon"]) if r["polygon"] is not None else None
        area = r["area_label"] if r["area_label"] is not None else round(r["area_geom"] or 0, 2)
        rooms.append({
            "id": f"r{i}", "number": r["number"], "name": r["name"], "category": categorize(r["name"]),
            "area_m2": area, "area_source": "printed label (DXF text)" if r["area_label"] is not None else "polygon geometry",
            "area_geom_m2": round(r["area_geom"], 2) if r["area_geom"] else None,
            "area_px": round((r["area_geom"] or 0) / SWISS_M_PER_PX ** 2, 1),
            "polygon": _round_poly(poly) if poly is not None else [],
            "centroid": [round(float(v), 1) for v in (poly.mean(0) if poly is not None else T(r["text_xy"]))],
            "unit": r["unit"], "outdoor": r["outdoor"], "shaft": r["shaft"], "confidence": 1.0,
        })
    objects = []
    def add(t, c, bb):
        objects.append({"id": f"o{len(objects)}", "type": t, "x": round(float(c[0]), 1), "y": round(float(c[1]), 1),
                        "bbox": [round(float(v), 1) for v in bb], "score": 1.0})
    for d in plan.doors:
        c = np.array(d["center"]); r = d["radius"]
        if d.get("double"):
            c = (c + np.array(d["partner"]["center"])) / 2; r *= 2
        p = T(c); h = r * s / 2
        add("door", p, [p[0] - h, p[1] - h, p[0] + h, p[1] + h])
    for w in plan.windows:
        q = T(w["polygon"]); add("window", q.mean(0), [*q.min(0), *q.max(0)])
    for f in plan.fixtures:
        x0, y0, x1, y1 = f["bbox"]; q = T(np.array([[x0, y0], [x1, y1]]))
        add(f["type"], q.mean(0), [q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()])
    units = []
    for u in plan.units:
        if not u["id"]:
            continue
        rs = [r for r in rooms if r["unit"] == u["id"] and not r["outdoor"] and not r["shaft"]]
        units.append({"id": u["id"], "polygon": _round_poly(T(u["polygon"])), "area_m2": round(sum(r["area_m2"] for r in rs), 2)})
    facts = {"source": "dxf", "width": W, "height": H,
             "scale": {"m_per_px": SWISS_M_PER_PX, "method": "exact (DXF metres)"},
             "rooms": rooms, "objects": objects, "units": units, "words": [], "storeys": 1,
             "warnings": [], "title": " / ".join(t["text"] for t in plan.annotations[:1])}
    _assign_rooms(facts)
    return img, summarize(facts)


# ----------------------------------------------------------------- raster
class Models:
    _inst = None

    def __init__(self):
        import torch
        from .models import GlyphNet, PlanNet
        self.torch = torch
        torch.set_num_threads(max(1, (os.cpu_count() or 4) // 2))
        self.plan = self.glyph = None
        p = os.path.join(WEIGHTS, "plannet_swiss.pt")
        if os.path.exists(p):
            ck = torch.load(p, map_location="cpu", weights_only=False)  # our own checkpoints only
            self.seg_ch, self.obj_cls = ck["seg_channels"], ck["obj_classes"]
            self.plan = PlanNet(len(self.seg_ch), len(self.obj_cls))
            self.plan.load_state_dict(ck["model"]); self.plan.eval()
            self.plan_scale = ck.get("input_scale") or 1.0
            self.plan_eval = ck.get("eval")
        self.cc = None
        c = os.path.join(WEIGHTS, "plannet_cc.pt")
        if os.path.exists(c):
            ck = torch.load(c, map_location="cpu", weights_only=False)  # our own checkpoints only
            self.cc_seg, self.cc_obj = ck["seg_channels"], ck["obj_classes"]
            self.cc = PlanNet(len(self.cc_seg), len(self.cc_obj))
            self.cc.load_state_dict(ck["model"]); self.cc.eval()
            self.cc_wall_px = ck.get("wall_px", 13.0)
            self.cc_eval = ck.get("eval")
        g = os.path.join(WEIGHTS, "glyphnet_swiss.pt")
        if os.path.exists(g):
            ck = torch.load(g, map_location="cpu", weights_only=False)  # our own checkpoints only
            self.glyph = GlyphNet(); self.glyph.load_state_dict(ck["model"]); self.glyph.eval()

    @classmethod
    def get(cls):
        if cls._inst is None:
            cls._inst = Models()
        return cls._inst


def _read_words_ocr(models, gray, text_mask):
    """Group text pixels into word boxes, read each with GlyphNet."""
    from .models import ctc_decode
    from train.train_glyph import crop_word, to_tensor
    m = (text_mask > 0.5).astype(np.uint8)
    # merge characters of one word horizontally, keep lines apart
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    boxes = [(x, y, x + w, y + h) for x, y, w, h, a in stats[1:] if a > 15 and h >= 4 and w >= 3]
    words = []
    for i in range(0, len(boxes), 64):
        chunk = boxes[i:i + 64]
        crops = [crop_word(gray, b) for b in chunk]
        keep = [(b, c) for b, c in zip(chunk, crops) if c is not None]
        if not keep:
            continue
        with models.torch.no_grad():
            pred = ctc_decode(models.glyph(to_tensor([c for _, c in keep])))
        for (b, _), (t, conf) in zip(keep, pred):
            if t.strip():
                words.append({"text": t.strip(), "box": [float(v) for v in b], "conf": round(conf, 3)})
    return words


def _parse_label_stacks(words):
    """Find room number tokens and attach the name above and the area below, like the drawing's stacks."""
    def centre(w):
        b = w["box"]; return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, b[3] - b[1]
    nums = [w for w in words if NUMBER_RE.match(w["text"])]
    out = []
    for n in nums:
        cx, cy, h = centre(n)
        near = [w for w in words if w is not n and abs(centre(w)[0] - cx) < 6 * h and abs(centre(w)[1] - cy) < 2.6 * h]
        above = sorted([w for w in near if centre(w)[1] < cy - 0.4 * h], key=lambda w: cy - centre(w)[1])
        below = sorted([w for w in near if centre(w)[1] > cy + 0.4 * h], key=lambda w: centre(w)[1] - cy)
        # name = words on the nearest line above (may be several words), skipping unit tags
        name = None
        if above:
            ly = centre(above[0])[1]
            line = sorted([w for w in above if abs(centre(w)[1] - ly) < 0.5 * h], key=lambda w: w["box"][0])
            txt = " ".join(w["text"] for w in line)
            if not UNIT_RE.match(txt) and not AREA_RE.match(txt) and not re.match(r"^(Whg|App)\.?$", txt):
                name = txt
        area = None
        if below:
            ly = centre(below[0])[1]
            line = sorted([w for w in below if abs(centre(w)[1] - ly) < 0.5 * h], key=lambda w: w["box"][0])
            txt = " ".join(w["text"] for w in line)
            m = re.match(r"^\s*(\d+[.,]\d+)", txt)
            if m:
                area = float(m.group(1).replace(",", "."))
        out.append({"number": n["text"], "name": name, "area": area, "xy": (cx, cy), "conf": n.get("conf", 1.0)})
    tags = []
    for i, w in enumerate(words):
        t = w["text"]
        m = UNIT_RE.match(t)
        if not m and re.match(r"^(Whg|App)\.?$", t):  # tag split into two words
            nxt = [v for v in words if v is not w and abs(centre(v)[1] - centre(w)[1]) < 0.5 * centre(w)[2]
                   and 0 < v["box"][0] - w["box"][2] < 3 * centre(w)[2] and re.match(r"^[A-Z]$", v["text"])]
            if nxt:
                m = re.match(r"(.*)", nxt[0]["text"]); tags.append((nxt[0]["text"], centre(w)[:2])); continue
        if m:
            tags.append((m.group(2), centre(w)[:2]))
    return out, tags


def analyze_raster(gray, words=None, source="raster"):
    from train.train_plannet import predict_full
    from .models import heat_peaks
    models = Models.get()
    warnings = ["Room and object detections are model predictions; verify them on this drawing style."]
    if models.plan is None:
        return _empty_facts(gray, source, "The plan-reading model is not installed in this copy of the app, so only the drawing is shown.")
    H, W = gray.shape
    f = models.plan_scale
    small = gray if f == 1 else cv2.resize(gray, (int(W * f), int(H * f)), interpolation=cv2.INTER_AREA)
    seg, heat = predict_full(models.plan, small)
    seg = seg.numpy()
    if f != 1:  # back to full resolution so polygons, OCR crops and areas use the original pixels
        seg = np.stack([cv2.resize(c, (W, H), interpolation=cv2.INTER_LINEAR) for c in seg])
    ch = {n: i for i, n in enumerate(models.seg_ch)}
    if words is None:
        words = _read_words_ocr(models, gray, seg[ch["text"]]) if models.glyph is not None else []
        if models.glyph is None:
            warnings.append("Text reader weights missing; room names and printed areas unavailable.")

    # ---- rooms: room mask minus room edges and walls -> connected components
    room = (seg[ch["room"]] > 0.5) & (seg[ch["room_edge"]] < 0.5) & (seg[ch["wall"]] < 0.5)
    room = cv2.morphologyEx(room.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, cents = cv2.connectedComponentsWithStats(room, 4)
    stacks, tags = _parse_label_stacks(words)
    min_area = 0.6 / SWISS_M_PER_PX ** 2  # ignore blobs < 0.6 m2 at sheet scale
    rooms = []
    for k in range(1, n):
        if stats[k, 4] < min_area * 0.5:
            continue
        mask = (lab == k).astype(np.uint8)
        # re-grow over the removed edge band so geometry matches the net room outline
        grown = cv2.dilate(mask, np.ones((5, 5), np.uint8)) & (seg[ch["wall"]] < 0.5)
        cs, _ = cv2.findContours(grown, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)
        poly = cv2.approxPolyDP(c, 1.5, True)[:, 0, :].astype(float)
        inside = [s for s in stacks if 0 <= int(s["xy"][1]) < H and 0 <= int(s["xy"][0]) < W and lab[int(s["xy"][1]), int(s["xy"][0])] == k]
        if not inside:  # label may sit on an edge pixel: nearest stack within the grown room
            inside = [s for s in stacks if 0 <= int(s["xy"][1]) < H and 0 <= int(s["xy"][0]) < W and grown[int(s["xy"][1]), int(s["xy"][0])]]
        lbl = inside[0] if inside else None
        if lbl is None and stats[k, 4] < min_area * 2:
            continue  # small unlabeled blob: likely furniture or symbol interior, not a room
        outdoor_p = float(seg[ch["outdoor"]][lab == k].mean())
        name = lbl["name"] if lbl else None
        low = _ascii(name)
        rooms.append({
            "id": f"r{len(rooms)}", "number": lbl["number"] if lbl else None, "name": name,
            "category": categorize(name) if name else ("balcony" if outdoor_p > 0.5 else "unlabelled"),
            "area_label": lbl["area"] if lbl else None, "pixels": float(cv2.contourArea(poly.astype(np.float32))),
            "polygon": _round_poly(poly), "centroid": [round(float(v), 1) for v in cents[k]],
            "unit": None, "outdoor": outdoor_p > 0.5 or low in OUTDOOR,
            "shaft": bool(lbl) and not name and stats[k, 4] < 3.5 / SWISS_M_PER_PX ** 2 or low in SHAFT_VOID,
            "confidence": round(float(seg[ch["room"]][lab == k].mean()), 3),
        })

    # ---- scale: robust ratio between printed areas and pixel areas (self-calibration)
    m_per_px, method = _printed_scale(rooms)
    if m_per_px is None:
        warnings.append("Scale not calibrated from printed areas. Set scale using a known dimension before measuring geometry.")
    _raster_areas(rooms, m_per_px, source)

    # ---- objects from heatmap peaks
    peaks = heat_peaks(heat)
    objects = []
    for c, plist in enumerate(peaks):
        t = models.obj_cls[c]
        for x, y, sc in plist:
            x, y = int(round(x / f)), int(round(y / f))
            h = 12 if t in ("wc", "washbasin", "shower") else 18 if t in ("door", "bathtub", "stove") else 14
            objects.append({"id": f"o{len(objects)}", "type": t, "x": x, "y": y, "bbox": [x - h, y - h, x + h, y + h], "score": round(sc, 3)})

    # ---- units: closed loops of the apartment-boundary line, named by Whg./App. tags
    ue = (seg[ch["unit_edge"]] > 0.4).astype(np.uint8)
    ue = cv2.morphologyEx(ue, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    cs, hier = cv2.findContours(ue, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    units = []
    # The model's nominal pixel density is only a contour filter, never a measured scale.
    loops = [c for c in cs if cv2.contourArea(c) > 4 / (m_per_px or SWISS_M_PER_PX) ** 2]
    for uid, (tx, ty) in tags:
        best = None
        for c in loops:
            if cv2.pointPolygonTest(c, (float(tx), float(ty)), False) >= 0:
                a = cv2.contourArea(c)
                if best is None or a < best[1]:
                    best = (c, a)
        poly = cv2.approxPolyDP(best[0], 2, True)[:, 0, :] if best is not None else None
        units.append({"id": uid, "polygon": _round_poly(poly) if poly is not None else [], "tag_xy": [tx, ty]})
    for r in rooms:
        cx, cy = r["centroid"]
        for u in units:
            if u["polygon"] and cv2.pointPolygonTest(np.array(u["polygon"], np.float32), (cx, cy), False) >= 0:
                r["unit"] = u["id"]; break
    for u in units:
        u["area_m2"] = _area_sum([r for r in rooms if r["unit"] == u["id"] and not r["outdoor"] and not r["shaft"]])
        u.pop("tag_xy", None)
    facts = {"source": source, "width": W, "height": H, "scale": {"m_per_px": m_per_px, "method": method, "verified": m_per_px is not None},
             "rooms": rooms, "objects": objects, "units": units, "words": words, "storeys": 1, "warnings": warnings,
             "capabilities": {"object_types": list(models.obj_cls), "room_labels": bool(words), "room_categories": bool(words),
                              "apartment_inventory": bool(tags), "storey_count": False},
             "wall_mask": (seg[ch["wall"]] > 0.5)}
    _assign_rooms(facts)
    return summarize(facts)


def analyze_geometry(gray, source="raster", why=None):
    """Training-free fallback for drawing styles our models were not trained on."""
    from .geometry import extract
    g = extract(gray)
    H, W = gray.shape
    rooms = []
    for i, r in enumerate(sorted(g["rooms"], key=lambda r: (r["centroid"][1] // 80, r["centroid"][0]))):
        rooms.append({"id": f"r{i}", "number": str(i + 1), "name": None, "category": "unlabelled",
                      "area_m2": None, "area_px": round(r["area_px"], 1), "area_source": "set the scale to measure",
                      "area_geom_m2": None, "polygon": _round_poly(r["polygon"]),
                      "centroid": [round(v, 1) for v in r["centroid"]], "unit": None, "outdoor": False, "shaft": False,
                      "confidence": 0.6})
    near = np.zeros((H, W), np.uint8)
    for r in rooms:
        cv2.fillPoly(near, [np.array(r["polygon"], np.int32)], 1)
    k = int(6 * g["stroke_px"]) + 3
    near = cv2.dilate(near, np.ones((k, k), np.uint8))
    objects = []
    for o in g["openings"]:
        if near[min(H - 1, int(o["y"])), min(W - 1, int(o["x"]))]:
            objects.append({"id": f"o{len(objects)}", "type": "opening", "x": round(o["x"], 1), "y": round(o["y"], 1),
                            "bbox": [round(v, 1) for v in o["bbox"]], "score": 0.5, "length_px": o["length_px"]})
    warn = [why] if why else []
    warn.append("Unknown drawing style: rooms found by wall geometry (no learned model). Use Set scale and click a known dimension to get areas in m2.")
    facts = {"source": source, "style": "geometry", "width": W, "height": H,
             "scale": {"m_per_px": None, "method": "not calibrated", "verified": False},
             "capabilities": {"object_types": ["opening"], "room_labels": False, "room_categories": False,
                              "apartment_inventory": False, "storey_count": False},
             "rooms": rooms, "objects": objects, "units": [], "words": [], "storeys": 1,
             "warnings": warn, "wall_mask": g["wall_mask"]}
    _assign_rooms(facts)
    return summarize(facts)


def apply_scale(facts, m_per_px, method):
    """Re-measure every geometry-based area with a new scale (printed labels stay authoritative)."""
    if type(m_per_px) not in (int, float) or not math.isfinite(m_per_px) or m_per_px <= 0:
        raise ValueError("Scale must be a positive finite metres-per-pixel value.")
    facts["scale"] = {"m_per_px": m_per_px, "method": method, "verified": True}
    for r in facts["rooms"]:
        if r.get("area_px") is None:
            continue
        geo = round(r["area_px"] * m_per_px ** 2, 2)
        r["area_geom_m2"] = geo
        if not str(r.get("area_source", "")).startswith("printed"):
            r["area_m2"], r["area_source"] = geo, "geometry x " + method
    for u in facts["units"]:
        u["area_m2"] = _area_sum([r for r in facts["rooms"] if r["unit"] == u["id"] and not r["outdoor"] and not r["shaft"]])
    facts["warnings"] = [w for w in facts["warnings"] if "Set scale" not in w and "Scale not calibrated" not in w]
    return summarize(facts)


def _empty_facts(gray, source, why):
    h, w = gray.shape
    return summarize({"source": source, "width": w, "height": h,
                      "scale": {"m_per_px": None, "method": "not measured", "verified": False},
                      "capabilities": {"object_types": [], "room_labels": False, "room_categories": False,
                                       "apartment_inventory": False, "storey_count": False},
                      "rooms": [], "objects": [], "units": [], "words": [], "storeys": None, "warnings": [why]})


def is_swiss_sheet(gray) -> bool:
    """ponytail: style router by sheet geometry (A-series landscape/portrait at >=120 dpi).
    Upgrade path: a tiny style classifier if more drawing styles get their own models."""
    h, w = gray.shape
    r = max(h, w) / min(h, w)
    return abs(r - 1.414) < 0.03 and max(h, w) >= 1700


def analyze_raster_cc(gray, source="raster"):
    """CubiCasa-style residential plan (Finnish real-estate drawings)."""
    from train.build_cubicasa import wall_thickness
    from train.train_plannet import predict_full
    from .models import heat_peaks
    models = Models.get()
    warnings = []
    H0, W0 = gray.shape
    wt = wall_thickness(gray)
    f = float(np.clip(models.cc_wall_px / wt, 0.35, 3.0)) if wt > 0 else 1.0
    g = cv2.resize(gray, (int(W0 * f), int(H0 * f)), interpolation=cv2.INTER_AREA if f < 1 else cv2.INTER_CUBIC)
    seg, heat = predict_full(models.cc, g)
    seg = seg.numpy()
    ch = {n: i for i, n in enumerate(models.cc_seg)}
    inv = 1.0 / f  # model px -> display px
    room = (seg[ch["room"]] > 0.5) & (seg[ch["room_edge"]] < 0.5) & (seg[ch["wall"]] < 0.5)
    room = cv2.morphologyEx(room.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, cents = cv2.connectedComponentsWithStats(room, 4)
    types = [c for c in models.cc_seg[3:]]
    rooms = []
    min_px = (models.cc_wall_px * 4) ** 2  # ~ a 1 m x 1 m closet at training density
    for k in range(1, n):
        if stats[k, 4] < min_px:
            continue
        m = lab == k
        grown = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) & (seg[ch["wall"]] < 0.5)
        cs, _ = cv2.findContours(grown, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)
        poly = cv2.approxPolyDP(c, 1.2, True)[:, 0, :].astype(float) * inv
        probs = [float(seg[ch[t]][m].mean()) for t in types]
        best = int(np.argmax(probs))
        cat = types[best] if probs[best] > 0.35 else "room"
        rooms.append({"id": f"r{len(rooms)}", "number": None, "name": None, "category": cat,
                      "pixels": float(cv2.contourArea(poly.astype(np.float32))), "polygon": _round_poly(poly),
                      "centroid": [round(float(v) * inv, 1) for v in cents[k]], "unit": None,
                      "outdoor": cat == "balcony", "shaft": False, "confidence": round(probs[best], 3)})
    peaks = heat_peaks(heat, thresh=0.35)
    objects = []
    for ci, plist in enumerate(peaks):
        t = models.cc_obj[ci]
        t = "washbasin" if t == "sink" else t
        for x, y, sc in plist:
            X, Y = x * inv, y * inv
            h = 14 * inv
            objects.append({"id": f"o{len(objects)}", "type": t, "x": round(X, 1), "y": round(Y, 1),
                            "bbox": [X - h, Y - h, X + h, Y + h], "score": round(sc, 3)})
    # Door width and image resolution do not establish the drawing's physical scale.
    m_per_px = None
    warnings.append("Set scale from a known dimension. Typical door widths are not a measured scale; areas are unavailable.")
    _raster_areas(rooms, None, source)
    # storeys: separate building footprints drawn side by side
    fp = (seg[ch["wall"]] > 0.5).astype(np.uint8)
    fp = cv2.morphologyEx(fp, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    cs, _ = cv2.findContours(fp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas = sorted([cv2.contourArea(c) for c in cs], reverse=True)
    storeys = sum(1 for a in areas if areas and a > 0.25 * areas[0]) or 1
    wall = cv2.resize((seg[ch["wall"]] > 0.5).astype(np.uint8), (W0, H0), interpolation=cv2.INTER_NEAREST) > 0
    facts = {"source": source, "style": "cubicasa", "width": W0, "height": H0,
             "scale": {"m_per_px": m_per_px, "method": "not calibrated", "verified": False},
             "capabilities": {"object_types": ["washbasin" if name == "sink" else name for name in models.cc_obj],
                              "room_labels": False, "room_categories": True, "apartment_inventory": False, "storey_count": True},
             "rooms": rooms, "objects": objects, "units": [], "words": [], "storeys": storeys,
             "warnings": warnings, "wall_mask": wall}
    _assign_rooms(facts)
    return summarize(facts)


def _assign_rooms(facts):
    polys = [(r["id"], np.array(r["polygon"], np.float32)) for r in facts["rooms"] if len(r["polygon"]) >= 3]
    for o in facts["objects"]:
        o["room"] = next((rid for rid, p in polys if cv2.pointPolygonTest(p, (float(o["x"]), float(o["y"])), False) >= 0), None)
    for r in facts["rooms"]:  # unnamed rooms: infer the type from what is inside
        if r.get("name") or r.get("category") not in ("shaft", "unlabelled", "room", "other"):
            continue
        kinds = {o["type"] for o in facts["objects"] if o.get("room") == r["id"]}
        if kinds & {"bathtub", "shower"}:
            r["category"] = "bathroom"
        elif "wc" in kinds:
            r["category"] = "wc_room"
        elif kinds & {"stove", "kitchen"}:
            r["category"] = "kitchen"
        elif r.get("shaft"):
            r["category"] = "shaft"


def load_gray(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError("unreadable image")
    if img.ndim == 3 and img.shape[2] == 4:
        a = img[..., 3:4].astype(np.float32) / 255
        img = (img[..., :3] * a + 255 * (1 - a)).astype(np.uint8)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img


def analyze_file(path):
    """Returns (display_image_bgr, facts)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".dxf":
        return analyze_dxf(path)
    if ext == ".pdf":
        import fitz
        page = fitz.open(path)[0]
        pix = page.get_pixmap(dpi=150, alpha=False)
        img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[..., :3][..., ::-1].copy()
        k = 150 / 72
        words = [{"text": w[4], "box": [w[0] * k, w[1] * k, w[2] * k, w[3] * k], "conf": 1.0} for w in page.get_text("words")]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if is_swiss_sheet(gray):
            facts = analyze_raster(gray, words=words or None, source="pdf")
        else:
            facts = analyze_geometry(gray, source="pdf")
            facts["words"] = words
        facts["warnings"].append("Only the first PDF page was analysed; sheet aspect ratio does not establish drawing style or scale.")
        return img, facts
    gray = load_gray(path)
    color = cv2.imread(path, cv2.IMREAD_COLOR)
    disp = color if color is not None and color.shape[:2] == gray.shape else cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    m = Models.get()
    facts = None
    if is_swiss_sheet(gray) and m.plan is not None:
        facts = analyze_raster(gray, source="raster")
        facts["style"] = "swiss"
    elif m.cc is not None:
        facts = analyze_raster_cc(gray, source="raster")
    # ponytail: confidence gate = "found at least 3 plausible rooms"; upgrade to a calibrated style classifier
    if facts is None or len([r for r in facts["rooms"] if (r.get("area_px") or 0) > 0]) < 3:
        facts = analyze_geometry(gray, source="raster")
    return disp, facts

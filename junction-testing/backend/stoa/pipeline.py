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


def summarize(facts):
    c = Counter(o["type"] for o in facts["objects"])
    rooms = facts["rooms"]
    indoor = [r for r in rooms if not r["outdoor"] and not r["shaft"]]
    facts["summary"] = {
        "rooms": len(rooms), "apartments": len(facts["units"]),
        "net_area_m2": round(sum(r["area_m2"] or 0 for r in indoor), 2),
        "outdoor_area_m2": round(sum(r["area_m2"] or 0 for r in rooms if r["outdoor"]), 2),
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
    for t in plan.texts:
        if t["layer"] == "ROOM_TEXT":
            p = T(t["xy"]); txt = t["text"].encode("ascii", "replace").decode()
            size = 0.32
            (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, size, 1)
            cv2.putText(img, txt, (int(p[0] - tw / 2), int(p[1] + th / 2)), cv2.FONT_HERSHEY_SIMPLEX, size, (30, 30, 30), 1, cv2.LINE_AA)

    rooms = []
    for i, r in enumerate(plan.rooms):
        poly = T(r["polygon"]) if r["polygon"] is not None else None
        area = r["area_label"] if r["area_label"] is not None else round(r["area_geom"] or 0, 2)
        rooms.append({
            "id": f"r{i}", "number": r["number"], "name": r["name"], "category": categorize(r["name"]),
            "area_m2": area, "area_source": "printed label (DXF text)" if r["area_label"] is not None else "polygon geometry",
            "area_geom_m2": round(r["area_geom"], 2) if r["area_geom"] else None,
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
    warnings = []
    if models.plan is None:
        raise RuntimeError("PlanNet weights missing: train with train/train_plannet.py")
    H, W = gray.shape
    seg, heat = predict_full(models.plan, gray)
    seg = seg.numpy(); ch = {n: i for i, n in enumerate(models.seg_ch)}
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
    pairs = [(r["area_label"], r["pixels"]) for r in rooms if r["area_label"] and r["pixels"] > 50]
    if len(pairs) >= 3:
        ratios = np.array([a / p for a, p in pairs])
        med = float(np.median(ratios))
        good = ratios[np.abs(ratios / med - 1) < 0.15]
        m_per_px = float(np.sqrt(np.median(good)))
        method = f"calibrated from {len(good)} printed room areas"
    else:
        m_per_px = SWISS_M_PER_PX
        method = "assumed 1:200 sheet at 150 dpi"
        warnings.append("Scale not calibrated from printed areas; geometric areas assume 1:200 at 150 dpi.")
    for r in rooms:
        geo = round(r["pixels"] * m_per_px ** 2, 2)
        r["area_geom_m2"] = geo
        if r["area_label"] is not None and abs(r["area_label"] / max(geo, 1e-6) - 1) < 0.25:
            r["area_m2"], r["area_source"] = r["area_label"], "printed label (read by GlyphNet)" if source == "raster" else "printed label (PDF text)"
        else:
            r["area_m2"], r["area_source"] = geo, "segmented geometry x calibrated scale"
            if r["area_label"] is not None:
                warnings.append(f"Room {r['number']}: printed {r['area_label']} m2 disagrees with geometry {geo} m2; used geometry.")
        del r["pixels"]

    # ---- objects from heatmap peaks
    peaks = heat_peaks(heat)
    objects = []
    for c, plist in enumerate(peaks):
        t = models.obj_cls[c]
        for x, y, sc in plist:
            h = 12 if t in ("wc", "washbasin", "shower") else 18 if t in ("door", "bathtub", "stove") else 14
            objects.append({"id": f"o{len(objects)}", "type": t, "x": x, "y": y, "bbox": [x - h, y - h, x + h, y + h], "score": round(sc, 3)})

    # ---- units: closed loops of the apartment-boundary line, named by Whg./App. tags
    ue = (seg[ch["unit_edge"]] > 0.4).astype(np.uint8)
    ue = cv2.morphologyEx(ue, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    cs, hier = cv2.findContours(ue, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    units = []
    loops = [c for c in cs if cv2.contourArea(c) > 4 / m_per_px ** 2]
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
        u["area_m2"] = round(sum(r["area_m2"] for r in rooms if r["unit"] == u["id"] and not r["outdoor"] and not r["shaft"]), 2)
        u.pop("tag_xy", None)
    for r in rooms:
        r.pop("area_label", None)
    facts = {"source": source, "width": W, "height": H, "scale": {"m_per_px": m_per_px, "method": method},
             "rooms": rooms, "objects": objects, "units": units, "words": words, "storeys": 1, "warnings": warnings,
             "wall_mask": (seg[ch["wall"]] > 0.5)}
    _assign_rooms(facts)
    return summarize(facts)


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
    # scale: these sheets carry no scale; estimate from door swings (typical 0.9 m leaf incl. frame)
    # ponytail: assumes standard Finnish 9M doors; replace with dimension-string reading when GlyphNet covers this style
    door_px = []
    dprob = heat[models.cc_obj.index("door")].numpy()
    for o in objects:
        if o["type"] == "door":
            x, y = int(o["x"] * f), int(o["y"] * f)
            r = (dprob[max(0, y - 25):y + 25, max(0, x - 25):x + 25] > 0.2)
            if r.any():
                ys, xs = np.nonzero(r); door_px.append(max(xs.ptp(), ys.ptp()) + 1)
    m_per_px = None
    if len(door_px) >= 2:
        m_per_px = 0.9 / (np.median(door_px) * inv * 1.6)
    if not m_per_px:
        m_per_px = 0.02
        warnings.append("No reliable scale on this sheet; areas are rough estimates.")
    else:
        warnings.append("Sheet has no scale: areas estimated from typical door width (0.9 m). Treat areas as approximate.")
    for r in rooms:
        r["area_m2"] = round(r.pop("pixels") * m_per_px ** 2, 1)
        r["area_source"] = "segmented geometry x door-based scale estimate"
        r["area_geom_m2"] = r["area_m2"]
    # storeys: separate building footprints drawn side by side
    fp = (seg[ch["wall"]] > 0.5).astype(np.uint8)
    fp = cv2.morphologyEx(fp, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    cs, _ = cv2.findContours(fp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    areas = sorted([cv2.contourArea(c) for c in cs], reverse=True)
    storeys = sum(1 for a in areas if areas and a > 0.25 * areas[0]) or 1
    wall = cv2.resize((seg[ch["wall"]] > 0.5).astype(np.uint8), (W0, H0), interpolation=cv2.INTER_NEAREST) > 0
    facts = {"source": source, "style": "cubicasa", "width": W0, "height": H0,
             "scale": {"m_per_px": m_per_px, "method": "estimated from door widths"},
             "rooms": rooms, "objects": objects, "units": [], "words": [], "storeys": storeys,
             "warnings": warnings, "wall_mask": wall}
    _assign_rooms(facts)
    return summarize(facts)


def _assign_rooms(facts):
    polys = [(r["id"], np.array(r["polygon"], np.float32)) for r in facts["rooms"] if len(r["polygon"]) >= 3]
    for o in facts["objects"]:
        o["room"] = next((rid for rid, p in polys if cv2.pointPolygonTest(p, (float(o["x"]), float(o["y"])), False) >= 0), None)


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
        return img, analyze_raster(gray, words=words or None, source="pdf")
    gray = load_gray(path)
    color = cv2.imread(path, cv2.IMREAD_COLOR)
    disp = color if color is not None and color.shape[:2] == gray.shape else cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    m = Models.get()
    if is_swiss_sheet(gray) or m.cc is None:
        facts = analyze_raster(gray, source="raster")
        facts["style"] = "swiss"
    else:
        facts = analyze_raster_cc(gray, source="raster")
    return disp, facts

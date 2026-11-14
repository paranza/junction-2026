"""Takeoff, tender estimate and code checks computed from a drawing's native objects.

Everything here is derived from the same extracted records the answers use (rooms with
polygons and areas, door frames, windows, fixtures). Every line carries the ids of the
objects it was computed from, so the viewer can show the receipt for each number.

What is measured and what is assumed is kept apart:
- measured: counts, room areas, room perimeters, window widths, walking distances,
  free space in a bathroom;
- assumed (editable per request): ceiling height, window glazing height, unit costs and
  carbon factors, the daylight and travel-distance limits. Defaults are placeholders for a
  demo, not market prices, EPD values or a specific national code.
"""
from __future__ import annotations

import heapq
import math
import re
import unicodedata
from statistics import median

# ----------------------------------------------------------------------------- vocabulary

def _plain(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text or "")).casefold() if not unicodedata.combining(c))


# term -> (function, english name). Matched on whole words of the normalized label.
# Sources: the room labels used in the Stoa preview (de, fr, it, fi, et, da) plus common synonyms.
_ONTOLOGY = [
    ("stair", "Stairwell", r"treppenhaus|cage d.?escalier|escalier|vano scala|scala|porras|porrashuone|trepikoda|trapperum|stair\w*"),
    ("lift", "Lift", r"lift|ascenseur|ascensore|hissi|elevator"),
    ("bedroom", "Bedroom", r"schlafzimmer|chambre(?: a coucher)?|camera(?: da letto)?|makuuhuone|mh|magamistuba|sovevaerelse|bedroom"),
    ("living", "Living / dining", r"wohnen(?:/essen)?|essen|sejour(?:/repas)?|repas|soggiorno(?:/pranzo)?|pranzo|olohuone|oh|elutuba(?:\+kook)?|stue|living|dining"),
    ("kitchen", "Kitchen", r"kuche|cuisine|cucina|keittio|k|kt|kook|kokken|tekokken|kitchen\w*"),
    ("bathroom", "Bathroom", r"bad|bain|salle de bains|sdb|bagno|kylpyhuone|kph|kh|ph|pesuhuone|vannituba|badevaerelse|bath\w*|shower room"),
    ("wc", "WC", r"wc|toilette|toilet|tualettruum|inva-wc|bad/wc"),
    ("corridor", "Corridor / hall", r"korridor|flur|diele|couloir|degagement|hall|corridoio|disimpegno|eteinen|et|kaytava|esik|koridor|gang|entre"),
    ("storage", "Storage", r"reduit|abstellraum|ripostiglio|varasto|var|vh|abiruum|depot|storage|closet|garderobe"),
    ("balcony", "Balcony / outdoor", r"balkon|balcon|balcone|loggia|terrasse|terrazza|parveke|rodu|terrace|veranda"),
    ("room", "Room (general)", r"zimmer|piece|stanza|huone|tuba|rum|room|kontor|office|buro"),
]
_HABITABLE = {"bedroom", "living", "room", "kitchen"}
_WET = {"bathroom", "wc"}


def classify(label):
    """Map a room label in any of the dataset languages to a function and an English name."""
    text = _plain(label)
    for function, english, pattern in _ONTOLOGY:
        if re.search(r"(?<![a-z])(?:" + pattern + r")(?![a-z])", text):
            return function, english
    return None, None


# ----------------------------------------------------------------------------- geometry

def _page_points(poly, page):
    return [(x * page["width"], y * page["height"]) for x, y in poly]


def _metres_per_point(rooms, page):
    """Scale from rooms whose metric area is known (printed or CAD geometry) vs their polygon."""
    from shapely.geometry import Polygon
    ratios = []
    for r in rooms:
        area_m2 = r.get("properties", {}).get("geometry_area_m2") or r.get("properties", {}).get("net_area_m2")
        if not area_m2 or not r.get("polygon") or len(r["polygon"]) < 3:
            continue
        shape = Polygon(_page_points(r["polygon"], page))
        if shape.is_valid and shape.area > 0:
            ratios.append(math.sqrt(area_m2 / shape.area))
    if len(ratios) < 3:
        return None
    m = median(ratios)
    good = [v for v in ratios if abs(v / m - 1) < 0.05]
    return median(good) if len(good) >= 3 else None


def _norm(points, page):
    return [[round(x / page["width"], 6), round(y / page["height"], 6)] for x, y in points]


# ----------------------------------------------------------------------------- defaults

DEFAULTS = {
    "ceiling_height_m": 2.6,
    "glazing_height_m": 1.4,
    "daylight_min_ratio": 0.10,
    "egress_limit_m": 35.0,
    "turning_diameter_m": 1.5,
    "waste_factor": 0.10,
}

# item key -> (label, unit, unit cost EUR, kg CO2e per unit). Demo placeholders: replace with
# the project's price book and the products' EPD values before using a number in a tender.
RATES = {
    "door": ("Interior door, leaf + frame", "pcs", 450.0, 45.0),
    "window": ("Window, per metre of opening width", "m", 520.0, 95.0),
    "window_unit": ("Window, average unit", "pcs", 780.0, 140.0),
    "toilet": ("WC, wall-hung incl. cistern", "pcs", 380.0, 40.0),
    "washbasin": ("Washbasin incl. tap", "pcs", 260.0, 25.0),
    "bathtub": ("Bathtub incl. fittings", "pcs", 650.0, 120.0),
    "shower": ("Shower tray incl. fittings", "pcs", 540.0, 60.0),
    "floor": ("Floor finish (parquet / vinyl)", "m²", 48.0, 9.0),
    "floor_wet": ("Floor tiles, wet rooms", "m²", 75.0, 14.0),
    "wall_paint": ("Wall paint on gypsum board", "m²", 18.0, 1.2),
    "wall_tiles": ("Wall tiles, wet rooms", "m²", 70.0, 13.0),
    "drywall": ("Gypsum board lining (both faces counted per room)", "m²", 35.0, 6.0),
    "skirting": ("Skirting board", "m", 12.0, 1.1),
}


# ----------------------------------------------------------------------------- main

def inspect(document, options=None):
    opts = {**DEFAULTS, **{k: v for k, v in (options or {}).items() if k in DEFAULTS and v is not None}}
    pages = document.get("pages") or []
    page = pages[0] if pages else {"width": 1.0, "height": 1.0}
    objects = document.get("objects", [])
    rooms = [o for o in objects if o.get("type") in ("room", "IfcSpace") and not str(o.get("properties", {}).get("spatial_kind", "")).startswith("shaft")]
    model_3d = str(document.get("format", "")).lower() == "ifc"
    # A whole IFC model mixes outlines from several floor views; lengths need one plan view.
    scale = None if model_3d else (_metres_per_point(rooms, page) if page.get("width", 1) > 1 else None)
    out = {"options": opts, "scale_m_per_pt": scale, "rooms": [], "boq": [], "checks": [], "warnings": []}
    if model_3d:
        out["warnings"].append("Whole 3D model: counts and modelled areas only. Open a floor plan view for wall areas, windows and code checks.")

    # ---- rooms: ontology, perimeter, wall area
    from shapely.geometry import Polygon, box
    room_shapes = {}
    for r in rooms:
        props = r.get("properties", {})
        function, english = classify(r.get("label"))
        outdoor = props.get("spatial_kind") == "outdoor" or function == "balcony"
        entry = {"id": r["id"], "label": r.get("label"), "number": props.get("room_number"),
                 "function": function or "unknown", "english": english or "Unclassified",
                 "ifc_space_type": "EXTERNAL" if outdoor else "INTERNAL",
                 "area_m2": props.get("net_area_m2"), "outdoor": outdoor, "polygon": r.get("polygon"),
                 "bbox": r.get("bbox")}
        if scale and r.get("polygon") and len(r["polygon"]) >= 3:
            shape = Polygon(_page_points(r["polygon"], page)).buffer(0)
            room_shapes[r["id"]] = shape
            entry["perimeter_m"] = round(shape.exterior.length * scale, 2)
        out["rooms"].append(entry)
    by_id = {e["id"]: e for e in out["rooms"]}

    # objects inside rooms
    def centre(o):
        b = o.get("bbox")
        return ((b[0] + b[2]) / 2 * page["width"], (b[1] + b[3]) / 2 * page["height"]) if b else None

    from shapely.geometry import Point
    room_of = {}  # object id -> room id (never written onto the cached document objects)
    for o in objects:
        c = centre(o)
        if c is None:
            continue
        room_of[o["id"]] = next((rid for rid, s in room_shapes.items() if s.contains(Point(c))), None)

    # Unnamed rooms (Trace labels them "Room"): type them from the fixtures inside.
    for e in out["rooms"]:
        if str(e["label"] or "").strip().casefold() in ("room", ""):
            kinds = {o.get("type") for o in objects if room_of.get(o["id"]) == e["id"]}
            e["function"], e["english"] = (("bathroom", "Bathroom") if kinds & {"bathtub", "shower"} else
                                           ("wc", "WC") if kinds & {"toilet", "washbasin"} else ("unknown", "Unnamed space"))

    # windows: width in metres and the room each one lights
    windows = []
    for w in (o for o in objects if o.get("type") in ("window", "IfcWindow")):
        entry = {"id": w["id"], "width_m": None, "room": None}
        if scale and w.get("polygon"):
            wshape = Polygon(_page_points(w["polygon"], page)).buffer(0)
            rect = wshape.minimum_rotated_rectangle
            xs = list(rect.exterior.coords)
            sides = sorted(math.dist(xs[i], xs[i + 1]) for i in range(4))
            entry["width_m"] = round(sides[-1] * scale, 3)
            near = wshape.buffer(0.6 / scale)
            hits = sorted(((near.intersection(s).area, rid) for rid, s in room_shapes.items() if near.intersects(s)), reverse=True)
            entry["room"] = hits[0][1] if hits else None
        windows.append(entry)

    # ---- bill of quantities
    def line(key, qty, ids, basis):
        label, unit, cost, carbon = RATES[key]
        qty = round(qty, 2)
        out["boq"].append({"key": key, "item": label, "unit": unit, "quantity": qty, "unit_cost_eur": cost,
                           "total_eur": round(qty * cost, 2), "carbon_kg_per_unit": carbon,
                           "carbon_kg": round(qty * carbon, 1), "evidence": ids, "basis": basis})

    for key, types in (("door", ("door", "IfcDoor")), ("toilet", ("toilet",)), ("washbasin", ("washbasin",)),
                       ("bathtub", ("bathtub",)), ("shower", ("shower",))):
        ids = [o["id"] for o in objects if o.get("type") in types]
        if ids:
            line(key, len(ids), ids, f"{len(ids)} detected {key} objects")
    measured = [w for w in windows if w["width_m"]]
    if windows and not measured:
        line("window_unit", len(windows), [w["id"] for w in windows], f"{len(windows)} modelled windows (no plan width available)")
    if measured:
        line("window", sum(w["width_m"] for w in measured), [w["id"] for w in measured],
             f"sum of {len(measured)} measured window opening widths")
    indoor = [e for e in out["rooms"] if not e["outdoor"] and e["area_m2"]]
    wet = [e for e in indoor if e["function"] in _WET]
    dry = [e for e in indoor if e["function"] not in _WET]
    k = 1 + opts["waste_factor"]
    if dry:
        line("floor", sum(e["area_m2"] for e in dry) * k, [e["id"] for e in dry],
             f"net area of {len(dry)} rooms x (1 + {opts['waste_factor']:.0%} waste)")
    if wet:
        line("floor_wet", sum(e["area_m2"] for e in wet) * k, [e["id"] for e in wet],
             f"net area of {len(wet)} wet rooms x (1 + {opts['waste_factor']:.0%} waste)")
    walled = [e for e in indoor if e.get("perimeter_m")]
    if walled:
        h = opts["ceiling_height_m"]
        door_w, win_h = 0.9 * 2.1, opts["glazing_height_m"]
        def wall_area(e):
            doors = sum(1 for o in objects if o.get("type") in ("door", "IfcDoor") and room_of.get(o["id"]) == e["id"])
            glazing = sum(w["width_m"] * win_h for w in windows if w["room"] == e["id"] and w["width_m"])
            return max(0.0, e["perimeter_m"] * h - doors * door_w - glazing)
        dry_w = [e for e in walled if e["function"] not in _WET]
        wet_w = [e for e in walled if e["function"] in _WET]
        if dry_w:
            line("wall_paint", sum(wall_area(e) for e in dry_w), [e["id"] for e in dry_w],
                 f"room perimeters x {h} m ceiling - door and window openings")
        if wet_w:
            line("wall_tiles", sum(wall_area(e) for e in wet_w) * k, [e["id"] for e in wet_w],
                 f"wet-room perimeters x {h} m - openings, + waste")
        line("drywall", sum(wall_area(e) for e in walled), [e["id"] for e in walled],
             "wall faces of all indoor rooms (each partition face counted from its room)")
        line("skirting", sum(e["perimeter_m"] for e in dry_w), [e["id"] for e in dry_w], "perimeters of dry rooms")
    out["totals"] = {"total_eur": round(sum(l["total_eur"] for l in out["boq"]), 2),
                     "carbon_kg": round(sum(l["carbon_kg"] for l in out["boq"]), 1)}

    # ---- daylight: glazing area / floor area for habitable rooms
    for e in indoor:
        if e["function"] not in _HABITABLE or not e.get("perimeter_m"):
            continue
        lit = [w for w in windows if w["room"] == e["id"] and w["width_m"]]
        glazing = sum(w["width_m"] for w in lit) * opts["glazing_height_m"]
        ratio = glazing / e["area_m2"] if e["area_m2"] else 0
        out["checks"].append({"check": "daylight", "room": e["id"], "label": f"{e['english']} {e['number'] or ''}".strip(),
                              "value": round(ratio, 3), "limit": opts["daylight_min_ratio"],
                              "status": "pass" if ratio >= opts["daylight_min_ratio"] else "fail",
                              "detail": f"{glazing:.2f} m² glazing ({len(lit)} windows x {opts['glazing_height_m']} m assumed height) / {e['area_m2']:.2f} m² floor",
                              "evidence": [e["id"]] + [w["id"] for w in lit]})

    # ---- accessibility: free turning circle in wet rooms
    fixtures = [o for o in objects if o.get("type") in ("toilet", "washbasin", "bathtub", "shower") and o.get("bbox")]
    for e in wet:
        shape = room_shapes.get(e["id"])
        if shape is None or not scale:
            continue
        free = shape
        for f in fixtures:
            if room_of.get(f["id"]) == e["id"]:
                b = f["bbox"]
                free = free.difference(box(b[0] * page["width"], b[1] * page["height"], b[2] * page["width"], b[3] * page["height"]))
        if free.is_empty:
            continue
        import shapely
        circle = shapely.maximum_inscribed_circle(free, tolerance=0.02 / scale)
        coords = list(circle.coords)
        diameter = 2 * math.dist(coords[0], coords[1]) * scale
        centre_pt = coords[0]
        out["checks"].append({"check": "turning_circle", "room": e["id"], "label": f"{e['english']} {e['number'] or ''}".strip(),
                              "value": round(diameter, 2), "limit": opts["turning_diameter_m"],
                              "status": "pass" if diameter >= opts["turning_diameter_m"] else "fail",
                              "detail": f"largest free circle {diameter:.2f} m between walls and fixtures (needs {opts['turning_diameter_m']} m)",
                              "circle": {"centre": _norm([centre_pt], page)[0], "radius_x": round(diameter / 2 / scale / page["width"], 6),
                                         "radius_y": round(diameter / 2 / scale / page["height"], 6)},
                              "evidence": [e["id"]]})

    # ---- egress: walking distance from every point of every flat to the nearest stairwell
    if scale and room_shapes:
        egress = _egress(out, objects, room_shapes, scale, page, opts)
        if egress:
            out["checks"].append(egress)
    elif not model_3d:
        out["warnings"].append("No metric scale on this sheet: lengths, wall areas and code checks need calibration.")
    return out


def _egress(out, objects, room_shapes, scale, page, opts):
    """Shortest walking path (8-connected grid, 0.15 m cells) through rooms and door openings
    to any stairwell; reports the furthest indoor point and draws its path."""
    import numpy as np
    import shapely
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    stairs = [rid for rid, e in ((e["id"], e) for e in out["rooms"]) if e["function"] == "stair" and rid in room_shapes]
    if not stairs:
        return None
    doors = [Polygon(_page_points(o["polygon"], page)).buffer(0.35 / scale) for o in objects
             if o.get("type") in ("door", "IfcDoor") and o.get("polygon") and len(o["polygon"]) >= 3]
    walk_rooms = [rid for rid, e in ((e["id"], e) for e in out["rooms"]) if rid in room_shapes and not e["outdoor"]]
    # Rooms connect only through door openings: shrink outlines slightly so rooms that merely
    # share an edge (no wall drawn between net outlines) do not become one walkable space.
    walkable = unary_union([room_shapes[r].buffer(-0.05 / scale) for r in walk_rooms] + doors)
    cell = 0.15 / scale
    x0, y0, x1, y1 = walkable.bounds
    xs = np.arange(x0, x1, cell); ys = np.arange(y0, y1, cell)
    if len(xs) * len(ys) > 2_000_000:
        return None
    gx, gy = np.meshgrid(xs, ys)
    free = shapely.contains_xy(walkable, gx, gy)
    target = np.zeros_like(free)
    for rid in stairs:
        target |= shapely.contains_xy(room_shapes[rid], gx, gy)
    target &= free
    dist = np.full(free.shape, np.inf)
    heap = []
    for i, j in zip(*np.nonzero(target)):
        dist[i, j] = 0.0
        heap.append((0.0, int(i), int(j)))
    heapq.heapify(heap)
    steps = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1), (-1, -1, 1.4142), (-1, 1, 1.4142), (1, -1, 1.4142), (1, 1, 1.4142)]
    H, W = free.shape
    while heap:
        d, i, j = heapq.heappop(heap)
        if d > dist[i, j]:
            continue
        for di, dj, c in steps:
            a, b = i + di, j + dj
            if 0 <= a < H and 0 <= b < W and free[a, b] and d + c < dist[a, b]:
                dist[a, b] = d + c
                heapq.heappush(heap, (d + c, a, b))
    # furthest reachable point that is inside a (non-stair) room
    inside = np.zeros_like(free)
    for rid in walk_rooms:
        if rid not in stairs:
            inside |= shapely.contains_xy(room_shapes[rid], gx, gy)
    reach = np.where(inside & np.isfinite(dist), dist, -1)
    if reach.max() <= 0:
        return None
    unreachable = int((inside & ~np.isfinite(dist)).sum())
    i, j = np.unravel_index(int(np.argmax(reach)), reach.shape)
    metres = float(dist[i, j]) * 0.15
    path = [(float(gx[i, j]), float(gy[i, j]))]
    while dist[i, j] > 0:
        best = None
        for di, dj, _ in steps:
            a, b = i + di, j + dj
            if 0 <= a < H and 0 <= b < W and np.isfinite(dist[a, b]) and (best is None or dist[a, b] < dist[best]):
                best = (a, b)
        if best is None or dist[best] >= dist[i, j]:
            break
        i, j = best
        path.append((float(gx[i, j]), float(gy[i, j])))
    path = path[::max(1, len(path) // 120)] + [path[-1]]
    start_room = next((rid for rid in walk_rooms if room_shapes[rid].contains(shapely.Point(path[0]))), None)
    label = by = next((e for e in out["rooms"] if e["id"] == start_room), None)
    return {"check": "egress", "room": start_room,
            "label": f"Furthest point: {by['english']} {by['number'] or ''}".strip() if by else "Furthest point",
            "value": round(metres, 1), "limit": opts["egress_limit_m"],
            "status": ("fail" if metres > opts["egress_limit_m"] else
                       "incomplete" if unreachable * 0.0225 > 0.05 * float(inside.sum()) * 0.0225 else "pass"),
            "detail": f"walking distance {metres:.1f} m through door openings to the nearest stairwell "
                      f"(limit {opts['egress_limit_m']} m, set it to your jurisdiction)"
                      + (f"; {unreachable * 0.0225:.1f} m² of floor not connected through a detected door" if unreachable else ""),
            "path": _norm(path, page), "evidence": ([start_room] if start_room else []) + stairs}

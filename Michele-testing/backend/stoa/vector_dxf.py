"""Exact parser for Swiss-Dwellings-style DXF floor plans.

The DXF is the ground truth: coordinates are metres, every element sits on a
named layer (WALL, DOOR, WINDOW, ROOM_OUTLINE, ROOM_TEXT, FIXTURE, UNIT_OUTLINE).
We use it two ways:
  1. a user uploads a DXF -> exact answers, no ML at all;
  2. training -> rasterise this geometry onto the matching PNG to get
     pixel-perfect labels for the PyTorch models (see labels.py).

Output coordinates stay in metres (DXF space, y up). Callers transform.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import ezdxf
import numpy as np

AREA_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*m")
NUMBER_RE = re.compile(r"^[A-Z]{0,2}\d+(?:\.\d+)+$")
UNIT_RE = re.compile(r"^(Whg\.|App\.)\s*([A-Z])$")

# Room names (de / fr / it) that are NOT counted as indoor net floor area.
OUTDOOR = {"balkon", "balcon", "balcone", "loggia", "terrasse", "terrazza", "terrazzo", "veranda", "sitzplatz"}
SHAFT_VOID = {"schacht", "gaine", "cavedio", "luftraum", "vide", "vuoto"}


def poly_area(pts: np.ndarray) -> float:
    x, y = pts[:, 0], pts[:, 1]
    return float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2)


def point_in_poly(p, poly: np.ndarray) -> bool:
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            inside = not inside
    return inside


@dataclass
class Plan:
    rooms: list = field(default_factory=list)      # dict(number,name,area_label,area_geom,polygon,unit,outdoor,text_xy)
    units: list = field(default_factory=list)      # dict(id, polygon)
    doors: list = field(default_factory=list)      # dict(center, radius, polylines)
    windows: list = field(default_factory=list)    # dict(polygon)
    fixtures: list = field(default_factory=list)   # dict(type, bbox, center)
    walls: list = field(default_factory=list)      # closed polygons (np arrays)
    wall_hatches: list = field(default_factory=list)
    texts: list = field(default_factory=list)      # dict(text, xy, height, layer)
    annotations: list = field(default_factory=list)


def _pts(e) -> np.ndarray:
    return np.array(e.get_points("xy"), dtype=float)


def _bbox(a: np.ndarray):
    return (*a.min(0), *a.max(0))


def _classify_fixtures(polys, circles):
    """Group FIXTURE entities into objects and type them by drawing signature.

    Signatures (Swiss Dwellings renderer, verified against questions.jsonl):
      bathtub          69-point open polyline (rounded inner basin)
      wc / washbasin   48-point open polyline (oval bowl); wc is elongated
      shower           closed ~square rect containing a small drain circle, no basin
      washing_machine  closed rect containing one r~0.15-0.25 circle (drum)
      stove            4 burner circles r=0.08
      kitchen          2-point counter lines (kitchen run)
    """
    objs = []
    bowls = [p for p in polys if not p["closed"] and len(p["pts"]) in (48, 69)]
    rects = [p for p in polys if p["closed"] and len(p["pts"]) == 4]
    lines = [p for p in polys if not p["closed"] and len(p["pts"]) == 2]
    used_rect = set()

    def rect_containing(c):
        best = None
        for i, r in enumerate(rects):
            x0, y0, x1, y1 = _bbox(r["pts"])
            if x0 - 1e-3 <= c[0] <= x1 + 1e-3 and y0 - 1e-3 <= c[1] <= y1 + 1e-3:
                a = (x1 - x0) * (y1 - y0)
                if best is None or a < best[1]:
                    best = (i, a)
        return None if best is None else best[0]

    small_all = [c for c in circles if c["r"] < 0.05]
    for b in bowls:
        a = b["pts"]
        x0, y0, x1, y1 = _bbox(a)
        c = ((x0 + x1) / 2, (y0 + y1) / 2)
        if len(a) == 69:
            t = "bathtub"
        else:
            # Legend: washbasin = oval WITH a drain dot, WC = oval without.
            has_dot = any(x0 <= s["c"][0] <= x1 and y0 <= s["c"][1] <= y1 for s in small_all)
            t = "washbasin" if has_dot else "wc"
        ri = rect_containing(c)
        if ri is not None:
            used_rect.add(ri)
            x0, y0, x1, y1 = _bbox(rects[ri]["pts"])
        objs.append({"type": t, "bbox": (x0, y0, x1, y1), "center": c})

    burners = [c for c in circles if abs(c["r"] - 0.08) < 0.01]
    small = [c for c in circles if c["r"] < 0.05]
    drums = [c for c in circles if 0.1 < c["r"] < 0.35]

    for d in drums:
        ri = rect_containing(d["c"])
        bb = _bbox(rects[ri]["pts"]) if ri is not None else (d["c"][0] - d["r"], d["c"][1] - d["r"], d["c"][0] + d["r"], d["c"][1] + d["r"])
        if ri is not None:
            used_rect.add(ri)
        objs.append({"type": "washing_machine", "bbox": bb, "center": d["c"]})

    for s in small:
        ri = rect_containing(s["c"])
        if ri is None or ri in used_rect:
            continue  # drain of a bathtub (rect already used) or stray dot
        used_rect.add(ri)
        bb = _bbox(rects[ri]["pts"])
        objs.append({"type": "shower", "bbox": bb, "center": ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)})

    # Stoves: cluster burners (4 per hob) by proximity.
    remaining = list(burners)
    while remaining:
        seed = remaining.pop()
        group = [seed]
        for c in remaining[:]:
            if np.hypot(c["c"][0] - seed["c"][0], c["c"][1] - seed["c"][1]) < 0.6:
                group.append(c)
                remaining.remove(c)
        xs = [g["c"][0] for g in group]
        ys = [g["c"][1] for g in group]
        bb = (min(xs) - 0.1, min(ys) - 0.1, max(xs) + 0.1, max(ys) + 0.1)
        objs.append({"type": "stove", "bbox": bb, "center": (float(np.mean(xs)), float(np.mean(ys)))})

    # Kitchen counters: rects that are long and ~0.6 deep and not used by sanitary fixtures.
    for i, r in enumerate(rects):
        if i in used_rect:
            continue
        x0, y0, x1, y1 = _bbox(r["pts"])
        w, h = sorted((x1 - x0, y1 - y0))
        if 0.5 <= w <= 0.75 and h >= 1.0:
            objs.append({"type": "kitchen", "bbox": (x0, y0, x1, y1), "center": ((x0 + x1) / 2, (y0 + y1) / 2)})
    return objs


def _arc_ends(d):
    c = np.array(d["center"])
    return [c + d["radius"] * np.array([np.cos(np.radians(a)), np.sin(np.radians(a))]) for a in (d["start"], d["end"])]


def merge_double_doors(doors: list) -> list:
    """A double door is two arcs whose hinges are r1+r2 apart and whose leaves meet
    at the midpoint of the opening. Count it once (63/65 plans exact vs 37/65 raw)."""
    used, out = set(), []
    for i, a in enumerate(doors):
        if i in used:
            continue
        ca = np.array(a["center"])
        for j in range(i + 1, len(doors)):
            if j in used:
                continue
            b = doors[j]
            cb = np.array(b["center"])
            if abs(np.linalg.norm(ca - cb) - a["radius"] - b["radius"]) > 0.05:
                continue
            mid = (ca + cb) / 2
            if min(np.linalg.norm(e - mid) for e in _arc_ends(a)) < 0.05 and \
               min(np.linalg.norm(e - mid) for e in _arc_ends(b)) < 0.05:
                used.add(j)
                a = dict(a, double=True, partner=b)
                break
        out.append(a)
    return out


def parse_dxf(path: str) -> Plan:
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    plan = Plan()
    room_polys, fix_polys, fix_circles = [], [], []
    door_lines = []
    for e in msp:
        layer, kind = e.dxf.layer.upper(), e.dxftype()
        if kind == "TEXT":
            plan.texts.append({"text": e.dxf.text, "xy": (e.dxf.insert.x, e.dxf.insert.y),
                               "height": e.dxf.height, "layer": layer})
            continue
        if layer == "WALL":
            if kind == "LWPOLYLINE":
                plan.walls.append(_pts(e))
            elif kind == "HATCH":
                for p in e.paths:
                    try:
                        v = np.array([(v[0], v[1]) for v in p.vertices], dtype=float)
                        if len(v) >= 3:
                            plan.wall_hatches.append(v)
                    except AttributeError:
                        pass
        elif layer == "DOOR":
            if kind == "ARC":
                plan.doors.append({"center": (e.dxf.center.x, e.dxf.center.y), "radius": e.dxf.radius,
                                   "start": e.dxf.start_angle, "end": e.dxf.end_angle})
            elif kind == "LWPOLYLINE":
                door_lines.append(_pts(e))
        elif layer == "WINDOW" and kind == "LWPOLYLINE" and e.closed:
            plan.windows.append({"polygon": _pts(e)})
        elif layer == "ROOM_OUTLINE" and kind == "LWPOLYLINE":
            room_polys.append(_pts(e))
        elif layer == "UNIT_OUTLINE" and kind == "LWPOLYLINE":
            plan.units.append({"id": None, "polygon": _pts(e)})
        elif layer == "FIXTURE":
            if kind == "LWPOLYLINE":
                fix_polys.append({"pts": _pts(e), "closed": e.closed})
            elif kind == "CIRCLE":
                fix_circles.append({"c": (e.dxf.center.x, e.dxf.center.y), "r": e.dxf.radius})

    plan.fixtures = _classify_fixtures(fix_polys, fix_circles)

    # Door leaf geometry (5-pt polyline = leaf rectangle) attached to its arc for drawing.
    for d in plan.doors:
        d["leaf"] = [l for l in door_lines if len(l) == 5 and
                     np.min(np.hypot(l[:, 0] - d["center"][0], l[:, 1] - d["center"][1])) < 0.05]
    plan.doors = merge_double_doors(plan.doors)

    # Room texts come in stacks: [name], number, [area]. Group by shared x and close y.
    rt = [t for t in plan.texts if t["layer"] == "ROOM_TEXT"]
    numbers = [t for t in rt if NUMBER_RE.match(t["text"].strip())]
    unit_tags = [t for t in rt if UNIT_RE.match(t["text"].strip())]
    for n in numbers:
        stack = [t for t in rt if abs(t["xy"][0] - n["xy"][0]) < 1e-6 and abs(t["xy"][1] - n["xy"][1]) < 1.2]
        name = next((t["text"] for t in stack if t["xy"][1] > n["xy"][1] and not UNIT_RE.match(t["text"].strip())
                     and not AREA_RE.match(t["text"])), None)
        area_t = next((t for t in stack if t["xy"][1] < n["xy"][1] and AREA_RE.match(t["text"])), None)
        area = float(AREA_RE.match(area_t["text"]).group(1).replace(",", ".")) if area_t else None
        # room polygon: smallest outline containing the number text
        cands = [p for p in room_polys if point_in_poly(n["xy"], p)]
        poly = min(cands, key=poly_area) if cands else None
        low = (name or "").strip().lower()
        plan.rooms.append({
            "number": n["text"].strip(), "name": name, "area_label": area,
            "area_geom": poly_area(poly) if poly is not None else None,
            "polygon": poly, "text_xy": n["xy"], "unit": None,
            "outdoor": low in OUTDOOR, "shaft": low in SHAFT_VOID or not low,  # number-only rooms are shafts/voids
        })

    # Unit ids from tags placed inside unit outlines.
    for u in plan.units:
        tag = next((t for t in unit_tags if point_in_poly(t["xy"], u["polygon"])), None)
        u["id"] = UNIT_RE.match(tag["text"].strip()).group(2) if tag else None
    for r in plan.rooms:
        probe = r["polygon"].mean(0) if r["polygon"] is not None else r["text_xy"]
        for u in plan.units:
            if point_in_poly(r["text_xy"], u["polygon"]) or point_in_poly(probe, u["polygon"]):
                r["unit"] = u["id"]
                break
    # A number-only room is a shaft/void unless it holds sanitary fixtures (then it is a small bathroom).
    for r in plan.rooms:
        if r["shaft"] and not (r["name"] or "").strip() and r["polygon"] is not None:
            if any(point_in_poly(f["center"], r["polygon"]) for f in plan.fixtures):
                r["shaft"] = False
    plan.annotations = [t for t in plan.texts if t["layer"] == "ANNOTATION"]
    return plan


def summarize(plan: Plan) -> dict:
    """Counts and areas a construction engineer asks for, computed exactly."""
    from collections import Counter
    fx = Counter(f["type"] for f in plan.fixtures)
    def area(r):
        return r["area_label"] if r["area_label"] is not None else (r["area_geom"] or 0.0)
    indoor = [r for r in plan.rooms if not r["outdoor"] and not r["shaft"]]
    units = {}
    for r in indoor:
        if r["unit"]:
            units[r["unit"]] = units.get(r["unit"], 0.0) + area(r)
    return {
        "apartments": len(plan.units),
        "doors": len(plan.doors),
        "windows": len(plan.windows),
        "wc": fx["wc"], "washbasin": fx["washbasin"], "bathtub": fx["bathtub"],
        "shower": fx["shower"], "stove": fx["stove"], "washing_machine": fx["washing_machine"],
        "rooms": len(plan.rooms),
        "net_area_indoor": round(sum(area(r) for r in indoor), 2),
        "unit_areas": {k: round(v, 2) for k, v in sorted(units.items())},
    }


if __name__ == "__main__":
    import sys
    p = parse_dxf(sys.argv[1])
    print(summarize(p))

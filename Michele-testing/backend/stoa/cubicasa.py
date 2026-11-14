"""CubiCasa5k SVG annotations -> geometry + training targets.

CubiCasa5k (Kalervo et al. 2019, CC BY-NC 4.0) ships, for ~5000 Finnish plans, an
SVG (model.svg) in the pixel space of F1_scaled.png with classed groups:
Wall, Window, Door <type>, Space <Type>, FixedFurniture <Type>, nested transforms.
The preview dataset's cubicasa5k/<set>-<id>.png images are F1_original.png of these.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import numpy as np

SVGNS = "{http://www.w3.org/2000/svg}"

# Space class -> our room category
SPACE_CAT = [
    (r"^Space (Bedroom)", "bedroom"), (r"^Space (Kitchen)", "kitchen"), (r"^Space (LivingRoom|Dining|Den)", "living"),
    (r"^Space Bath", "bathroom"), (r"^Space (Toilet|WC)", "wc_room"), (r"^Space Sauna", "sauna"),
    (r"^Space Outdoor Balcony", "balcony"), (r"^Space Outdoor", "outdoor"), (r"^Space (Entry|DraughtLobby|Hall|Corridor|Lobby)", "corridor"),
    (r"^Space (Storage|Closet|Utility|TechnicalRoom|DressingRoom|Attic)", "storage"), (r"^Space (Garage|CarPort)", "garage"),
]
ROOM_TYPES = ["bedroom", "kitchen", "living", "bathroom", "wc_room", "sauna", "balcony", "corridor", "storage"]


def _matrix(t: str | None) -> np.ndarray:
    M = np.eye(3)
    if not t:
        return M
    for name, args in re.findall(r"(\w+)\(([^)]*)\)", t):
        v = [float(x) for x in re.split(r"[ ,]+", args.strip()) if x]
        if name == "matrix" and len(v) == 6:
            m = np.array([[v[0], v[2], v[4]], [v[1], v[3], v[5]], [0, 0, 1]])
        elif name == "translate":
            m = np.array([[1, 0, v[0]], [0, 1, v[1] if len(v) > 1 else 0], [0, 0, 1]])
        elif name == "scale":
            m = np.diag([v[0], v[1] if len(v) > 1 else v[0], 1])
        elif name == "rotate":
            a = np.radians(v[0]); c, s = np.cos(a), np.sin(a)
            m = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
            if len(v) == 3:
                m = np.array([[1, 0, v[1]], [0, 1, v[2]], [0, 0, 1]]) @ m @ np.array([[1, 0, -v[1]], [0, 1, -v[2]], [0, 0, 1]])
        else:
            continue
        M = M @ m
    return M


def _pts(s: str, M: np.ndarray) -> np.ndarray:
    v = [float(x) for x in re.split(r"[ ,]+", s.strip()) if x]
    p = np.array(v[: len(v) // 2 * 2]).reshape(-1, 2)
    if not len(p):
        return p
    return (np.c_[p, np.ones(len(p))] @ M.T)[:, :2]


def parse_svg(path: str) -> dict:
    root = ET.parse(path).getroot()
    out = {"walls": [], "windows": [], "doors": [], "spaces": [], "furniture": [], "floors": 0}

    def first_poly(g, M):
        """Outline polygon of an element: its own first <polygon> child (not nested decorations)."""
        for ch in g:
            if ch.tag == SVGNS + "polygon":
                return _pts(ch.get("points", ""), M @ _matrix(ch.get("transform")))
        return None

    def all_points(g, M):
        pts = []
        for ch in g.iter():
            if ch.tag == SVGNS + "polygon":
                pass
        def rec(n, MM):
            MM = MM @ _matrix(n.get("transform"))
            if n.tag == SVGNS + "polygon":
                pts.append(_pts(n.get("points", ""), MM))
            elif n.tag == SVGNS + "rect":
                x, y, w, h = (float(n.get(k, 0)) for k in ("x", "y", "width", "height"))
                pts.append((np.c_[np.array([[x, y], [x + w, y + h]]), np.ones(2)] @ MM.T)[:, :2])
            for c in n:
                cls = c.get("class", "")
                if "Dimension" in cls or "SelectionControls" in cls or "Label" in cls:
                    continue
                rec(c, MM)
        for c in g:
            rec(c, M)
        pts = [p for p in pts if len(p)]
        return np.concatenate(pts) if pts else None

    def walk(node, M):
        for g in node:
            if g.tag != SVGNS + "g":
                continue
            cls = (g.get("class") or "").strip()
            MM = M @ _matrix(g.get("transform"))
            if cls.startswith("Floorplan"):
                out["floors"] += 1
            if cls == "Wall" or cls.startswith("Wall "):
                p = first_poly(g, MM)
                if p is not None and len(p) >= 3:
                    out["walls"].append(p)
                walk(g, MM)  # windows and doors are nested inside walls
                continue
            if cls.startswith("Window"):
                p = first_poly(g, MM)
                if p is not None and len(p) >= 3:
                    out["windows"].append({"type": cls, "polygon": p})
                continue
            if cls.startswith("Door") and cls != "Doors":
                p = first_poly(g, MM)
                ap = all_points(g, MM)
                if p is not None and len(p) >= 3:
                    out["doors"].append({"type": cls, "polygon": p, "extent": ap if ap is not None else p})
                continue
            if cls.startswith("Space "):
                p = first_poly(g, MM)
                cat = next((c for pat, c in SPACE_CAT if re.match(pat, cls)), "other")
                if p is not None and len(p) >= 3:
                    out["spaces"].append({"type": cls, "category": cat, "polygon": p})
                walk(g, MM)  # furniture may be nested inside spaces
                continue
            if cls.startswith("FixedFurnitureSet"):
                walk(g, MM)
                continue
            if cls.startswith("FixedFurniture"):
                ap = all_points(g, MM)
                if ap is not None:
                    out["furniture"].append({"type": cls, "bbox": (*ap.min(0), *ap.max(0))})
                walk(g, MM)  # e.g. a sink nested in a base cabinet
                continue
            walk(g, MM)

    walk(root, np.eye(3))
    return out


def furniture_kind(t: str):
    t = t.replace("FixedFurniture", "").strip()
    if re.match(r"^Toilet", t):
        return "wc"
    if re.match(r"^(Sink|DoubleSink|RoundSink|CornerSink)", t):
        return "sink"
    if re.match(r"^Bathtub", t):
        return "bathtub"
    if re.match(r"^Shower$", t) or re.match(r"^ShowerCab", t):
        return "shower"
    if "IntegratedStove" in t or re.match(r"^ElectricalAppliance Stove", t):
        return "stove"
    if "SaunaStove" in t:
        return "sauna_stove"
    return None


def _inside(bb, poly):
    from .vector_dxf import point_in_poly
    return point_in_poly(((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2), poly)


def refine_wet_rooms(a: dict):
    """Bath spaces: with shower/bathtub -> bathroom; toilet only -> wc_room; sauna stove -> sauna."""
    for sp in a["spaces"]:
        if sp["category"] != "bathroom":
            continue
        kinds = {furniture_kind(f["type"]) for f in a["furniture"] if _inside(f["bbox"], sp["polygon"])}
        if "sauna_stove" in kinds:
            sp["category"] = "sauna"
        elif not kinds & {"shower", "bathtub"} and "wc" in kinds:
            sp["category"] = "wc_room"
    return a


def counts(a: dict) -> dict:
    from collections import Counter
    refine_wet_rooms(a)
    f = Counter(furniture_kind(x["type"]) for x in a["furniture"])
    sp = Counter(s["category"] for s in a["spaces"])
    return {
        "windows": len(a["windows"]),
        "doors": sum(1 for d in a["doors"] if not d["type"].startswith("Door None")),
        "wc": f["wc"], "sink": f["sink"], "shower_bathtub": f["shower"] + f["bathtub"],
        "floors": max(1, a["floors"]), "sauna": max(sp["sauna"], f["sauna_stove"]), "kitchen": sp["kitchen"], "bedroom": sp["bedroom"],
        "wc_room": sp["wc_room"], "bathroom": sp["bathroom"], "balcony": sp["balcony"], "outdoor_any": sp["balcony"] + sp["outdoor"], "sauna_stove": f["sauna_stove"],
    }

"""Material takeoff from extracted geometry: what a site crew orders.

Per room: floor area, perimeter (skirting), wall area to paint/tile for a given
ceiling height minus door and window openings. Defaults are typical and editable
from the UI (query params). All formulas are shown in the output.
"""
from __future__ import annotations

import numpy as np
import math

from .questions import measured_area

DOOR_W, DOOR_H = 0.9, 2.1      # m, typical interior door leaf opening
WIN_W, WIN_H = 1.2, 1.2        # m, typical window opening
WET = {"bathroom", "wc_room", "sauna"}


def perimeter_px(poly):
    p = np.asarray(poly, float)
    return float(np.sum(np.hypot(*(np.roll(p, -1, 0) - p).T))) if len(p) >= 3 else 0.0


def compute(facts: dict, ceiling_h: float = 2.5, waste: float = 0.10) -> dict:
    s = facts["scale"]["m_per_px"]
    rows = []
    method = str(facts.get("scale", {}).get("method", ""))
    known_scale = (facts.get("source") == "dxf" or facts.get("scale", {}).get("verified") is True
                   or method.startswith("calibrated"))
    rooms = [r for r in facts["rooms"] if not r.get("shaft")]
    if (type(s) not in (int, float) or not math.isfinite(s) or s <= 0 or not known_scale
            or not rooms or any(measured_area(r, facts) is None for r in rooms)):
        return {"assumptions": {"ceiling_height_m": ceiling_h, "waste_factor": waste,
                                "formula": "Set a verified scale and establish every included room area before calculating a takeoff."},
                "status": "insufficient_evidence", "rooms": [],
                "totals": {k: None for k in ("floor_m2", "flooring_order_m2", "skirting_m", "paint_m2", "wall_tiles_m2", "perimeter_m")}}
    for r in facts["rooms"]:
        if r.get("shaft"):
            continue
        objs = [o for o in facts["objects"] if o.get("room") == r["id"]]
        doors = sum(o["type"] == "door" for o in objs)
        wins = sum(o["type"] == "window" for o in objs)
        per = round(perimeter_px(r["polygon"]) * s, 2)
        floor = r["area_m2"] or 0
        wall = max(0.0, per * ceiling_h - doors * DOOR_W * DOOR_H - wins * WIN_W * WIN_H)
        wet = r.get("category") in WET
        rows.append({
            "id": r["id"], "number": r.get("number"), "name": r.get("name"), "category": r.get("category"),
            "floor_m2": round(floor, 2), "perimeter_m": per, "wall_m2": round(wall, 2),
            "doors": doors, "windows": wins, "outdoor": r.get("outdoor", False),
            "flooring_order_m2": round(floor * (1 + waste), 2),
            "skirting_m": round(max(0.0, per - doors * DOOR_W), 2),
            "wall_tiles_m2": round(wall * (1 + waste), 2) if wet else 0.0,
            "paint_m2": 0.0 if wet or r.get("outdoor") else round(wall, 2),
        })
    tot = lambda k: round(sum(x[k] for x in rows if not x["outdoor"]), 2)
    return {
        "assumptions": {"ceiling_height_m": ceiling_h, "waste_factor": waste, "door_opening_m": [DOOR_W, DOOR_H],
                        "window_opening_m": [WIN_W, WIN_H],
                        "formula": "wall = perimeter x height - doors x 0.9x2.1 - windows x 1.2x1.2; order = net x (1 + waste)"},
        "rooms": rows,
        "totals": {k: tot(k) for k in ("floor_m2", "flooring_order_m2", "skirting_m", "paint_m2", "wall_tiles_m2", "perimeter_m")},
    }

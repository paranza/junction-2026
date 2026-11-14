"""Training-free room extraction for any clean line drawing (fallback for unknown styles).

Idea: walls are the thickest ink strokes on a plan. Keep only strokes as thick as the
typical wall, bridge door gaps with directional closing, then every enclosed free-space
region that does not touch the sheet border is a room. The bridges themselves are the
door openings, and their median length (a door is ~0.85 m wide) gives a scale estimate
until the user calibrates with a known dimension.

Works on scans and phone photos of plans with solid walls. Known limits: hatched walls,
very faint scans, and open-plan spaces without a separating wall merge or vanish.
"""
from __future__ import annotations

import cv2
import numpy as np

DOOR_M = 0.85  # typical door opening incl. frame, used only for the scale estimate


def _ink(gray):
    g = cv2.GaussianBlur(gray, (3, 3), 0)
    # Otsu for clean scans; adaptive handles uneven phone-photo lighting. Union keeps both.
    _, otsu = cv2.threshold(g, 0, 1, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ada = cv2.adaptiveThreshold(g, 1, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    return (otsu & ada).astype(np.uint8)


def _stroke_width(ink):
    dt = cv2.distanceTransform(ink, cv2.DIST_L2, 3)
    ridge = (dt == cv2.dilate(dt, np.ones((3, 3), np.uint8))) & (dt >= 1)
    v = dt[ridge]
    if len(v) < 50:
        return 2.0
    return float(2 * np.percentile(v, 90))  # thickest common strokes = walls


def extract(gray):
    """Returns dict(rooms=[{polygon, area_px, centroid}], openings=[{x,y,length_px,bbox}],
    wall_mask, px_per_m_estimate or None, scale_up)."""
    H0, W0 = gray.shape
    up = max(1.0, 1500 / max(H0, W0))  # small web images: work at ~1500 px
    g = cv2.resize(gray, (int(W0 * up), int(H0 * up)), interpolation=cv2.INTER_CUBIC) if up > 1 else gray
    H, W = g.shape
    ink = _ink(g)
    t = _stroke_width(ink)
    k = max(2, int(round(t * 0.6)))
    walls = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    # drop handwriting / text blobs: wall networks are long, letters are compact
    n, lab, st, _ = cv2.connectedComponentsWithStats(walls, 8)
    keep = np.zeros(n, bool)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        keep[i] = max(w, h) > 12 * t or a > 60 * t * t
    walls = keep[lab].astype(np.uint8)
    # enclosure = walls plus any long thin line work (windows are thin lines across the wall);
    # compact blobs (text, numbers, symbols) are removed
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
    keep = np.zeros(n, bool)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        keep[i] = max(w, h) > 15 * t
    bound = (keep[lab].astype(np.uint8) | walls)
    # bridge door gaps: directional closing up to ~7 wall thicknesses
    L = int(max(8, 7 * t))
    closed = bound.copy()
    for ker in (np.ones((1, L), np.uint8), np.ones((L, 1), np.uint8)):
        closed |= cv2.morphologyEx(bound, cv2.MORPH_CLOSE, ker)
    closed = cv2.dilate(closed, np.ones((3, 3), np.uint8))
    # free space -> rooms
    free = (1 - closed).astype(np.uint8)
    n, lab, st, cent = cv2.connectedComponentsWithStats(free, 4)
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    min_a, max_a = (10 * t) ** 2, 0.35 * H * W
    rooms = []
    for i in range(1, n):
        a = st[i, 4]
        if i in border or a < min_a or a > max_a:
            continue
        m = (lab == i).astype(np.uint8)
        m = cv2.dilate(m, np.ones((3, 3), np.uint8)) & (1 - walls)  # grow back over the dilation margin
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        if min(w, h) < 4 * t:  # slivers between parallel lines are not rooms
            continue
        poly = cv2.approxPolyDP(c, max(1.5, t * 0.4), True)[:, 0, :].astype(float) / up
        rooms.append({"polygon": poly, "area_px": float(cv2.contourArea(c)) / up ** 2,
                      "centroid": (cent[i] / up).tolist()})
    # openings = the bridges that closing added between wall ends
    bridge = (closed & (1 - cv2.dilate(bound, np.ones((5, 5), np.uint8)))).astype(np.uint8)
    n, lab, st, cent = cv2.connectedComponentsWithStats(bridge, 8)
    openings = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        length = max(w, h)
        if 2.5 * t <= length <= L + 4 and min(w, h) <= 3 * t:
            openings.append({"x": cent[i][0] / up, "y": cent[i][1] / up, "length_px": length / up,
                             "bbox": [x / up, y / up, (x + w) / up, (y + h) / up]})
    px_per_m = None
    if len(openings) >= 3:
        px_per_m = float(np.median([o["length_px"] for o in openings])) / DOOR_M
    wall_full = cv2.resize(walls, (W0, H0), interpolation=cv2.INTER_NEAREST) > 0 if up > 1 else walls > 0
    return {"rooms": rooms, "openings": openings, "wall_mask": wall_full, "px_per_m": px_per_m, "stroke_px": t / up}


if __name__ == "__main__":
    import sys
    g = cv2.imread(sys.argv[1], cv2.IMREAD_GRAYSCALE)
    r = extract(g)
    print(len(r["rooms"]), "rooms", len(r["openings"]), "openings", "px/m", r["px_per_m"], "stroke", r["stroke_px"])
    vis = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
    rng = np.random.default_rng(0)
    for rm in r["rooms"]:
        col = tuple(int(c) for c in rng.integers(60, 230, 3))
        cv2.polylines(vis, [rm["polygon"].astype(np.int32)], True, col, 2)
    for o in r["openings"]:
        cv2.circle(vis, (int(o["x"]), int(o["y"])), 4, (0, 0, 255), -1)
    cv2.imwrite(sys.argv[2], vis)

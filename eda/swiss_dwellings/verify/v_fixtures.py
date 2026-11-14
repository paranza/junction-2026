# PDF-only symbol classification for windows and sanitary fixtures (my own rules from v_framesig clusters).
# Duplicated records are drawn as identical paths: dedupe geometry for classification, keep multiplicity for counting.
import collections, math
from shapely.geometry import box, Polygon, LineString
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_pdf

def gkey(d):
    pts = [p for s in v_pdf.subpaths(d) for p in s]
    return (round(d.get("width") or 0, 2), len(d["items"]), tuple(sorted((round(x, 1), round(y, 1)) for x, y in pts)))

def classify(m):
    frames_all = [f for f in m["frames"] if round(f.get("width") or 0, 2) == 0.51]
    mult = collections.Counter(gkey(f) for f in frames_all)
    frames, seen = [], set()
    for f in frames_all:
        k = gkey(f)
        if k not in seen: seen.add(k); frames.append(f)
    blacks, seen = [], set()
    for d in m["blacks"]:
        k = gkey(d)
        if k not in seen: seen.add(k); blacks.append(d)
    res = []
    for f in frames:
        fr = f["rect"]
        fb = box(fr.x0 - 0.3, fr.y0 - 0.3, fr.x1 + 0.3, fr.y1 + 0.3)
        within = lambda r: fb.contains(box(r.x0, r.y0, max(r.x1, r.x0 + 1e-3), max(r.y1, r.y0 + 1e-3)))
        thin, parts = [], collections.Counter()
        for d in blacks:
            if not within(d["rect"]): continue
            w = round(d.get("width") or 0, 2)
            kinds = collections.Counter(it[0] for it in d["items"])
            if w == 0.37 and set(kinds) == {"l"} and kinds["l"] == 1: thin.append(d)
            elif w == 0.51:
                if kinds.get("l") == 47: parts["ellipse"] += 1
                elif kinds.get("l") == 68: parts["tub"] += 1
                elif kinds.get("l") == 1: parts["line"] += 1
                elif kinds.get("c") == 8: parts["circle"] += 1
                elif kinds.get("qu") == 1: parts["square"] += 1
                else: parts["other51"] += 1
            elif w == 0.99: continue  # wall outline strokes can fall inside a window bbox
            else: parts[f"other{w}"] += 1
        inner_frames = sum(1 for g in frames if g is not f and within(g["rect"]))
        if parts["tub"] >= 1: kind = "bathtub"
        elif parts["ellipse"] >= 1 and parts["line"] >= 1: kind = "wc"
        elif parts["ellipse"] >= 1 and parts["circle"] >= 1: kind = "washbasin"
        elif parts["square"] >= 1 and parts["circle"] >= 1: kind = "shower"
        elif parts["circle"] >= 4: kind = "stove"
        elif not parts and inner_frames == 0 and len(thin) == 2:
            ring = [p for s in v_pdf.subpaths(f) for p in s]
            mrr = Polygon(ring).minimum_rotated_rectangle
            c = list(mrr.exterior.coords)
            sides = sorted(((math.dist(c[i], c[i+1]), c[i], c[i+1]) for i in range(4)), key=lambda t: -t[0])
            L, a0, a1 = sides[0]
            ang_long = math.atan2(a1[1]-a0[1], a1[0]-a0[0])
            segs = [LineString([(d["items"][0][1].x, d["items"][0][1].y), (d["items"][0][2].x, d["items"][0][2].y)]) for d in thin]
            par = all(abs(math.sin(math.atan2(s.coords[1][1]-s.coords[0][1], s.coords[1][0]-s.coords[0][0]) - ang_long)) < 0.1 for s in segs)
            if segs[0].intersects(segs[1]): kind = "x_cross"
            elif par and min(s.length for s in segs) > 0.8 * L: kind = "window"
            else: kind = "two_lines_other"
        elif not parts and inner_frames == 0 and len(thin) == 0: kind = "empty"
        elif len(thin) >= 3: kind = "many_lines"
        else: kind = "other"
        res.append(dict(kind=kind, rect=tuple(round(v, 1) for v in fr), mult=mult[gkey(f)], d=f))
    return res

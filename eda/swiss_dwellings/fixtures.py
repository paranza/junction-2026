"""Classify FIXTURE symbols in a swiss_dwellings DXF by what each closed frame contains."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, glob, os, collections, sys
from shapely.geometry import Polygon, Point, LineString, box
DS = _DATA + "/data/swiss_dwellings"

def groups(msp):
    frames, parts = [], []
    for e in msp.query("*[layer=='FIXTURE']"):
        if e.dxftype() == "CIRCLE":
            c = e.dxf.center; r = e.dxf.radius
            parts.append(dict(kind="circle", r=r, geom=Point(c[0], c[1]).buffer(r), key=("C", round(c[0], 4), round(c[1], 4), round(r, 4))))
        else:
            pts = [tuple(p[:2]) for p in e.get_points()]
            if e.closed:
                frames.append(dict(poly=Polygon(pts), pts=pts, key=tuple(round(v, 4) for p in pts for v in p)))
            else:
                parts.append(dict(kind=f"open{len(pts)}", geom=LineString(pts), key=("L",) + tuple(round(v, 4) for p in pts for v in p)))
    out = []
    for fr in frames:
        P = fr["poly"].buffer(0.01)
        # parts inside this frame and not inside a smaller frame that is itself inside
        inside = [q for q in parts if P.contains(q["geom"])]
        inner_frames = [g for g in frames if g is not fr and g["poly"].area < fr["poly"].area and P.contains(g["poly"])]
        out.append(dict(frame=fr, parts=inside, inner_frames=inner_frames))
    return out

def classify(g):
    fr = g["frame"]["poly"]; minx, miny, maxx, maxy = fr.bounds
    w, h = sorted([maxx - minx, maxy - miny])
    kinds = collections.Counter(q["kind"] for q in g["parts"])
    circles = sorted(round(q["r"], 3) for q in g["parts"] if q["kind"] == "circle")
    n_inner = len(g["inner_frames"])
    sig = (n_inner, tuple(sorted(kinds.items())), tuple(circles))
    return sig, (round(w, 2), round(h, 2))

if __name__ == "__main__":
    sigs = collections.Counter(); ex = {}
    for f in sorted(glob.glob(f"{DS}/*.dxf")):
        msp = ezdxf.readfile(f).modelspace()
        for g in groups(msp):
            sig, wh = classify(g)
            # coarse signature: kinds only, circle count and radius buckets
            s2 = (sig[0], sig[1], len(sig[2]), tuple(sorted(set("big" if r >= 0.1 else ("burner" if r >= 0.06 else "dot") for r in sig[2]))))
            sigs[s2] += 1
            ex.setdefault(s2, []).append((os.path.basename(f)[:20], wh))
    for k, v in sigs.most_common():
        print(v, k, ex[k][:3])

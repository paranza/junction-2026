import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Are duplicated door records identical (invisible) or different swings (visible)?
import sys, os, collections, ezdxf, math
D = _DATA + "/data/swiss_dwellings"
def k(pts): return tuple(sorted((round(x, 3), round(y, 3)) for x, y in pts))
for stem in sys.argv[1:]:
    msp = ezdxf.readfile(f"{D}/{stem}.dxf").modelspace()
    ents = [e for e in msp if e.dxf.layer == "DOOR"]
    # entity order: check if door parts come grouped (frame, arc, leaf) in sequence
    seq = "".join("F" if (e.dxftype()=="LWPOLYLINE" and len(e)==5) else "A" if e.dxftype()=="ARC" else "L" if e.dxftype()=="LWPOLYLINE" and len(e)==2 else "?" for e in ents)
    frames = [e for e in ents if e.dxftype()=="LWPOLYLINE" and len(e)==5]
    arcs = [e for e in ents if e.dxftype()=="ARC"]
    leaves = [e for e in ents if e.dxftype()=="LWPOLYLINE" and len(e)==2]
    fk = collections.Counter(k([(p[0], p[1]) for p in f.get_points("xy")]) for f in frames)
    ak = collections.Counter((round(a.dxf.center[0],3), round(a.dxf.center[1],3), round(a.dxf.radius,3), round(a.dxf.start_angle%360,1), round(a.dxf.end_angle%360,1)) for a in arcs)
    lk = collections.Counter(k([(p[0], p[1]) for p in l.get_points("xy")]) for l in leaves)
    print("==", stem, "seq", seq[:60], "...")
    print(" frames", len(frames), "distinct", len(fk), "dup groups", sum(1 for v in fk.values() if v>1))
    print(" arcs", len(arcs), "distinct", len(ak), "leaves", len(leaves), "distinct", len(lk))
    # for each duplicated frame, are the associated arcs (within the frame bbox+radius) identical?
    for key_, n in fk.items():
        if n < 2: continue
        xs = [p[0] for p in key_]; ys = [p[1] for p in key_]
        cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
        near = [a for a in arcs if math.dist((a.dxf.center[0], a.dxf.center[1]), (cx, cy)) < 1.2]
        sig = collections.Counter((round(a.dxf.center[0],3), round(a.dxf.center[1],3), round(a.dxf.radius,3), round(a.dxf.start_angle%360,1), round(a.dxf.end_angle%360,1)) for a in near)
        print("  dup frame x%d at (%.2f,%.2f) w=%.2f h=%.2f; arcs near: %s" % (n, cx, cy, max(xs)-min(xs), max(ys)-min(ys), [(s[3], s[4], s[2], c) for s, c in sig.items()]))

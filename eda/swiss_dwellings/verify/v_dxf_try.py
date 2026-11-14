import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_dxf
for stem in sys.argv[1:]:
    m = v_dxf.load(stem)
    print("==", stem, "insunits", m["insunits"], "bulge", m["bulge_any"], "open room lines", m["open_room_lines"], "outlines", len(m["outl"]))
    print(" ann", m["ann"])
    print(" rooms", len(m["rooms"]), "no poly", sum(r["poly"] is None for r in m["rooms"]), "unlabelled", sum(r["label"] is None for r in m["rooms"]), "printed", sum(r["printed"] is not None for r in m["rooms"]))
    for r in m["rooms"]:
        if r["printed"] is not None and r["net"] is not None and round(r["net"], 2) != r["printed"]:
            print("  printed mismatch", r["num"], r["label"], r["printed"], round(r["raw"], 3), round(r["net"], 3), r["n_inner"])
    print(" units", [(round(u["poly"].area, 1), u["tags"]) for u in m["units"]])
    print(" tags", [(t["t"], t["unit"] is not None) for t in m["tags"]])
    print(" doors frames", len(m["door_frames"]), "distinct", len({v_dxf.key(p) for p in m["door_frames"]}), "arcs", len(m["door_arcs"]), "lines", len(m["door_lines"]), "other", dict(m["door_other"]))
    print(" windows rects", len(m["win_rects"]), "distinct", len({v_dxf.key(p) for p in m["win_rects"]}), "lines", len(m["win_lines"]), "other", dict(m["win_other"]))
    print(" fixtures", collections.Counter((f["kind"], f.get("n"), f.get("closed")) for f in m["fx"]))

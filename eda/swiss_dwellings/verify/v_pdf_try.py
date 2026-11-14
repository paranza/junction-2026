import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_pdf
for stem in sys.argv[1:]:
    m = v_pdf.load(stem)
    rs = m["rooms"]
    print("==", stem, "scale", m["scale"], "rooms", len(rs), "no poly", sum(r["poly"] is None for r in rs), "unlab", sum(r["label"] is None for r in rs),
          "printed", sum(r["printed"] is not None for r in rs), "polys", len(m["polys"]), collections.Counter(p["fill"] for p in m["polys"]))
    print(" fills of numbered rooms", collections.Counter(r["fill"] for r in rs))
    for r in rs:
        if r["printed"] is not None and r["net"] is not None and round(r["net"], 2) != r["printed"]:
            print("  printed mismatch", r["num"], r["label"], r["printed"], round(r["raw"], 3), round(r["net"], 3), r["n_inner"])
    print(" units", [(round(u["g"].area), u["tags"], u["w"]) for u in m["units"]])
    print(" doors", len(m["doors"]), "distinct", len(m["door_keys"]), "frames", len(m["frames"]))

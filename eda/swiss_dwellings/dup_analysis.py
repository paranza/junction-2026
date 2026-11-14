"""Where do duplicated door/window records sit? Test: duplicates = openings between two different units (or unit and common area)."""
import os, sys, glob, collections
import pandas as pd
from shapely.geometry import Polygon
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dxf_model as M

WD = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in sorted(glob.glob(f"{M.DS}/*.dxf")):
    name = os.path.basename(f)[:-4]
    m = M.load(name); msp = m["msp"]
    for layer, sel in [("DOOR", lambda e: len(e) == 5), ("WINDOW", lambda e: e.closed)]:
        ents = [e for e in msp.query(f"LWPOLYLINE[layer=='{layer}']") if sel(e)]
        keys = collections.Counter(tuple(round(v, 4) for p in e.get_points() for v in p[:2]) for e in ents)
        for k, mult in keys.items():
            pts = list(zip(k[0::2], k[1::2]))
            g = Polygon(pts).buffer(0.05)
            near = [r for r in m["rooms"] if r["poly"] is not None and r["poly"].intersects(g)]
            # "zones" a door touches: unit tag, or 'common' for numbered rooms outside any unit, 'outside' if fewer than 2 rooms
            zones = sorted({(r["unit"] or "common") for r in near})
            rows.append(dict(file=name, layer=layer, mult=mult, n_rooms=len(near), zones="|".join(zones), n_zones=len(zones)))
D = pd.DataFrame(rows)
D["dup"] = D.mult > 1
print(D.groupby(["layer", "mult"]).size())
print("\nDOOR: duplicated vs number of distinct zones touched")
print(pd.crosstab(D[D.layer == "DOOR"].n_zones, D[D.layer == "DOOR"].dup))
print("\nWINDOW: duplicated vs number of distinct zones touched")
print(pd.crosstab(D[D.layer == "WINDOW"].n_zones, D[D.layer == "WINDOW"].dup))
print("\nWINDOW: duplicated vs rooms touched")
print(pd.crosstab(D[D.layer == "WINDOW"].n_rooms, D[D.layer == "WINDOW"].dup))
# rule test per file: predicted gold = unique + (#unique openings touching >= 2 zones)
g = D.groupby(["file", "layer"]).apply(lambda d: pd.Series(dict(gold=d.mult.sum(), unique=len(d), rule=len(d) + (d.n_zones >= 2).sum()))).reset_index()
for L in ["DOOR", "WINDOW"]:
    x = g[g.layer == L]
    print(L, "files:", len(x), "gold==unique:", (x.gold == x.unique).sum(), "gold==unique+cross-zone:", (x.gold == x.rule).sum())
D.to_csv(f"{WD}/dup_openings.csv", index=False)

import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
import sys
sys.path.insert(0, _ROOT + "/eda/swiss_dwellings")
import dxf_model as M
from shapely.ops import unary_union
cases = [("site1110_bldg2250_floor10322", "5.11"), ("site11861_bldg18508_floor50415", "0.25"), ("site11861_bldg18508_floor50415", "0.01"),
         ("site1213_bldg2383_floor48290", "2.09"), ("site1689_bldg2841_floor13117", "4.17"), ("site610_bldg1324_floor50793", "2.17"), ("site65_bldg3_floor5", "4.26")]
for f, num in cases:
    m = M.load(f)
    r = next(r for r in m["rooms"] if r["num"] == num)
    inner = [o for o in m["outlines"] if o is not r["poly"] and r["poly"].intersection(o).area > 0.5 * o.area and o.area < r["poly"].area]
    nums_in = {o.wkt[:30]: [q["num"] for q in m["rooms"] if q["poly"] is o] for o in inner}
    print(f, num, r["label"], "printed", r["printed"], "poly", round(r["area"], 3), "interiors", len(r["poly"].interiors))
    for o in inner:
        print("   inner outline area", round(o.area, 3), "numbered as", [q["num"] + ":" + str(q["label"]) for q in m["rooms"] if q["poly"] is o])
    if inner:
        print("   area - inner:", round(r["area"] - sum(o.area for o in inner), 3), " area - union(inner):", round(r["poly"].difference(unary_union(inner)).area, 3))

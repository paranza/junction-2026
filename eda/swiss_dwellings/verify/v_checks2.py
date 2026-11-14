# F4 test: does subtracting holes / nested outlines matter under the official 2% rule?
# PDF: outer ring only vs compound path with holes. DXF: outer outline vs minus nested outlines.
# Also: what are the DXF ROOM_OUTLINE variants (open polylines, DASHED linetype)?
import sys, os, collections, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_pdf, v_dxf, v_parse, v_local, v_eval
import ezdxf
from shapely.geometry import Polygon, Point

stems = v_local.stems("pdf", "dxf")
qs = [q for q in v_parse.load() if q["lang"] == "en"]
C = collections.Counter(); asked_rel = []
for s in stems:
    m = v_eval.model(s)
    X = v_dxf.load(s)
    xr = {r["num"]: r for r in X["rooms"]}
    for r in m["rooms"]:
        g = r["poly"]["g"]
        outer = sum(Polygon(p.exterior).area for p in getattr(g, "geoms", [g])) * m["mpp"] ** 2
        r["outer"] = outer
        if r["printed"] is not None:
            C["printed"] += 1
            C["printed==round(pdf_outer)"] += round(outer, 2) == r["printed"]
            C["pdf_outer_off_gt_2pct"] += abs(outer - r["printed"]) > 0.02 * r["printed"]
            x = xr[r["num"]]
            C["printed==round(dxf_raw)"] += round(x["raw"], 2) == r["printed"]
            C["printed==round(dxf_net)"] += round(x["net"], 2) == r["printed"]
            C["dxf_raw_off_gt_2pct"] += abs(x["raw"] - r["printed"]) > 0.02 * r["printed"]
        C["rooms"] += 1
        C["rooms_outer_gt_net_by_2pct"] += outer > 1.02 * r["net"]
    # asked questions: outer-only variants under the 2% rule
    rooms = m["rooms"]
    for q in [q for q in qs if q["stem"] == s]:
        if q["fam"] == "area_room":
            r = [r for r in rooms if r["num"] == q["param"][0]][0]
            pred = r["outer"]
        elif q["fam"] == "area_label_total":
            pred = sum(r["outer"] for r in rooms if r["label"] == q["param"])
        elif q["fam"] == "area_total_indoor":
            pred = sum(r["outer"] for r in rooms if v_eval.FILL.get(r["fill"]) != "outdoor")
        elif q["fam"] == "area_apartment":
            pred = sum(r["outer"] for r in rooms if r["unit"] is not None and v_eval.FILL.get(r["fill"]) != "outdoor"
                       and any(t.split()[-1] == q["param"] and v_eval.res_tag(t) for t in r["unit"]["tags"]))
        else:
            continue
        ok = abs(round(pred, 2) - q["ans"]) <= 0.02 * q["ans"]
        C[(q["fam"], "outer_only_ok")] += ok
        C[(q["fam"], "n")] += 1
        asked_rel.append((abs(pred - q["ans"]) / q["ans"], q["fam"], s[:24], q["param"]))
    # DXF ROOM_OUTLINE variants
    doc = ezdxf.readfile(f"{v_dxf.D}/{s}.dxf")
    for e in doc.modelspace():
        if e.dxf.layer != "ROOM_OUTLINE": continue
        kind = (e.dxftype(), int(e.dxf.get("flags", -1)) if e.dxftype() == "LWPOLYLINE" else None, e.dxf.get("linetype", "BYLAYER"),
                len(e) if e.dxftype() == "LWPOLYLINE" else None)
        if kind[2] == "DASHED" or kind[1] == 0:
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            # where is it: inside which room polygon (by midpoint of first segment)?
            mid = Point((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2) if len(pts) > 1 else Point(pts[0])
            host = [r for r in X["rooms"] if r["poly"] is not None and r["poly"].buffer(1e-3).contains(mid)]
            hl = min(host, key=lambda r: r["poly"].area)["label"] if host else "NONE"
            C[("variant", kind[0], kind[1], kind[2], "nverts=%s" % (kind[3] if kind[3] in (2, 3, 4, 5) else ">5"))] += 1
            C[("variant_host", kind[2], hl)] += 1
asked_rel.sort(reverse=True)
for k in sorted(C, key=str): print(k, C[k])
print("worst asked rel err with outer-only:", [(round(a, 4), f, s, p) for a, f, s, p in asked_rel[:8]])

# DXF-side verification: door/window record counts, room attribute richness, DXF-only answers, PDF<->DXF agreement.
import sys, os, collections, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_dxf, v_parse, v_local, v_eval, v_pdf
import ezdxf
from shapely.geometry import Point
import pandas as pd

OUT = v_eval.OUT_LABELS
stems = sys.argv[1:] or v_local.stems("pdf", "dxf")
qs = [q for q in v_parse.load() if q["lang"] == "en" and q["stem"] in set(stems)]
gold = {(q["stem"], q["fam"], json.dumps(q["param"], ensure_ascii=False)): q["ans"] for q in qs}
rows, agree, attr = [], collections.Counter(), collections.Counter()
for s in stems:
    X = v_dxf.load(s)
    # --- ROOM_OUTLINE attribute richness: any per-entity attribute that could encode category?
    doc = ezdxf.readfile(f"{v_dxf.D}/{s}.dxf")
    for e in doc.modelspace():
        if e.dxf.layer == "ROOM_OUTLINE":
            a = e.dxf.all_existing_dxf_attribs()
            a.pop("handle", None); a.pop("owner", None)
            attr[(json.dumps(a, sort_keys=True, default=str), bool(e.xdata) if hasattr(e, "xdata") else None, e.has_extension_dict)] += 1
    hatch_layers = collections.Counter(e.dxf.layer for e in doc.modelspace() if e.dxftype() == "HATCH")
    attr[("hatch_layers", json.dumps(dict(hatch_layers)))] += 1
    # --- door / window counts
    g = lambda fam, p=None: gold.get((s, fam, json.dumps(p, ensure_ascii=False)))
    fk = collections.Counter(v_dxf.key(p) for p in X["door_frames"])
    wk = collections.Counter(v_dxf.key(p) for p in X["win_rects"])
    ak = collections.Counter((round(a.dxf.center[0], 3), round(a.dxf.center[1], 3), round(a.dxf.radius, 3)) for a in X["door_arcs"])
    rows.append(dict(stem=s, gold_doors=g("count_doors"), frames=len(X["door_frames"]), frames_distinct=len(fk), arcs=len(X["door_arcs"]),
                     arcs_distinct=len(ak), dup_frame_groups=sum(v > 1 for v in fk.values()), max_mult=max(fk.values()) if fk else 0,
                     gold_windows=g("count_windows"), win=len(X["win_rects"]), win_distinct=len(wk)))
    # --- DXF-only answers for area families (outdoor by label dictionary)
    rooms = X["rooms"]
    for r in rooms:
        r["unit"] = None
        if r["poly"] is None: continue
        cont = [u for u in X["units"] if u["poly"].intersection(r["poly"]).area > 0.5 * r["poly"].area]
        r["unit"] = min(cont, key=lambda u: u["poly"].area) if cont else None
    for q in [q for q in qs if q["stem"] == s]:
        fam, p = q["fam"], q["param"]
        pred = None
        if fam == "area_room":
            rr = [r for r in rooms if r["num"] == p[0]]; pred = round(rr[0]["net"], 2) if rr and rr[0]["net"] else None
        elif fam == "area_label_total":
            pred = round(sum(r["net"] for r in rooms if r["label"] == p and r["net"]), 2)
        elif fam == "area_apartment":
            pred = round(sum(r["net"] for r in rooms if r["unit"] and any(t.split()[-1] == p and v_eval.res_tag(t) for t in r["unit"]["tags"]) and r["label"] not in OUT), 2)
        elif fam == "area_total_indoor":
            pred = round(sum(r["net"] for r in rooms if r["net"] and r["label"] not in OUT), 2)
        elif fam == "count_label":
            pred = sum(r["label"] == p for r in rooms)
        elif fam == "count_apartments":
            pred = sum(v_eval.res_tag(t["t"]) for t in X["tags"])
        elif fam == "count_doors": pred = len(X["door_frames"])
        elif fam == "count_windows": pred = len(X["win_rects"])
        else: continue
        agree[("dxf_only", fam, v_eval.ok(fam, pred, q["ans"]))] += 1
    # --- PDF vs DXF room agreement
    Pm = v_pdf.load(s)
    pr = {r["num"]: r for r in Pm["rooms"]}; xr = {r["num"]: r for r in rooms}
    agree[("same_room_number_set", set(pr) == set(xr))] += 1
    for n in set(pr) & set(xr):
        a, b = pr[n], xr[n]
        agree[("label_equal", a["label"] == b["label"])] += 1
        agree[("printed_equal", a["printed"] == b["printed"])] += 1
        if a["net"] is not None and b["net"] is not None:
            d = abs(a["net"] - b["net"])
            agree[("net_diff_lt_0.005m2", d < 0.005)] += 1
            agree[("net_rel_diff_lt_0.1pct", d <= 0.001 * max(b["net"], 1e-9))] += 1
df = pd.DataFrame(rows)
df.to_csv(f"dxf_doors_windows_{len(stems)}files.csv", index=False)
print("files", len(stems))
for c in ["frames", "frames_distinct", "arcs", "arcs_distinct"]: print(f"doors gold == {c}: {(df[c] == df.gold_doors).sum()}/{len(df)}")
for c in ["win", "win_distinct"]: print(f"windows gold == {c}: {(df[c] == df.gold_windows).sum()}/{len(df)}")
print("door records", df.frames.sum(), "distinct positions", df.frames_distinct.sum(), "files with dup", (df.dup_frame_groups > 0).sum(), "max multiplicity", df.max_mult.max())
print("window records", df.win.sum(), "distinct", df.win_distinct.sum())
for k, v in sorted(agree.items(), key=str): print(v, k)
print("ROOM_OUTLINE attribute variety:")
for k, v in attr.most_common(12): print(" ", v, k)

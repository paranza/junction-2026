import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Check SVG data-guid -> IFC GlobalId links, storey agreement, and the SVG(mm) -> PDF(pt) transform using space polygons.
import re, pickle, pandas as pd, numpy as np, pymupdf, shapely.geometry as sg
import xml.etree.ElementTree as ET
DS = _DATA + "/data/ifc_models/"
NS = "{http://www.w3.org/2000/svg}"
def svg_polys(fn):
    root = ET.parse(DS + fn).getroot(); vb = [float(v) for v in root.get("viewBox").split()]
    out = []
    for g in root.iter(NS + "g"):
        if g.get("class") != "IfcSpace": continue
        for pth in g.iter(NS + "path"):
            pts = [tuple(map(float, xy.split(","))) for xy in re.findall(r"[-\d.]+,[-\d.]+", pth.get("d"))]
            out.append((g.get("data-guid"), g.get("data-name"), sg.Polygon(pts)))
    return vb, out
for model, plan, storey in [("bsc-molio_molio-with-uris", "bsc-molio_molio-with-uris_plan-02-klder", "Kælder"), ("bsc-esplanades_1807-ep-ar-v18", "bsc-esplanades_1807-ep-ar-v18_plan-04-4-korrus", "4.korrus")]:
    E = pd.DataFrame(pickle.load(open(f"facts_{model}.pkl", "rb"))["els"]).set_index("gid")
    vb, polys = svg_polys(plan + ".svg")
    gids = [g for g, n, p in polys]
    found = [g in E.index for g in gids]
    st = E.loc[[g for g in gids if g in E.index], "storey"].value_counts().to_dict()
    # area check: SVG mm^2 on paper at 1:100 -> m^2 = mm^2 * 0.01 ; compare with qto/geometry floor area by GUID
    ref = pd.to_numeric(E.get("BaseQuantities.NetFloorArea"), errors="coerce") if "BaseQuantities.NetFloorArea" in E else E.g_bottom_minz
    ref = ref.fillna(E.g_bottom_minz)
    rel = [abs(p.area * 0.01 - ref[g]) / ref[g] for g, n, p in polys]
    print(plan, "| SVG spaces:", len(polys), "| GUIDs found in IFC:", sum(found), "| storeys:", st, "| max rel area err SVG vs IFC: %.4f" % max(rel))
    # transform check: PDF pt = (svg - vb_origin) * 72/25.4 ; compare bounds of the largest space
    page = pymupdf.open(DS + plan + ".pdf")[0]
    g, n, p = max(polys, key=lambda t: t[2].area)
    x0, y0, x1, y1 = p.bounds; k = 72 / 25.4
    pred = ((x0 - vb[0]) * k, (y0 - vb[1]) * k, (x1 - vb[0]) * k, (y1 - vb[1]) * k)
    fills = [d["rect"] for d in page.get_drawings() if d.get("fill") and abs(d["fill"][0] - 0.89) < 0.005]
    best = min(fills, key=lambda r: sum(abs(a - b) for a, b in zip((r.x0, r.y0, r.x1, r.y1), pred)))
    print("   largest space", n, "pred PDF bbox", [round(v, 1) for v in pred], "nearest PDF fill bbox", [round(v, 1) for v in (best.x0, best.y0, best.x1, best.y1)])

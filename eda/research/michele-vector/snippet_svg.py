# S7: IfcConvert-style SVG -> {GlobalId: (ifc_class, name, shapely geometry in PDF points)}; uses stdlib + shapely only.
import re, sys, xml.etree.ElementTree as ET
import pymupdf, shapely
from shapely.geometry import Polygon, LineString
NS = "{http://www.w3.org/2000/svg}"

def svg_elements(svg_path, page_rect=None):
    root = ET.parse(svg_path).getroot()
    vx, vy, vw, vh = map(float, root.get("viewBox").split())
    sx = sy = 1.0
    if page_rect is not None:  # map SVG user units to the twin PDF page (same drawing, different units)
        sx, sy = page_rect.width / vw, page_rect.height / vh
    out = {}
    for g in root.iter(NS + "g"):
        guid = g.get("data-guid")
        if not guid: continue
        geoms = []
        for p in g.iter(NS + "path"):
            for sub in re.split(r"(?=M)", p.get("d", "")):  # one subpath per M; IfcConvert writes straight M/L segments
                pts = [((float(x) - vx) * sx, (float(y) - vy) * sy) for x, y in re.findall(r"(-?[\d.eE+-]+),(-?[\d.eE+-]+)", sub)]
                if len(pts) >= 3 and pts[0] == pts[-1] or len(pts) >= 4 and shapely.Point(pts[0]).distance(shapely.Point(pts[-1])) < 1e-6 * max(vw, vh):
                    geoms.append(shapely.make_valid(Polygon(pts)))
                elif len(pts) >= 2:
                    geoms.append(LineString(pts))
        out[guid] = (g.get("class"), g.get("data-name"), shapely.union_all(geoms) if geoms else None)
    return out

if __name__ == "__main__":
    svg, pdf = sys.argv[1], sys.argv[2]
    page = pymupdf.open(pdf)[0]
    root = ET.parse(svg).getroot()
    print("svg width/height", root.get("width"), root.get("height"), "viewBox", root.get("viewBox"))
    print("pdf page.rect", page.rect, "-> mm", page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72)
    els = svg_elements(svg, page.rect)
    from collections import Counter
    print(Counter(c for c, n, g in els.values()))
    # sanity: does an IfcSpace polygon in PDF coords contain the PDF text of its name?
    ok = tot = 0
    for guid, (cls, name, geom) in els.items():
        if cls != "IfcSpace" or geom is None or not name: continue
        hits = page.search_for(name)
        if not hits: continue
        tot += 1
        ok += any(geom.buffer(1).contains(shapely.Point((h.x0 + h.x1) / 2, (h.y0 + h.y1) / 2)) for h in hits)
    print(f"space labels found inside their own SVG polygon: {ok}/{tot}")

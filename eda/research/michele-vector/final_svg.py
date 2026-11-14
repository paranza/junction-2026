import math, re, xml.etree.ElementTree as ET
import shapely
from shapely.geometry import Polygon, LineString

def svg_elements(svg_path, page_rect=None):
    """IfcConvert SVG -> {GlobalId: (ifc_class, name, geometry)}; with page_rect, geometry is in the twin PDF's points."""
    ns = {"svg": "http://www.w3.org/2000/svg"}
    root = ET.parse(svg_path).getroot()
    vx, vy, vw, vh = map(float, root.get("viewBox").split())
    sx, sy = (page_rect.width / vw, page_rect.height / vh) if page_rect is not None else (1.0, 1.0)
    out = {}
    for g in root.iterfind(".//svg:g[@data-guid]", ns):
        geoms = []
        for p in g.iterfind(".//svg:path", ns):
            for sub in re.split(r"(?=M)", p.get("d", "")):  # IfcConvert writes straight M/L segments
                pts = [((float(x) - vx) * sx, (float(y) - vy) * sy) for x, y in re.findall(r"(-?[\d.eE+-]+),(-?[\d.eE+-]+)", sub)]
                closed = sub.rstrip().endswith(("Z", "z")) or (len(pts) >= 4 and math.dist(pts[0], pts[-1]) < 1e-6 * max(vw, vh))
                if closed and len(pts) >= 3: geoms.append(shapely.make_valid(Polygon(pts)))
                elif len(pts) >= 2: geoms.append(LineString(pts))
        out[g.get("data-guid")] = (g.get("class"), g.get("data-name"), shapely.union_all(geoms) if geoms else None)
    return out

import sys
sys.path.insert(0, sys.argv[1])
import pymupdf
from final_svg import svg_elements
from final_dxf import dxf_summary
svg, pdf, dxf = sys.argv[2], sys.argv[3], sys.argv[4]
page = pymupdf.open(pdf)[0]
els = svg_elements(svg, page.rect)
import shapely
ok = tot = 0
for guid, (cls, name, geom) in els.items():
    if cls == "IfcSpace" and geom is not None and name and (hits := page.search_for(name)):
        tot += 1; ok += any(geom.buffer(1).contains(shapely.Point((h.x0 + h.x1) / 2, (h.y0 + h.y1) / 2)) for h in hits)
print("svg elements", len(els), "space labels inside own polygon", ok, "/", tot); assert ok == tot > 0
s = dxf_summary(dxf)
print("to_m", s["to_m"], "blocks", dict(s["blocks"]), "hatch area m2", s["hatches"][0].area * s["to_m"] ** 2, "texts", s["texts"])
assert s["blocks"]["DOOR_900"] == 3 and abs(s["hatches"][0].area * s["to_m"] ** 2 - 59) < 1e-9
print("FINAL SVG+DXF CHECKS PASSED")

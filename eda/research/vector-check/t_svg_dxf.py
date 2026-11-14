import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from snips import svg_elements, dxf_summary
import pymupdf
FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fx")
print("G on ifcopenshell.draw output (ifc: namespace attrs):", len(svg_elements(f"{FX}/syn.svg")), "elements")
els = svg_elements(f"{FX}/syn_data.svg")
for k, (c, n, geom) in els.items(): print("G", c, n, geom.geom_type if geom else None, "area_mm2=", round(geom.area, 2) if geom else None)
# page scaling: A3 page in points
els_pt = svg_elements(f"{FX}/syn_data.svg", pymupdf.Rect(0, 0, 297 * 72 / 25.4, 420 * 72 / 25.4))
w0 = [g for c, n, g in els_pt.values() if n == "W0"][0]
print("G W0 area in pt2 -> m2 at 1:100:", round(w0.area * (100 * 0.0254 / 72) ** 2, 4), "(expected 1.0 = 5 m x 0.2 m)")
# H) DXF
import ezdxf
d = ezdxf.new("R2013"); d.units = ezdxf.units.M; msp = d.modelspace()
msp.add_lwpolyline([(0, 0), (4, 0), (4, 3), (0, 3)], close=True, dxfattribs={"layer": "ROOM_OUTLINE"})
msp.add_lwpolyline([(5, 0), (8, 0), (8, 2), (5, 2), (5, 0)], close=False, dxfattribs={"layer": "ROOM_OUTLINE"})  # geometrically closed, flag unset
h = msp.add_hatch(dxfattribs={"layer": "WALL"})
h.paths.add_polyline_path([(0, 0), (10, 0), (10, 6), (0, 6)], is_closed=True, flags=ezdxf.const.BOUNDARY_PATH_EXTERNAL)
h.paths.add_polyline_path([(4, 2), (5, 2), (5, 3), (4, 3)], is_closed=True, flags=ezdxf.const.BOUNDARY_PATH_OUTERMOST)
msp.add_text("MH", dxfattribs={"layer": "ROOM_TEXT", "insert": (1, 1)})
msp.add_mtext("KH\\P12.0 m²", dxfattribs={"layer": "ROOM_TEXT", "insert": (6, 1)})
door = d.blocks.new("DOOR"); door.add_line((0, 0), (0.9, 0))
pair = d.blocks.new("PAIR"); pair.add_blockref("DOOR", (0, 0)); pair.add_blockref("DOOR", (2, 0))
msp.add_blockref("DOOR", (1, 0)); msp.add_blockref("PAIR", (5, 6))
mi = msp.add_blockref("DOOR", (0, 10)); mi.grid(size=(2, 3), spacing=(1, 1))  # MINSERT 2x3 = 6 doors
d.saveas(f"{FX}/h.dxf")
r = dxf_summary(f"{FX}/h.dxf")
print("H to_m", r["to_m"], "room areas", r["room_areas_m2"], "hatch areas", [round(x.area, 4) for x in r["hatches"]], "texts", r["texts"], "blocks", dict(r["blocks"]))
print("H per_layer", dict(r["per_layer"]))
e = list(msp.query('LWPOLYLINE[layer=="ROOM_OUTLINE"]'))[1]
pts = e.get_points("xy"); print("H open-flag polyline first==last:", pts[0] == pts[-1], "closed flag:", e.closed)

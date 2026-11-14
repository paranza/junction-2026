# Build synthetic test files (no dataset content): a Matplotlib vector PDF plan, a schedule-table PDF, a DXF.
import sys, matplotlib
matplotlib.use("pdf")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle
out = sys.argv[1]
# 1) Plan: 10 m x 6 m room with a 1 m x 1 m hole (column), drawn at 1:100 on A4 landscape.
fig = plt.figure(figsize=(11.69, 8.27))  # inches, A4 landscape
mm = 1 / 25.4
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 297); ax.set_ylim(0, 210); ax.axis("off")  # 1 data unit = 1 mm on paper
def ring(x0, y0, w, h, ccw=True):
    pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
    return pts if ccw else pts[::-1]
# 1:100 -> 10 m = 100 mm on paper
outer, hole = ring(50, 50, 100, 60), ring(90, 70, 10, 10, ccw=False)
verts = outer + [outer[0]] + hole + [hole[0]]
codes = [Path.MOVETO] + [Path.LINETO] * 3 + [Path.CLOSEPOLY] + [Path.MOVETO] + [Path.LINETO] * 3 + [Path.CLOSEPOLY]
ax.add_patch(PathPatch(Path(verts, codes), facecolor="#d9ead3", edgecolor="none"))
ax.add_patch(Rectangle((170, 50), 40, 30, facecolor="#fce5cd", edgecolor="black", lw=0.5))  # 4 m x 3 m = 12 m2
ax.text(100, 100, "Living", fontsize=9, fontweight="bold")
ax.text(175, 60, "Bath", fontsize=9)
ax.text(230, 60, "rotated label", fontsize=8, rotation=90)
ax.text(220, 20, "Scale 1:100", fontsize=8)
fig.savefig(f"{out}/plan.pdf"); plt.close(fig)
# 2) Schedule table with ruled grid, via PyMuPDF.
import pymupdf
doc = pymupdf.open(); page = doc.new_page(width=842, height=595)
rows = [["MARK", "WIDTH", "HEIGHT", "TYPE"], ["D101", "3'-0\"", "7'-0\"", "A"], ["D102", "2'-8\"", "7'-0\"", "B"], ["D103", "3'-0\"", "7'-0\"", "A"]]
x0, y0, cw, rh = 100, 100, 90, 22
for i, r in enumerate(rows):
    for j, t in enumerate(r):
        rect = pymupdf.Rect(x0 + j * cw, y0 + i * rh, x0 + (j + 1) * cw, y0 + (i + 1) * rh)
        page.draw_rect(rect, color=(0, 0, 0), width=0.7)
        page.insert_text(rect.bl + (4, -6), t, fontsize=10, fontname="hebo" if i == 0 else "helv")
page.insert_text((100, 90), "DOOR SCHEDULE", fontsize=12, fontname="hebo")
doc.save(f"{out}/schedule.pdf")
# 3) DXF with units, layers, LWPOLYLINE, HATCH with hole, TEXT, MTEXT, nested INSERTs.
import ezdxf
d = ezdxf.new("R2018", setup=True); d.units = ezdxf.units.MM
msp = d.modelspace()
d.layers.add("A-WALL"); d.layers.add("A-AREA"); d.layers.add("A-DOOR")
msp.add_lwpolyline([(0, 0), (10000, 0), (10000, 6000), (0, 6000)], close=True, dxfattribs={"layer": "A-WALL"})
h = msp.add_hatch(color=3, dxfattribs={"layer": "A-AREA"})
h.paths.add_polyline_path([(0, 0), (10000, 0), (10000, 6000), (0, 6000)], is_closed=True, flags=ezdxf.const.BOUNDARY_PATH_EXTERNAL)
h.paths.add_polyline_path([(4000, 2000), (5000, 2000), (5000, 3000), (4000, 3000)], is_closed=True, flags=ezdxf.const.BOUNDARY_PATH_OUTERMOST)
msp.add_text("LIVING", height=250, dxfattribs={"layer": "A-AREA"}).set_placement((4500, 4000))
msp.add_mtext("ROOM 2\\PBEDROOM", dxfattribs={"layer": "A-AREA", "char_height": 200, "insert": (8000, 1000)})
door = d.blocks.new("DOOR_900"); door.add_line((0, 0), (900, 0)); door.add_arc((0, 0), 900, 0, 90)
pair = d.blocks.new("DOOR_PAIR"); pair.add_blockref("DOOR_900", (0, 0)); pair.add_blockref("DOOR_900", (2000, 0))
msp.add_blockref("DOOR_900", (1000, 0), dxfattribs={"layer": "A-DOOR"})
msp.add_blockref("DOOR_PAIR", (5000, 6000), dxfattribs={"layer": "A-DOOR"})
d.saveas(f"{out}/plan.dxf")
print("ok")

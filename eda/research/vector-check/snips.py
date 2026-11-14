# Snippets copied verbatim from the reading list under review.
import pymupdf

def words_with_bold(page):
    """Words with bbox, bold flag, size, font and writing direction (rawdict gives per-char bboxes)."""
    out = []
    for b in page.get_text("rawdict")["blocks"]:
        for l in b.get("lines", []):  # image blocks have no "lines"
            for s in l["spans"]:
                # Matplotlib Type 3 fonts report flags=0 even for bold, so also check the font name
                bold = bool(s["flags"] & pymupdf.TEXT_FONT_BOLD) or "bold" in s["font"].lower()
                word, box = "", pymupdf.EMPTY_RECT()
                for ch in s["chars"] + [{"c": " "}]:  # sentinel flushes the last word
                    if ch["c"].isspace():
                        if word:
                            out.append(dict(text=word, bbox=tuple(box), bold=bold, size=s["size"], font=s["font"], dir=l["dir"]))
                        word, box = "", pymupdf.EMPTY_RECT()
                    else:
                        word += ch["c"]; box |= ch["bbox"]
    return out

import functools
import pymupdf, shapely
from shapely.geometry import Polygon

def subpaths(items):
    """Split a get_drawings() items list into closed point rings; a gap between items starts a new subpath."""
    rings, cur = [], []
    for it in items:
        if it[0] == "re":
            rings.append([tuple(p) for p in (it[1].tl, it[1].tr, it[1].br, it[1].bl)]); continue
        if it[0] == "qu":
            q = it[1]; rings.append([tuple(p) for p in (q.ul, q.ur, q.lr, q.ll)]); continue
        p0, p1 = it[1], it[-1]  # "l": (p1, p2); "c": (p1, c1, c2, p2). shortcut: Bezier curves become chords, flatten them if rooms have arcs
        if cur and (abs(cur[-1][0] - p0.x) > 1e-3 or abs(cur[-1][1] - p0.y) > 1e-3):
            rings.append(cur); cur = []
        if not cur: cur = [tuple(p0)]
        cur.append(tuple(p1))
    if cur: rings.append(cur)
    return [r for r in rings if len(r) >= 3]

def fill_polygons(page, rgb, tol=0.01):
    """Union of all filled paths whose fill colour matches rgb (0..1 floats). Holes: XOR of subpath rings."""
    polys = []
    for p in page.get_drawings():
        f = p.get("fill")
        if f and all(abs(a - b) <= tol for a, b in zip(f, rgb)):
            rings = [shapely.make_valid(Polygon(r)) for r in subpaths(p["items"])]
            if rings: polys.append(functools.reduce(lambda a, b: a.symmetric_difference(b), rings))
    return shapely.union_all(polys) if polys else Polygon()  # for COUNTS keep polys per path instead: duplicate records count

import re

def m_per_pt(page):
    """'1:100' in the page text -> metres per PDF point (1 pt = 1/72 inch on paper)."""
    m = re.search(r"\b1\s*:\s*(\d+)\b", page.get_text())
    if not m: return None
    return int(m.group(1)) * 0.0254 / 72

def schedule_tables(page, title="SCHEDULE"):
    if page.rotation:
        page.remove_rotation()                 # in memory only: text becomes horizontal, coords match what a human sees
    paths = page.get_drawings()                # extract vector graphics once, reuse for every clip
    out = []
    for hit in page.search_for(title):         # ASCII case-insensitive; schedule titles sit above or below the grid
        clip = pymupdf.Rect(hit.x0 - 400, hit.y0 - 400, hit.x0 + 600, hit.y0 + 400) & page.rect
        for t in page.find_tables(clip=clip, paths=paths, use_layout=False).tables:  # default use_layout=True: ~40 s, 0 tables on a real sheet
            cells = [[page.get_text("text", clip=c).strip() if c else None for c in row.cells] for row in t.rows]  # robust per-cell text
            out.append((tuple(t.bbox), t.to_pandas(), cells))
    return out

def evidence_png(page, boxes, path, pad=24, dpi=200):
    boxes = [pymupdf.Rect(b) for b in boxes]
    area = pymupdf.Rect(boxes[0])
    for b in boxes[1:]: area |= b
    annots = []
    for b in boxes:  # annotations take unrotated coords, like get_text/search_for/get_drawings return
        a = page.add_rect_annot(b); a.set_colors(stroke=(1, 0, 0)); a.set_border(width=1.5); a.update(); annots.append(a)
    clip = ((area + (-pad, -pad, pad, pad)) * page.rotation_matrix) & page.rect  # get_pixmap clip is in rotated coords
    pix = page.get_pixmap(clip=clip, dpi=dpi)
    for a in annots: page.delete_annot(a)  # leave the page as found
    pix.save(path)
    return pix

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

from collections import Counter
import ezdxf
from ezdxf import units
from ezdxf.addons import geo
from shapely.geometry import shape, Polygon

def dxf_summary(path):
    doc = ezdxf.readfile(path)                      # damaged files: doc, auditor = ezdxf.recover.readfile(path)
    msp = doc.modelspace()
    k = units.conversion_factor(doc.units, units.M) if doc.units else None   # $INSUNITS 0 = unitless: decide scale yourself
    per_layer = Counter((e.dxftype(), e.dxf.layer) for e in msp)
    rooms = [Polygon(e.get_points("xy")) for e in msp.query('LWPOLYLINE[layer=="ROOM_OUTLINE"]') if e.closed]  # shortcut: bulges ignored; use ezdxf.path.make_path(e).flattening(0.001) if any bulge != 0
    hatches = [shape(geo.proxy(h)) for h in msp.query("HATCH")]          # holes kept via __geo_interface__
    texts = [(e.dxf.text, tuple(e.dxf.insert)[:2]) for e in msp.query("TEXT")] + \
            [(e.plain_text(), tuple(e.dxf.insert)[:2]) for e in msp.query("MTEXT")]

    def count_inserts(layout, c):
        for ins in layout.query("INSERT"):          # MINSERT grids: multiply by ins.mcount
            c[ins.dxf.name] += 1
            count_inserts(doc.blocks[ins.dxf.name], c)   # nested blocks
        return c
    return dict(to_m=k, per_layer=per_layer, room_areas_m2=[p.area * k * k for p in rooms] if k else None,
                hatches=hatches, texts=texts, blocks=count_inserts(msp, Counter()))

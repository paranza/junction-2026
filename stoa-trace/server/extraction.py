"""Native construction-document extraction. This module never reads QA labels.

Pages are 1-based. All 2D boxes/polygons use normalized, top-left page
coordinates. IFC objects without an available 2D projection have no bbox.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        # Uploaded files live outside the dataset root. The API's evidence-path
        # resolver validates this absolute path against its allowed upload root.
        return str(path.resolve())


def _uid(path: Path, root: Path) -> str:
    return hashlib.sha1(relative_path(path, root).encode()).hexdigest()[:12]


def _box(box, width, height):
    return [round(max(0, min(1, float(v) / (width if i % 2 == 0 else height))), 6)
            for i, v in enumerate(box)]


def _bbox(points):
    if not points:
        return None
    return [min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)]


def _safe(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_safe(v) for v in value]
    return str(value)


def _empty(path, root):
    return {"format": path.suffix.lower().lstrip("."), "page_count": 0,
            "pages": [], "objects": [], "metadata": {
                "source_path": relative_path(path, root),
                "coordinate_system": "normalized_top_left", "extraction_version": 1},
            "warnings": []}


def linked_model(path: Path) -> Path | None:
    """Only exact same-drawing and explicit renderer-name links, never revisions."""
    candidate = path.with_suffix(".ifc")
    if candidate.exists():
        return candidate
    if "_plan-" in path.stem:
        candidate = path.with_name(path.stem.split("_plan-", 1)[0] + ".ifc")
        if candidate.exists():
            return candidate
    return None


def _pdf(path, root):
    import fitz
    result = _empty(path, root)
    prefix = _uid(path, root)
    fill_regions = {}
    with fitz.open(path) as pdf:
        result["page_count"] = len(pdf)
        result["metadata"].update({"pdf_metadata": _safe(pdf.metadata), "tables": []})
        for index, page in enumerate(pdf):
            source_rotation = page.rotation
            if source_rotation:
                # Rewrite the in-memory page transform, preserving appearance.
                # Extraction then matches the default rendered source image.
                page.remove_rotation()
            rect = page.cropbox
            width, height = rect.width, rect.height
            words = [{"text": word[4], "bbox": _box(word[:4], width, height),
                      "block": word[5], "line": word[6]} for word in page.get_text("words")]
            item = {"page": index + 1, "width": width, "height": height,
                    "rotation": page.rotation, "source_rotation": source_rotation,
                    "text": page.get_text("text"), "words": words}
            try:
                drawings = page.get_drawings()
                fills = _room_fill_regions(drawings, width, height)
                if fills:
                    fill_regions[index + 1] = fills
                if "schedule" in item["text"].casefold():
                    result["metadata"].setdefault("schedule_tables", []).extend(
                        _ruled_schedules(page, drawings, index + 1, width, height, prefix))
                item["vector_count"] = len(drawings)
                item["vectors"] = [{"bbox": _box(d["rect"], width, height),
                                    "type": d.get("type", "path")}
                                   for d in drawings[:5000]]
            except Exception:
                item["vector_count"] = 0
            if not words:
                result["warnings"].append(f"Page {index+1} has no native text; OCR or vision is required.")
            # Native table extraction retains cell/row boxes for inspectable counts.
            if ("schedule" in item["text"].casefold()
                    and not any(re.fullmatch(r"\d{2,4}\.[A-Z]\d?", w["text"]) for w in words)):
                try:
                    tables = page.find_tables(strategy="lines_strict")
                    for ti, table in enumerate(tables.tables):
                        rows = table.extract()
                        record = {"page": index + 1, "bbox": _box(table.bbox, width, height), "rows": []}
                        for ri, values in enumerate(rows):
                            cells = table.rows[ri].cells
                            cell_boxes = [list(c) for c in cells if c]
                            bounds = [min(c[0] for c in cell_boxes), min(c[1] for c in cell_boxes),
                                      max(c[2] for c in cell_boxes), max(c[3] for c in cell_boxes)] if cell_boxes else list(table.bbox)
                            record["rows"].append({"id": f"{prefix}:p{index+1}:t{ti}:r{ri}",
                                                   "values": values, "bbox": _box(bounds, width, height)})
                        result["metadata"]["tables"].append(record)
                except Exception:
                    result["warnings"].append(f"Native table extraction unavailable on page {index+1}; text remains available.")
            result["pages"].append(item)
    result["objects"].extend(_word_schedules(result, prefix))
    # A same-name semantic SVG provides exact IFC GUID projections without 3D.
    sibling = path.with_suffix(".svg")
    if sibling.exists():
        try:
            svg = _svg(sibling, root)
            for obj in svg["objects"]:
                obj["properties"]["native_source_path"] = relative_path(sibling, root)
                obj["source_path"] = relative_path(path, root)
            result["objects"].extend(svg["objects"])
            result["metadata"]["semantic_svg"] = relative_path(sibling, root)
        except Exception:
            result["warnings"].append("Linked SVG could not be parsed.")
    sibling = path.with_suffix(".dxf")
    if sibling.exists():
        try:
            cad = _dxf(sibling, root)
            projected = _project_dxf_to_pdf(cad, result)
            _apply_fill_categories(projected, result, fill_regions.get(1, []))
            result["objects"].extend(projected)
            result["metadata"]["semantic_dxf"] = relative_path(sibling, root)
            result["metadata"]["dxf_layers"] = cad["metadata"].get("layers", {})
            result["metadata"]["cad_extents"] = cad["metadata"].get("cad_extents")
            result["metadata"]["cad_projection_registered"] = bool(projected) and all(o.get("bbox") for o in projected)
            result["metadata"]["cad_projection_method"] = "matching native room-number anchors"
            result["metadata"]["semantic_inventory"] = cad["metadata"].get("semantic_inventory", {})
            result["warnings"].extend(cad["warnings"])
        except Exception as exc:
            result["warnings"].append(f"Linked DXF extraction unavailable ({type(exc).__name__}).")
    model = linked_model(path)
    if model:
        result["metadata"]["linked_model"] = relative_path(model, root)
    return result


# Swiss sheet room fills (stroke grey 0.541) encode the room category; learned by
# registering DXF rooms onto PDF paths in the EDA (eda/swiss_dwellings/pdf_solver.py).
_FILL_CATEGORY = {(1.0, 1.0, 1.0): "room", (0.894, 0.894, 0.894): "outdoor",
                  (0.953, 0.953, 0.953): "common", (0.812, 0.812, 0.812): "shaft_or_void"}


def _ruled_schedules(page, drawings, page_number, width, height, prefix):
    """Ruled schedule grids on a page, with header names and normalized row boxes."""
    from .schedules import find_tables, split_header
    out = []
    try:
        tables = find_tables(page, drawings)
    except Exception:
        return out
    for ti, table in enumerate(tables):
        header, body = split_header(table["rows"], table.get("header_above"))
        rows = []
        for ri, row in enumerate(body):
            x0 = min(c["bbox"][0] for c in row); y0 = min(c["bbox"][1] for c in row)
            x1 = max(c["bbox"][2] for c in row); y1 = max(c["bbox"][3] for c in row)
            rows.append({"id": f"{prefix}:p{page_number}:s{ti}:r{ri}", "cells": [c["text"] for c in row],
                         "bbox": _box((x0, y0, x1, y1), width, height)})
        out.append({"page": page_number, "title": table["title"], "header": header,
                    "touches_below": table.get("touches_below", False),
                    "bbox": _box(table["bbox"], width, height), "rows": rows})
    return out


def _room_fill_regions(drawings, width, height):
    """Closed filled room paths with their category, in normalized page coordinates."""
    from shapely.geometry import Polygon
    out = []
    for d in drawings:
        color, fill = d.get("color"), d.get("fill")
        if d.get("type") != "fs" or not color or not fill:
            continue
        if tuple(round(v, 3) for v in color) != (0.541, 0.541, 0.541):
            continue
        category = _FILL_CATEGORY.get(tuple(round(v, 3) for v in fill))
        if category is None:
            continue
        points = []
        for it in d["items"]:
            if it[0] == "l":
                points += [it[1], it[2]]
            elif it[0] == "c":
                points += [it[1], it[4]]
            elif it[0] == "re":
                r = it[1]; points += [r.tl, r.tr, r.br, r.bl]
            elif it[0] == "qu":
                q = it[1]; points += [q.ul, q.ur, q.lr, q.ll]
        if len(points) >= 3:
            polygon = Polygon([(pt.x / width, pt.y / height) for pt in points]).buffer(0)
            if polygon.area > 0:
                out.append((polygon, category))
    return out


def _apply_fill_categories(objects, document, regions):
    """Mark projected rooms as shaft/void or outdoor from the sheet's room fill, located by
    the room's printed number. Keeps the basis on the record for inspection."""
    if not regions or not document.get("pages"):
        return
    from shapely.geometry import Point
    words = {}
    for w in document["pages"][0].get("words", []):
        words.setdefault(w["text"], []).append(w)
    for obj in objects:
        if obj.get("type") != "room":
            continue
        number = obj["properties"].get("room_number")
        found = words.get(number, []) if number else []
        if len(found) != 1:
            continue
        b = found[0]["bbox"]
        point = Point((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        covering = [(polygon.area, category) for polygon, category in regions if polygon.covers(point)]
        if not covering:
            continue
        category = min(covering)[1]
        obj["properties"]["sheet_fill_category"] = category
        obj["properties"]["spatial_kind_basis"] = "room fill colour on the paired PDF sheet"
        if category in ("shaft_or_void", "outdoor"):
            obj["properties"]["spatial_kind"] = category
        else:
            # The fill is authoritative: a stairwell's treads cross its outline but it is
            # a common indoor room, not a shaft.
            obj["properties"].pop("spatial_kind", None)


def _word_schedules(document, prefix):
    """Recover ruled schedules from aligned native words when table OCR fails.

    Header coordinates define column roles. IDs and row y positions define
    evidence; values are source text, not a hardcoded schedule or answer list.
    """
    objects = []
    for page in document["pages"]:
        if "schedule" not in page.get("text", "").casefold():
            continue
        words = page["words"]
        center = lambda w: ((w["bbox"][0]+w["bbox"][2])/2, (w["bbox"][1]+w["bbox"][3])/2)
        anchors = [w for w in words if re.fullmatch(r"\d{2,4}\.[A-Z]\d?", w["text"])]
        if anchors:
            # Use the repeated identifier column, excluding callouts elsewhere.
            from collections import Counter
            col = Counter(round(center(w)[0],2) for w in anchors).most_common(1)[0][0]
            anchors = [w for w in anchors if abs(center(w)[0]-col)<.015]
            top = min(w["bbox"][1] for w in anchors)
            headers = [w for w in words if top-.04 < center(w)[1] < top-.001
                       and col-.04 < center(w)[0] < col+.4]
            find = lambda text: sorted([w for w in headers if w["text"].casefold()==text],key=lambda w:center(w)[0])
            columns = [(col,"door_number")]
            for token, field in (("width","width"),("height","height"),("hardware","hardware_group"),("notes","notes"),("name","room_name")):
                found = find(token)
                if found:
                    columns.append((center(found[0])[0],field))
            found = find("number")
            if len(found)>=2:
                columns.append((center(found[1])[0],"room_number"))
            for token, fields in (("type",("door_type","frame_type")),("matl",("door_material","frame_material"))):
                for word,field in zip(find(token),fields):
                    columns.append((center(word)[0],field))
            columns.sort()
            right = columns[-1][0]+.025
            for row_index, anchor in enumerate(anchors):
                y = center(anchor)[1]
                tol = max(.0005,(anchor["bbox"][3]-anchor["bbox"][1])*.4)
                row = sorted([w for w in words if abs(center(w)[1]-y)<tol and col-.02<center(w)[0]<right],key=lambda w:center(w)[0])
                # Assign each word by the midpoint between column headers.
                props = {}
                for i,(x,field) in enumerate(columns):
                    left = (columns[i-1][0]+x)/2 if i else col-.025
                    edge = (x+columns[i+1][0])/2 if i+1<len(columns) else right
                    props[field] = " ".join(w["text"] for w in row if left<=center(w)[0]<edge)
                props["door_number"] = anchor["text"]
                props["cells"] = [props[field] for _,field in columns]
                props["count_basis"] = "one native schedule row per door identifier"
                bounds = [min(w["bbox"][0] for w in row),min(w["bbox"][1] for w in row),
                          max(w["bbox"][2] for w in row),max(w["bbox"][3] for w in row)]
                objects.append({"id":f"{prefix}:p{page['page']}:door:{anchor['text']}",
                                "type":"schedule_door", "label":"Door "+anchor["text"],
                                "page":page["page"], "bbox":bounds,
                                "source_path":document["metadata"]["source_path"], "properties":props})
        areas = [w for w in words if w["text"].casefold() in ("sf","ft²","ft2")]
        if areas:
            top = min(w["bbox"][1] for w in areas)
            headers = [w for w in words if top-.035<center(w)[1]<top-.001]
            find = lambda text: sorted([w for w in headers if w["text"].casefold()==text],key=lambda w:center(w)[0])
            number_headers, name_headers, floor_headers, base_headers = find("number"),find("name"),find("floor"),find("base")
            if not (number_headers and name_headers):
                continue
            nx,nm = center(number_headers[0])[0],center(name_headers[0])[0]
            fx = center(floor_headers[0])[0] if floor_headers else nm+.08
            bx = center(base_headers[0])[0] if base_headers else fx+.06
            for area_anchor in areas:
                y = center(area_anchor)[1]
                tol = max(.0005,(area_anchor["bbox"][3]-area_anchor["bbox"][1])*.4)
                row = sorted([w for w in words if abs(center(w)[1]-y)<tol],key=lambda w:center(w)[0])
                ids = [w for w in row if abs(center(w)[0]-nx)<.015 and re.fullmatch(r"\d{2,4}",w["text"])]
                values = [w for w in row if center(w)[0]<center(area_anchor)[0] and re.fullmatch(r"[\d,]+(?:\.\d+)?",w["text"])]
                if len(ids)!=1 or not values:
                    continue
                area = float(values[-1]["text"].replace(",",""))
                floor_words = [w for w in row if re.fullmatch(r"F\d+",w["text"]) and abs(center(w)[0]-fx)<.04]
                name_right = min(w["bbox"][0] for w in floor_words)-.002 if floor_words else (nm+fx)/2
                name = " ".join(w["text"] for w in row if ids[0]["bbox"][2]+.002<w["bbox"][0]<name_right)
                floor = " ".join(w["text"] for w in floor_words)
                base = next((w["text"] for w in row if re.fullmatch(r"B\d+",w["text"]) and abs(center(w)[0]-bx)<.02),"")
                selected = [w for w in row if center(values[-1])[0]-.01<center(w)[0]<bx+.02]
                bounds=[min(w["bbox"][0] for w in selected),min(w["bbox"][1] for w in selected),
                        max(w["bbox"][2] for w in selected),max(w["bbox"][3] for w in selected)]
                props={"room_number":ids[0]["text"],"room_name":name,"area_ft2":area,
                       "floor_finish":floor,"base_finish":base,"cells":[area,name,floor,base]}
                objects.append({"id":f"{prefix}:p{page['page']}:room:{ids[0]['text']}",
                                "type":"schedule_room","label":"Room "+ids[0]["text"]+" · "+name,
                                "page":page["page"],"bbox":bounds,"properties":props,
                                "source_path":document["metadata"]["source_path"]})
    return objects


def _image(path, root):
    from .rendering import raster_metadata
    result = _empty(path, root)
    pages, warnings = raster_metadata(path)
    result.update(page_count=len(pages), pages=pages)
    result["warnings"].extend(warnings)
    result["warnings"].append("Raster image: no native semantics. Object counts require visual detection and completeness review.")
    return result


def _svg_path_points(data):
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?", data)
    i, command, current, start = 0, None, (0., 0.), (0., 0.)
    points, polygonal = [], True
    arity = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
            if command.upper() == "Z":
                current = start
                points.append(current)
                continue
        if not command or command.upper() == "Z":
            break
        n = arity.get(command.upper(), 0)
        if not n or i + n > len(tokens) or any(t.isalpha() for t in tokens[i:i+n]):
            break
        values = list(map(float, tokens[i:i+n])); i += n
        rel, kind = command.islower(), command.upper()
        x, y = current
        if kind == "H":
            current = (values[0] + x if rel else values[0], y)
            points.append(current)
        elif kind == "V":
            current = (x, values[0] + y if rel else values[0])
            points.append(current)
        elif kind == "A":
            # Endpoint alone does not bound an arc accurately. Do not manufacture
            # a precise box for projected curved objects.
            polygonal = False
            current = (values[-2] + x if rel else values[-2], values[-1] + y if rel else values[-1])
            rx, ry = abs(values[0]), abs(values[1])
            # A deliberately conservative highlight envelope, never used for
            # measurements. Rotated ellipses fit inside the max-radius square.
            radius = max(rx, ry)
            points.extend([(x-radius,y-radius),(x+radius,y+radius),
                           (current[0]-radius,current[1]-radius),(current[0]+radius,current[1]+radius)])
        else:
            coords = [(values[j] + x if rel else values[j], values[j+1] + y if rel else values[j+1])
                      for j in range(0, len(values), 2)]
            points.extend(coords)
            current = coords[-1]
            if kind == "M":
                start = current
                command = "l" if rel else "L"
            if kind not in ("M", "L"):
                polygonal = False
    return points, polygonal


def _svg(path, root):
    result = _empty(path, root)
    tree = ET.parse(path).getroot()
    box = [float(v) for v in re.split(r"[ ,]+", tree.get("viewBox", "").strip()) if v]
    if len(box) != 4 or box[2] <= 0 or box[3] <= 0:
        raise ValueError("SVG has no usable viewBox")
    x0, y0, width, height = box
    result.update(page_count=1, pages=[{"page": 1, "width": width, "height": height, "text": "", "words": []}])
    result["metadata"]["view_box"] = box
    prefix = _uid(path, root)
    transformed = any(e.get("transform") for e in tree.iter())
    if transformed:
        result["warnings"].append("SVG contains transforms; semantic objects are retained without guessed geometry.")
    seen = set()
    for group in tree.iter():
        guid = group.get("data-guid")
        if not guid or guid in seen:
            continue
        seen.add(guid)
        cls = next((c for c in group.get("class", "").split() if c.startswith("Ifc")), "IfcProduct")
        obj = {"id": f"{prefix}:{guid}", "guid": guid, "type": cls,
               "label": group.get("data-name") or cls, "page": 1,
               "source_path": relative_path(path, root), "properties": {"source_kind": "semantic_svg"}}
        points, polys = [], []
        if not transformed:
            for element in group.iter():
                if element.tag.rsplit("}", 1)[-1] == "path":
                    pts, poly = _svg_path_points(element.get("d", ""))
                    normalized = [[(x-x0)/width, (y-y0)/height] for x, y in pts]
                    points.extend(normalized)
                    if poly and len(normalized) >= 3:
                        polys.append(normalized)
            if points:
                bounds = _bbox(points)
                obj["bbox"] = [round(max(0, min(1, v)), 6) for v in bounds]
                if cls == "IfcSpace" and polys:
                    obj["polygon"] = [[round(max(0, min(1, v)), 6) for v in p] for p in max(polys, key=len)]
        result["objects"].append(obj)
    model = linked_model(path)
    if model:
        result["metadata"]["linked_model"] = relative_path(model, root)
    return result


def _dxf(path, root):
    import ezdxf
    from ezdxf import bbox as dxf_bbox
    from shapely.geometry import Point, Polygon
    result = _empty(path, root)
    drawing = ezdxf.readfile(path)
    model = drawing.modelspace()
    extent = dxf_bbox.extents(model, fast=True)
    if not extent.has_data:
        return result
    minx, miny, maxx, maxy = extent.extmin.x, extent.extmin.y, extent.extmax.x, extent.extmax.y
    width, height = maxx-minx or 1, maxy-miny or 1
    norm = lambda x, y: [round((x-minx)/width, 6), round((maxy-y)/height, 6)]
    prefix = _uid(path, root)
    text_items, outlines, unit_outlines, arcs, windows, room_lines, fixtures = [], [], [], [], [], [], []
    door_frames = []
    layers = {}
    for entity in model:
        layer, kind = entity.dxf.layer.upper(), entity.dxftype()
        layers[layer] = layers.get(layer, 0) + 1
        if kind in ("TEXT", "MTEXT"):
            value = entity.dxf.text if kind == "TEXT" else entity.plain_text()
            point = entity.dxf.insert
            text_items.append({"text": value.strip(), "point": (point.x, point.y),
                               "layer": layer, "handle": entity.dxf.handle})
        elif kind == "LWPOLYLINE" and layer in ("ROOM_OUTLINE", "UNIT_OUTLINE"):
            points = [(v[0], v[1]) for v in entity.get_points()]
            closed = bool(entity.closed or (len(points) >= 4 and math.dist(points[0], points[-1]) <= 1e-7))
            if closed and len(points) >= 3 and not any(abs(v[4]) > 1e-12 for v in entity.get_points()):
                polygon = Polygon(points)
                if polygon.is_valid and polygon.area:
                    (outlines if layer == "ROOM_OUTLINE" else unit_outlines).append((entity.dxf.handle, points, polygon))
            elif layer == "ROOM_OUTLINE" and len(points) == 2:
                room_lines.append(points)
        elif kind == "ARC" and layer == "DOOR":
            arcs.append(entity)
        elif kind == "LWPOLYLINE" and layer == "DOOR" and len(entity) == 5:
            door_frames.append(entity)
        elif kind == "LWPOLYLINE" and layer == "WINDOW" and entity.closed:
            windows.append(entity)
        elif layer == "FIXTURE":
            fixtures.append(entity)
    result["metadata"].update({"layers": layers, "cad_extents": [minx, miny, maxx, maxy],
                                "coordinate_system": "normalized_cad_extents",
                                "preview_registration": False,
                                "insunits": drawing.units,
                                "cad_text": [{**t, "point": list(t["point"])} for t in text_items]})
    words = []
    for t in text_items:
        x, y = norm(*t["point"])
        words.append({"text": t["text"], "bbox": [max(0,x-.002), max(0,y-.012), min(1,x+.04), min(1,y+.003)]})
    result.update(page_count=1, pages=[{"page": 1, "width": width, "height": height,
                                      "text": "\n".join(t["text"] for t in text_items), "words": words}])
    for handle, points, polygon in unit_outlines:
        inside_tags = [t for t in text_items if polygon.covers(Point(t["point"]))]
        assigned = [t for t in inside_tags if re.fullmatch(r"(?:app\.?|apt\.?|wohnung|whg\.?|appartement|appart\.?|unita)\s+[A-Z]", t["text"], re.I)]
        commercial = [t for t in inside_tags if re.fullmatch(r"(?:gewerbe|commerce|commercio|commercial|unit[aàé])\s+\S{1,3}", t["text"], re.I)]
        # Only outlines carrying a residential tag are apartments. Untagged outlines and
        # commercial units stay inspectable but are not counted as residential units.
        kind = "apartment" if assigned else "commercial_unit" if commercial else "unit_outline_untagged"
        label = assigned[0]["text"] if assigned else commercial[0]["text"] if commercial else f"Untagged unit outline {handle}"
        poly = [norm(x,y) for x,y in points]
        result["objects"].append({"id": f"{prefix}:{handle}", "type": kind, "label": label,
                                  "page": 1, "bbox": _bbox(poly), "polygon": poly,
                                  "source_path": relative_path(path, root),
                                  "properties": {"layer": "UNIT_OUTLINE", "cad_handle": handle}})
    # Nested outlines (a lift inside its shaft, a niche inside a room) all cover the same
    # label texts. A room number belongs to the smallest outline that contains it, and the
    # name and area are the texts stacked on that number, so no outline inherits a label twice.
    number_re = r"[A-Za-z]?\d+[.\-]\d+(?:[.\-]\d+)?"
    tag_re = r"(?:app\.?|apt\.?|wohnung|whg\.?|appart\.?)\s+[A-Z]"
    room_texts = [t for t in text_items if t["layer"] == "ROOM_TEXT"]
    owner = {}
    for t in room_texts:
        if re.fullmatch(number_re, t["text"]):
            covering = [(polygon.area, handle) for handle, _, polygon in outlines if polygon.covers(Point(t["point"]))]
            if covering:
                owner.setdefault(min(covering)[1], []).append(t)

    def _stack(number):
        x, y = number["point"]
        return [t for t in room_texts if t is not number and abs(t["point"][0]-x) < 1e-6 and abs(t["point"][1]-y) < 1.2]
    # Net floor area excludes spaces drawn inside a room (a lift or shaft inside a stairwell).
    from shapely.ops import unary_union
    net_geometry = {}
    for handle, _, polygon in outlines:
        inner = [other for h, _, other in outlines if h != handle and other.area < polygon.area
                 and polygon.intersection(other).area > 0.5 * other.area]
        net_geometry[handle] = polygon.difference(unary_union(inner)).area if inner else polygon.area
    for handle, points, polygon in outlines:
        numbers = owner.get(handle, [])
        if numbers:
            stack = _stack(numbers[0])
            areas = [t for t in stack if t["point"][1] < numbers[0]["point"][1] and re.search(r"\d[\d.,]*\s*m[²2]", t["text"], re.I)]
            names = [t for t in sorted(stack, key=lambda t: t["point"][1]) if t["point"][1] > numbers[0]["point"][1]
                     and not re.search(r"\d[\d.,]*\s*m[²2]", t["text"], re.I) and not re.fullmatch(tag_re, t["text"], re.I)]
        else:
            inside = [t for t in room_texts if polygon.covers(Point(t["point"]))]
            owned = {id(t) for ts in owner.values() for n in ts for t in [n] + _stack(n)}
            free = [t for t in inside if id(t) not in owned]
            areas = [t for t in free if re.search(r"\d[\d.,]*\s*m[²2]", t["text"], re.I)]
            names = [t for t in free if t not in areas and not re.fullmatch(tag_re, t["text"], re.I)]
        label = names[0]["text"] if names else "Room"
        props = {"layer": "ROOM_OUTLINE", "cad_handle": handle,
                 "room_number": numbers[0]["text"] if numbers else None,
                 "cad_anchor": list(numbers[0]["point"]) if numbers else list(polygon.representative_point().coords[0])}
        # A crossed closed room outline denotes a shaft/void in these semantic
        # exports. Retain the basis so exclusions can be inspected.
        crossing = [line for line in room_lines if abs(line[0][0]-line[1][0]) > 1e-5
                    and abs(line[0][1]-line[1][1]) > 1e-5
                    and polygon.buffer(1e-7).covers(Point(line[0]))
                    and polygon.buffer(1e-7).covers(Point(line[1]))]
        if len(crossing) >= 2:
            props["spatial_kind"] = "shaft_or_void"
        if areas:
            match = re.search(r"([\d.,]+)\s*m[²2]", areas[0]["text"], re.I)
            props["net_area_m2"] = float(match.group(1).replace(",", "."))
            props["printed_area_m2"] = props["net_area_m2"]
            props["area_source"] = "native room area annotation"
        elif drawing.units == 6:
            props["net_area_m2"] = net_geometry[handle]
            props["area_source"] = ("closed native room polygon minus enclosed spaces, metre drawing units"
                                    if net_geometry[handle] < polygon.area - 1e-9 else
                                    "closed native room polygon in metre drawing units")
        if drawing.units == 6:
            props["geometry_area_m2"] = polygon.area
            props["geometry_area_source"] = "closed ROOM_OUTLINE polygon; DXF INSUNITS=metres"
        for uhandle, _, upolygon in unit_outlines:
            if upolygon.covers(polygon.representative_point()):
                props["unit_id"] = f"{prefix}:{uhandle}"
        poly = [norm(x,y) for x,y in points]
        result["objects"].append({"id": f"{prefix}:{handle}", "type": "room", "label": label,
                                  "page": 1, "bbox": _bbox(poly), "polygon": poly,
                                  "source_path": relative_path(path, root), "properties": props})
    semantic_layers = {"ROOM_OUTLINE", "UNIT_OUTLINE", "ROOM_TEXT"}.issubset(layers)
    if semantic_layers:
        result["metadata"]["semantic_inventory"] = {"door":len(door_frames) if door_frames else len(arcs), "window":len(windows)}
    # These symbol rules describe the supplied layered Swiss export style only.
    # They are not a general CAD object detector. Restrict them to its semantic
    # layers and retain the geometric basis for every classified fixture.
    if semantic_layers and "FIXTURE" in layers:
        result["objects"].extend(_swiss_fixtures(fixtures, prefix, norm, path, root))
        for category in ("toilet", "washbasin", "bathtub", "shower"):
            result["metadata"]["semantic_inventory"][category] = sum(
                o["type"] == category for o in result["objects"])
    # One door frame (5-point leaf outline) per door symbol, duplicates kept as in the
    # export. Arcs miss leaf-only doors and double-count double doors; they remain the
    # basis only for exports without frames.
    for frame in door_frames if semantic_layers else []:
        poly = [norm(v[0], v[1]) for v in frame.get_points()]
        result["objects"].append({"id": f"{prefix}:{frame.dxf.handle}", "type": "door",
                                  "label": "Door frame", "page": 1, "bbox": _bbox(poly), "polygon": poly,
                                  "source_path": relative_path(path, root),
                                  "properties": {"cad_handle": frame.dxf.handle,
                                                 "count_basis": "one door frame outline per semantic door symbol",
                                                 "complete_inventory": True}})
    for arc in arcs if not (semantic_layers and door_frames) else []:
        center, radius = arc.dxf.center, arc.dxf.radius
        points = [norm(center.x-radius, center.y-radius), norm(center.x+radius, center.y+radius)]
        result["objects"].append({"id": f"{prefix}:{arc.dxf.handle}", "type": "door" if semantic_layers else "door_swing",
                                  "label": "Door swing arc", "page": 1, "bbox": _bbox(points),
                                  "source_path": relative_path(path, root),
                                  "properties": {"cad_handle": arc.dxf.handle,
                                                 "count_basis":"one door swing arc per semantic door symbol",
                                                 "complete_inventory": semantic_layers}})
    for window in windows:
        poly = [norm(v[0],v[1]) for v in window.get_points()]
        result["objects"].append({"id":f"{prefix}:{window.dxf.handle}", "type":"window",
                                  "label":"Window outline", "page":1, "bbox":_bbox(poly), "polygon":poly,
                                  "source_path":relative_path(path,root),
                                  "properties":{"cad_handle":window.dxf.handle,
                                                "count_basis":"closed WINDOW layer outline"}})
    return result


def _swiss_fixtures(entities, prefix, norm, path, root):
    """Recognize documented symbol topology, without reading question labels.

    The exporter emits dense bowl curves, an enclosing rectangle and either a
    cistern stroke or tap circle; tub outlines are denser rounded curves. Unknown
    fixture shapes remain unclassified instead of becoming guessed instances.
    """
    from shapely.geometry import Point, Polygon
    polylines, frames, strokes, taps = [], [], [], []
    for entity in entities:
        if entity.dxftype() == "CIRCLE":
            taps.append((entity.dxf.center.x, entity.dxf.center.y))
        elif entity.dxftype() == "LWPOLYLINE":
            points = [(float(v[0]), float(v[1])) for v in entity.get_points()]
            if any(abs(v[4]) > 1e-12 for v in entity.get_points()):
                continue
            if entity.closed and len(points) >= 3:
                shape = Polygon(points)
                if shape.is_valid and shape.area:
                    frames.append((shape, points, entity.dxf.handle))
            elif len(points) == 2:
                strokes.append(Point((points[0][0]+points[1][0])/2, (points[0][1]+points[1][1])/2))
            else:
                polylines.append((entity.dxf.handle, points))
    results, used = [], set()
    for handle, points in polylines:
        count = len(points)
        if count not in (5, 48, 69):
            continue
        if len(points) < 3:
            continue
        center = Point(sum(p[0] for p in points)/count, sum(p[1] for p in points)/count)
        containing = sorted((f for f in frames if f[0].covers(center)), key=lambda f: f[0].area)
        frame = containing[0] if containing else None
        category, basis = None, None
        if count == 69:
            category, basis = "bathtub", "dense rounded tub outline in the Swiss FIXTURE symbol set"
        elif count == 5:
            if math.dist(points[0], points[-1]) <= 1e-7:
                category, basis = "shower", "closed tray outline in the Swiss FIXTURE symbol set"
        elif frame:
            if any(frame[0].covers(stroke) for stroke in strokes):
                category, basis = "toilet", "bowl curve, enclosing frame and cistern stroke"
            elif any(frame[0].covers(Point(tap)) for tap in taps):
                category, basis = "washbasin", "bowl curve, enclosing frame and tap circle"
        if category is None:
            continue
        identity = frame[2] if frame and category in {"toilet", "washbasin"} else handle
        if identity in used:
            continue
        used.add(identity)
        polygon = [norm(x, y) for x, y in (frame[1] if frame and category in {"toilet", "washbasin"} else points)]
        results.append({"id": f"{prefix}:fixture-{identity}", "type": category,
                        "label": category.capitalize(), "page": 1, "bbox": _bbox(polygon),
                        "source_path": relative_path(path, root),
                        "properties": {"layer": "FIXTURE", "cad_handle": handle,
                                       "count_basis": basis, "classifier": "swiss_semantic_fixture_v1"}})
    return results


def _project_dxf_to_pdf(cad, pdf):
    """Fit CAD→PDF from unique native room-number anchors; refuse bad fits."""
    rooms = [o for o in cad["objects"] if o["type"] == "room"]
    words = pdf["pages"][0]["words"] if pdf["pages"] else []
    pairs = []
    for room in rooms:
        number = room["properties"].get("room_number")
        found = [w for w in words if w["text"] == number] if number else []
        if len(found) == 1:
            box = found[0]["bbox"]
            pairs.append((room["properties"]["cad_anchor"], [(box[0]+box[2])/2, (box[1]+box[3])/2]))
    if len(pairs) < 3:
        pdf["warnings"].append("Linked CAD quantities available; insufficient matching anchors for a precise PDF overlay.")
        return _unregistered_cad_objects(cad, pdf["metadata"]["source_path"])
    def fit(axis):
        xs, ys = [p[0][axis] for p in pairs], [p[1][axis] for p in pairs]
        mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
        denominator = sum((v-mx)**2 for v in xs)
        if denominator < 1e-12:
            return None
        slope = sum((x-mx)*(y-my) for x,y in zip(xs,ys))/denominator
        if not math.isfinite(slope) or abs(slope) < 1e-10:
            return None
        return slope, my-slope*mx
    fx, fy = fit(0), fit(1)
    if not fx or not fy:
        pdf["warnings"].append("Linked CAD alignment is degenerate; source records are retained without drawing locations.")
        return _unregistered_cad_objects(cad, pdf["metadata"]["source_path"])
    residual = sum(math.hypot(fx[0]*c[0]+fx[1]-p[0], fy[0]*c[1]+fy[1]-p[1]) for c,p in pairs)/len(pairs)
    if residual > .015:
        pdf["warnings"].append("Linked CAD alignment was ambiguous; polygons were not projected onto the PDF.")
        return _unregistered_cad_objects(cad, pdf["metadata"]["source_path"])
    minx, miny, maxx, maxy = cad["metadata"]["cad_extents"]
    def transform(point):
        x, y = minx+point[0]*(maxx-minx), maxy-point[1]*(maxy-miny)
        return [round(max(0,min(1,fx[0]*x+fx[1])),6), round(max(0,min(1,fy[0]*y+fy[1])),6)]
    objects = []
    for original in cad["objects"]:
        obj = {**original, "properties": dict(original["properties"])}
        obj["properties"]["native_source_path"] = original["source_path"]
        obj["properties"]["projection_mean_error"] = round(residual, 6)
        obj["properties"]["preview_registration"] = True
        obj["source_path"] = pdf["metadata"]["source_path"]
        if obj.get("polygon"):
            obj["polygon"] = [transform(p) for p in obj["polygon"]]
            obj["bbox"] = _bbox(obj["polygon"])
        elif obj.get("bbox"):
            b = obj["bbox"]
            obj["bbox"] = _bbox([transform(b[:2]),transform(b[2:])])
        objects.append(obj)
    return objects


def _unregistered_cad_objects(cad, displayed_source=None):
    """Retain native quantities while withholding unregistered visual geometry."""
    objects = []
    for original in cad.get("objects", []):
        if original.get("type") == "door_swing":
            continue
        obj = {**original, "properties": dict(original.get("properties", {}))}
        props = obj["properties"]
        props["native_source_path"] = original.get("source_path")
        props["preview_registration"] = False
        props["native_geometry"] = {"coordinate_system": "normalized_cad_extents",
                                    "bbox": original.get("bbox"), "polygon": original.get("polygon")}
        obj.pop("bbox", None)
        obj.pop("polygon", None)
        if displayed_source:
            obj["source_path"] = displayed_source
        objects.append(obj)
    return objects


_IFC_QUANTITY_PROPERTIES = {
    "netfloorarea": ("net_area_m2", "area", "m²"),
    "netarea": ("net_area_m2", "area", "m²"),
    "nettoflache": ("net_area_m2", "area", "m²"),
    "nettogeschossflache": ("net_area_m2", "area", "m²"),
    "grossfloorarea": ("gross_area_m2", "area", "m²"),
    "grossarea": ("gross_area_m2", "area", "m²"),
    "netsidearea": ("net_side_area_m2", "area", "m²"),
    "grosssidearea": ("gross_side_area_m2", "area", "m²"),
    "netvolume": ("net_volume_m3", "volume", "m³"),
    "grossvolume": ("gross_volume_m3", "volume", "m³"),
    "length": ("length_m", "length", "m"),
    "netlength": ("net_length_m", "length", "m"),
    "grosslength": ("gross_length_m", "length", "m"),
}


def _ifc_explicit_quantities(entity, metadata):
    """Retain exact quantity roles, property paths and dimensional units.

    No tessellated bounding-box approximation is substituted for a quantity.
    Unknown units/roles stay unavailable so aggregation can refuse partial sums.
    """
    import ifcopenshell.util.unit as unit_util
    result = {}
    for relation in getattr(entity, "IsDefinedBy", ()):
        definition = getattr(relation, "RelatingPropertyDefinition", None)
        if not definition or not definition.is_a("IfcElementQuantity"):
            continue
        for quantity in definition.Quantities:
            normalized = re.sub(r"[^a-z]", "", (quantity.Name or "").casefold())
            role = _IFC_QUANTITY_PROPERTIES.get(normalized)
            if role is None:
                continue
            key, dimension, unit_name = role
            expected_type = {"area": "IfcQuantityArea", "length": "IfcQuantityLength", "volume": "IfcQuantityVolume"}[dimension]
            if not quantity.is_a(expected_type):
                continue
            explicit_unit = getattr(quantity, "Unit", None)
            if explicit_unit is not None:
                if getattr(explicit_unit, "UnitType", None) != dimension.upper()+"UNIT":
                    continue
                try:
                    factor = unit_util.get_unit_scale(explicit_unit)
                except (AttributeError, TypeError, ValueError):
                    continue
                unit_basis = "explicit quantity unit"
            else:
                factor = metadata[dimension+"_unit_scale"]
                unit_basis = "project "+dimension.upper()+"UNIT"
            raw = getattr(quantity, {"area": "AreaValue", "length": "LengthValue", "volume": "VolumeValue"}[dimension], None)
            if type(raw) not in (int, float) or not math.isfinite(raw) or raw < 0 or factor is None or not math.isfinite(factor) or factor <= 0:
                continue
            value = float(raw)*factor
            path = f"{definition.Name}.{quantity.Name}"
            if key in result and not math.isclose(result[key], value, rel_tol=1e-9, abs_tol=1e-9):
                # Conflicting same-role source values are not arbitrarily chosen.
                result.pop(key, None)
                result.setdefault("ambiguous_quantities", []).append(key)
                continue
            if key in result.get("ambiguous_quantities", []):
                continue
            result[key] = value
            result.setdefault("quantity_sources", {})[key] = {
                "property_path": path, "value": value, "unit": unit_name,
                "raw_value": raw, "unit_scale": factor, "unit_basis": unit_basis}
            if key == "net_area_m2":
                result["area_source"] = path
                result["area_unit_basis"] = unit_basis
    return result


def _ifc(path, root):
    import ifcopenshell
    import ifcopenshell.util.element as element_util
    import ifcopenshell.util.unit as unit_util
    result = _empty(path, root)
    model = ifcopenshell.open(str(path))
    prefix = _uid(path, root)
    storeys = model.by_type("IfcBuildingStorey")
    projects = model.by_type("IfcProject")
    units = getattr(projects[0], "UnitsInContext", None) if projects else None
    assigned_types = {getattr(u, "UnitType", None) for u in units.Units} if units else set()
    def project_unit_scale(kind):
        # The library returns 1 for an absent assignment. Absence is not proof
        # of an SI unit; keep quantities with unknown dimensional units absent.
        return unit_util.calculate_unit_scale(model, kind) if kind in assigned_types else None
    result["metadata"].update({"schema": model.schema, "storeys": [
        {"guid": s.GlobalId, "name": s.Name, "elevation": s.Elevation} for s in storeys],
        "linked_views": [], "length_unit_scale": project_unit_scale("LENGTHUNIT"),
        "area_unit_scale": project_unit_scale("AREAUNIT"),
        "volume_unit_scale": project_unit_scale("VOLUMEUNIT")})
    projections = {}
    from .rendering import visual_sources
    views = visual_sources(path)
    for page_number, displayed in enumerate(views, 1):
        view = displayed.with_suffix(".svg")
        if not view.exists():
            view = displayed
        try:
            doc = _svg(view, root) if view.suffix.lower()==".svg" else None
            result["metadata"]["linked_views"].append(relative_path(displayed, root))
            if displayed.suffix.lower()==".pdf":
                import pymupdf
                with pymupdf.open(displayed) as pdf:
                    width,height=pdf[0].rect.width,pdf[0].rect.height
            elif doc:
                width,height=doc["pages"][0]["width"],doc["pages"][0]["height"]
            else:
                from PIL import Image
                with Image.open(displayed) as image:
                    width,height=image.size
            result["pages"].append({"page":page_number,"width":width,"height":height,
                                    "text":"","words":[],"source_path":relative_path(displayed,root)})
            for obj in doc["objects"] if doc else []:
                obj["source_path"] = relative_path(displayed, root)
                projections.setdefault(obj["guid"], []).append(obj)
        except Exception:
            result["warnings"].append(f"Unable to parse linked view {view.name}.")
    result["page_count"]=len(result["pages"])
    entities = (list(model.by_type("IfcElement")) + list(model.by_type("IfcSpace")) + list(storeys)
                + list(model.by_type("IfcProject")) + list(model.by_type("IfcSite")) + list(model.by_type("IfcBuilding")))
    for entity in entities:
        guid = entity.GlobalId
        props = {"name": getattr(entity, "Name", None), "long_name": getattr(entity, "LongName", None),
                 "description": getattr(entity, "Description", None), "ifc_entity_id": entity.id()}
        try:
            container = element_util.get_container(entity)
            if container:
                # Elements contained in a space (or another sub-storey zone) belong to the storey
                # that aggregates it: walk up the spatial hierarchy to the IfcBuildingStorey.
                storey, seen = container, set()
                while storey is not None and not storey.is_a("IfcBuildingStorey") and storey.id() not in seen:
                    seen.add(storey.id())
                    storey = element_util.get_aggregate(storey) or element_util.get_container(storey)
                if storey is not None and storey.is_a("IfcBuildingStorey"):
                    props.update(storey=storey.Name, storey_guid=storey.GlobalId)
                    if storey is not container:
                        props.update(spatial_container=container.Name, spatial_container_class=container.is_a())
                else:
                    props.update(storey=container.Name, storey_guid=container.GlobalId)
            elif entity.is_a("IfcSpace"):
                parent = element_util.get_aggregate(entity)
                if parent and parent.is_a("IfcBuildingStorey"):
                    props.update(storey=parent.Name, storey_guid=parent.GlobalId)
            # A part aggregated into another product (a stair inside a stair, a panel inside a
            # curtain wall) is not a separate instance of its class.
            whole = element_util.get_aggregate(entity)
            # Only a part of the same class (a stair inside a stair) is not a separate instance;
            # a door hosted in a curtain wall is still a door.
            base = lambda name: name.replace("StandardCase", "").replace("ElementedCase", "")
            if (whole is not None and whole.is_a("IfcProduct") and not whole.is_a("IfcSpatialStructureElement")
                    and base(whole.is_a()) == base(entity.is_a())):
                props.update(nested_in=whole.is_a(), nested_in_guid=getattr(whole, "GlobalId", None))
            # Large walls/MEP models can contain tens of thousands of products.
            # Read full property sets only where this native QA route uses them.
            psets = element_util.get_psets(entity) if entity.is_a("IfcSpace") else {}
            if psets:
                props["property_sets"] = _safe(psets)
                # Common exporter-specific area properties, e.g. Estonian
                # AR_Ruum.120_Pindala. Do not confuse a length unit with area.
                candidates = []
                for set_name, values in psets.items():
                    if not isinstance(values, dict):
                        continue
                    for property_name, value in values.items():
                        normalized_name = re.sub(r"[^a-z]", "", property_name.casefold())
                        # ArchiCAD writes the zone's net area as "Measured Net Area" on every zone.
                        if normalized_name in ("netfloorarea", "netarea", "measurednetarea", "pindala", "nettoflache", "nutzflache"):
                            if type(value) in (int, float):
                                parsed = float(value)
                            elif isinstance(value, str) and re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*", value):
                                parsed = float(value.strip().replace(",", "."))
                            else:
                                continue
                            candidates.append((0 if normalized_name.startswith(("net", "measurednet")) else 1,
                                               parsed, f"{set_name}.{property_name}"))
                if candidates and result["metadata"]["area_unit_scale"] is not None:
                    _, value, property_path = min(candidates)
                    props["net_area_m2"] = value * result["metadata"]["area_unit_scale"]
                    props["area_source"] = property_path
                    props["area_unit_basis"] = "project AREAUNIT"
            props.update(_ifc_explicit_quantities(entity, result["metadata"]))
            for ambiguous in props.get("ambiguous_quantities", []):
                props.pop(ambiguous, None)
            if entity.is_a("IfcSite"):
                for attr in ("RefLatitude", "RefLongitude", "RefElevation", "LandTitleNumber"):
                    if getattr(entity, attr, None) is not None:
                        props[attr] = _safe(getattr(entity, attr))
            if entity.is_a("IfcProject"):
                for attr in ("Phase", "ObjectType"):
                    if getattr(entity, attr, None) is not None:
                        props[attr] = _safe(getattr(entity, attr))
            if entity.is_a("IfcBuilding"):
                for attr in ("ElevationOfRefHeight", "ElevationOfTerrain"):
                    if getattr(entity, attr, None) is not None:
                        props[attr] = _safe(getattr(entity, attr))
            typ = element_util.get_type(entity)
            if typ:
                props["element_type"] = typ.Name
                props["element_type_class"] = typ.is_a()
            predefined = getattr(entity, "PredefinedType", None) or getattr(typ, "PredefinedType", None)
            if predefined:
                props["predefined_type"] = str(predefined)
        except Exception:
            pass
        # Dimensions are model length units, separate from area quantities.
        for key in ("OverallWidth", "OverallHeight"):
            value = getattr(entity, key, None)
            if value is not None and result["metadata"]["length_unit_scale"] is not None:
                props[key] = value * result["metadata"]["length_unit_scale"]
            elif value is not None:
                props[key+"_raw"] = value
                props["dimension_warning"] = "No project LENGTHUNIT assignment; raw dimensions are not SI quantities."
        label = " · ".join(str(v) for v in (props.get("name"), props.get("long_name")) if v) or entity.is_a()
        obj = {"id": f"{prefix}:{guid}", "guid": guid, "type": entity.is_a(),
               "label": label, "page": 1, "source_path": relative_path(path, root), "properties": props}
        if projections.get(guid):
            projection = projections[guid][0]
            for key in ("bbox", "polygon", "source_path", "page"):
                if key in projection:
                    obj[key] = projection[key]
            obj["properties"]["native_source_path"] = relative_path(path, root)
            obj["properties"]["available_projections"] = [p["source_path"] for p in projections[guid]]
        result["objects"].append(obj)
    result["metadata"]["class_counts"] = {}
    for obj in result["objects"]:
        cls = obj["type"]
        result["metadata"]["class_counts"][cls] = result["metadata"]["class_counts"].get(cls, 0) + 1
    if result["metadata"]["linked_views"]:
        result["metadata"]["preview_path"] = result["metadata"]["linked_views"][0]
    result["warnings"].append("BIM quantities describe model contents; completeness of the construction model is not independently established.")
    return result


def extract_document(path: Path, data_root: Path) -> dict:
    path, data_root = Path(path), Path(data_root)
    if path.suffix.lower() == ".dxf" and path.with_suffix(".pdf").exists():
        # The viewer uses the paired sheet; reuse its anchor-fitted evidence.
        result = _pdf(path.with_suffix(".pdf"), data_root)
        result["format"] = "dxf"
        result["metadata"]["original_source_path"] = relative_path(path, data_root)
        result["metadata"]["preview_path"] = relative_path(path.with_suffix(".pdf"), data_root)
        return result
    from .rendering import RASTER_SUFFIXES
    dispatch = {".pdf": _pdf, **{suffix: _image for suffix in RASTER_SUFFIXES},
                ".svg": _svg, ".dxf": _dxf, ".ifc": _ifc}
    extractor = dispatch.get(path.suffix.casefold())
    if extractor is None:
        result = _empty(path, data_root)
        result["warnings"].append("This format requires conversion before native extraction.")
        return result
    result = extractor(path, data_root)
    if path.suffix.lower() == ".dxf":
        # The standalone renderer chooses its own page margins and layout.
        # CAD-extent coordinates have no established image-to-page transform.
        result["objects"] = _unregistered_cad_objects(result)
        for page in result.get("pages", []):
            page["words"] = [{"text": word.get("text", "")} for word in page.get("words", [])]
        result["metadata"]["coordinate_system"] = "unregistered_native_cad"
        result["metadata"]["cad_projection_registered"] = False
        result["warnings"].append("Native CAD quantities are available, but their coordinates are not registered to this preview. Drawing highlights are withheld.")
    return result


@lru_cache(maxsize=8)
def extract_cached(path: str, data_root: str, mtime_ns: int = 0) -> dict:
    return extract_document(Path(path), Path(data_root))


def render_page(path: Path, page: int = 1, scale: float = 1.5) -> bytes:
    """Rasterize a source page without modifying the drawing."""
    import fitz
    path = Path(path)
    if path.suffix.lower() in (".ifc", ".dxf"):
        sibling = path.with_suffix(".pdf")
        if not sibling.exists() and path.suffix.lower() == ".ifc":
            sibling = next(iter(sorted(path.parent.glob(path.stem + "_plan-*.pdf"))), None)
        if not sibling or not sibling.exists():
            raise ValueError("No linked 2D rendering is available")
        path = sibling
    with fitz.open(path) as source:
        doc = source
        if not source.is_pdf and path.suffix.lower() == ".svg":
            doc = fitz.open("pdf", source.convert_to_pdf())
        target = doc.load_page(page - 1)
        # The original page's rotation matches extraction after remove_rotation.
        return target.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).tobytes("png")

"""Material takeoff from native room outlines: perimeter, skirting, wall area and waste.

No model call. A length is measured on the same closed room outline the area answers
use, and those rooms are returned as evidence. What a floor plan cannot show (the
ceiling height, a waste allowance) is read from the question and never assumed.
"""
from __future__ import annotations

import math
import re

from .native_qa import _QUOTED_TEXT, _normal, _result

_ROOM_NUMBER = r"\b[a-z]?\d+[.\-]\d+(?:[.\-]\d+)?\b"
_OUTDOOR = r"balcon|balkon|loggia|terrass|terrazz|outdoor|shaft|void|schacht|caved|vuoto|luftraum"
_LENGTH = r"(\d+(?:[.,]\d+)?)\s*-?\s*(mm|cm|metres?|meters?|m)\b"
_HEIGHT_WORD = r"(?:ceiling|room|wall|clear|storey)\s+height"
_HEIGHT = re.compile(r"(?:\b(?:with|at|for|using|assuming|given|and)\s+)?(?:\b(?:a|an|the)\s+)?"
                     r"(?:\b" + _HEIGHT_WORD + r"\s+(?:of\s+|is\s+)?)?(?:\bh\s*=?\s*)?" + _LENGTH
                     + r"(?:\s*-?\s*(?:high|tall|ceilings?(?:\s+height)?|" + _HEIGHT_WORD + r"|height)\b)?")
# Groups: an explicit addition (+, plus, add, allow for), "extra", the percentage, a waste word.
_WASTE = re.compile(r"(?:\b(?:and|with|including|incl\.?)\s+)?(\+|\b(?:plus|add(?:ing)?|allow(?:ing)?(?:\s+for)?)\b)?\s*"
                    r"(?:\ban?\s+)?(\bextra\s+)?(?<![\d.,])(\d{1,2}(?:[.,]\d+)?)\s*(?:%|percent\b|per cent\b)"
                    r"(?:\s+(?:of|for|as)\b)?(?:\s+(extra|cutting waste|waste|wastage|allowance|overage|spare|contingency|margin)\b)?"
                    r"(?:\s+(?:allowance|factor|margin)\b)?", re.I)
_APARTMENT = r"\b(?:apartment|apt\.?|app\.?|flat|unit|wohnung|whg\.?|appartement|appart\.?|appartamento)\s+([a-z])\b"
# First match wins: a wall-area question can also mention the perimeter it is built from.
_KINDS = (("wall", r"\bwall (?:surface |finish )?areas?\b|\bwall surfaces?\b|\bareas? of (?:the |all )?walls\b"),
          ("skirting", r"\bskirting(?: boards?)?\b|\bskirtings\b|\bbaseboards?\b"),
          ("perimeter", r"\bperimeters?\b"))
_SAFE = set("what s is are the a an of for in on at to this that these those all total combined overall whole entire every each "
            "room rooms space spaces apartment flat unit floor plan drawing level storey selected area areas "
            "need needs needed require requires required do does i we you me my our it there will be should would can could please "
            "how much many long length lengths linear running run metre metres meter meters m lm square sqm "
            "calculate compute measure give find tell show determine and sum indoor interior internal inside "
            "labelled labeled named numbered install fit order buy".split())


def _fmt(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _name(room):
    number, label = room.get("properties", {}).get("room_number"), room.get("label")
    label = None if label in (None, "", "Room") else label
    return f"room {number} ({label})" if number and label else f"room {number}" if number else label or "unnamed room"


def _perimeter(room, document):
    """Outline length in metres, or None. The outline and its own metric area fix the
    scale, so no sheet scale, DPI or typical object size is assumed."""
    props, meta = room.get("properties", {}), document.get("metadata", {})
    area, points, matrix = props.get("geometry_area_m2"), room.get("polygon"), meta.get("preview_transform")
    try:
        if points and matrix:  # standalone CAD: undo the renderer's page placement
            a, b, c, d, e, f = matrix
            det = a * e - b * d
            outline = [((e * (u - c) - b * (v - f)) / det, (a * (v - f) - d * (u - c)) / det) for u, v in points]
        else:
            if points:  # registered to a paired sheet: page units
                page = next(p for p in document.get("pages", []) if p.get("page") == room.get("page", 1))
                width, height = page["width"], page["height"]
            else:  # unregistered CAD keeps its outline normalized to the CAD extents
                points = props["native_geometry"]["polygon"]
                x0, y0, x1, y1 = meta["cad_extents"]
                width, height = x1 - x0, y1 - y0
            outline = [(x * width, y * height) for x, y in points]
        from shapely.geometry import Polygon
        shape = Polygon(outline)
        if type(area) not in (int, float) or not area > 0 or not shape.is_valid or not shape.area > 0:
            return None
        value = shape.exterior.length * math.sqrt(area / shape.area)
        return value if math.isfinite(value) else None
    except (KeyError, StopIteration, TypeError, ValueError, ZeroDivisionError):
        return None


def _scope(q, kind, rooms, units, region):
    """(rooms, description, question without its room selectors), or None when the
    question names a room this drawing does not have."""
    indoor = lambda items: [r for r in items if not re.search(_OUTDOOR, _normal(r.get("label")))
                            and r.get("properties", {}).get("spatial_kind") not in ("shaft_or_void", "outdoor")]
    labels = {}
    for room in rooms:
        if room.get("label") not in (None, "", "Room"):
            labels.setdefault(_normal(room["label"]), []).append(room)
    quoted = [m[1:-1].strip() for m in re.findall(_QUOTED_TEXT, q)]
    if any(label not in labels for label in quoted):
        return None
    q = re.sub(_QUOTED_TEXT, " ", q)
    numbers = list(dict.fromkeys(re.findall(_ROOM_NUMBER, q)))
    letter = re.search(_APARTMENT, q)
    mentioned = quoted or [label for label in labels if re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", q)]
    if numbers:
        chosen = [r for r in rooms if str(r.get("properties", {}).get("room_number") or "").casefold() in numbers]
        if {str(r["properties"]["room_number"]).casefold() for r in chosen} != set(numbers):
            return None
        where = _name(chosen[0]) if len(chosen) == 1 else f"{len(chosen)} rooms ({', '.join(numbers)})"
        q = re.sub(_ROOM_NUMBER, " ", q)
    elif letter:
        unit = [u for u in units if re.search(r"\b" + letter.group(1) + r"\b", _normal(u.get("label")))]
        # The perimeter of an apartment is its own boundary, not the sum of its rooms.
        if len(unit) != 1 or kind == "perimeter":
            return None
        chosen = indoor([r for r in rooms if r.get("properties", {}).get("unit_id") == unit[0]["id"]])
        where = f"{unit[0]['label']} ({len(chosen)} indoor rooms)"
        q = q.replace(letter.group(0), " ")
    elif mentioned:
        chosen = [r for label in mentioned for r in labels[label]]
        where = _name(chosen[0]) if len(chosen) == 1 else f"{len(chosen)} rooms labelled {', '.join(labels[m][0]['label'] for m in mentioned)}"
    else:
        # "The perimeter of this floor" is the building outline, which room outlines do not give.
        if kind == "perimeter" and not re.search(r"\b(?:rooms|spaces)\b", q):
            return None
        chosen = indoor([r for r in rooms if r.get("properties", {}).get("room_number")])
        where = f"all {len(chosen)} indoor rooms " + ("in the selected area" if region else "on this drawing")
    for label in mentioned:
        q = re.sub(r"(?<!\w)" + re.escape(label) + r"(?!\w)", " ", q)
    return (chosen, where, q) if chosen else None


def _room_quantity(question, document):
    objects = document.get("objects", [])
    rooms = [o for o in objects if o.get("type") == "room"]
    q = _normal(question)
    kind = next((name for name, pattern in _KINDS if re.search(pattern, q)), None)
    if not rooms or not kind:
        return None
    # "How many skirting" is a count, which a length cannot answer.
    if re.search(r"\b(?:number of|count)\b|\bhow many\b(?! (?:linear |running |square )?(?:metres?|meters?|m|lm|sqm)\b)", q):
        return None
    height, match = None, _HEIGHT.search(q)
    # In a wall-area question a lone length can only be the height.
    if match and (kind == "wall" or re.search(r"height|high|tall|ceiling", match.group(0))):
        height = float(match.group(1).replace(",", ".")) * {"mm": .001, "cm": .01}.get(match.group(2), 1)
        q = q[:match.start()] + " " + q[match.end():]
    scope = _scope(q, kind, rooms, [o for o in objects if o.get("type") == "apartment"],
                   document.get("metadata", {}).get("requested_scope") == "region")
    if scope is None:
        return None
    chosen, where, q = scope
    for _, pattern in _KINDS:
        q = re.sub(pattern, " ", q)
    q = re.sub(r"\b(?:m|ft)[23]\b", " ", q)
    # Every remaining word must be understood: an unresolved filter is refused, not ignored.
    if re.search(r"[\d<>]", q) or not all(word in _SAFE for word in re.findall(r"[a-z]+", q)):
        return None
    terms = [_perimeter(room, document) for room in chosen]
    if any(term is None for term in terms) or (height is not None and (kind != "wall" or not 1.8 <= height <= 10)):
        return None
    # Each room is rounded to the centimetre first, so the listed terms add up to the total.
    terms = [round(term, 2) for term in terms]
    total = round(sum(terms), 2)
    outline = (" + ".join(_fmt(t) for t in terms[:8]) + (" + …" if len(terms) > 8 else "") + f" = {_fmt(total)} m"
               if len(terms) > 1 else f"closed outline of {where} = {_fmt(total)} m")
    if kind == "wall" and height is None:
        example = chosen[0]["properties"].get("room_number")
        return {"answer": "A wall area needs the ceiling height, which a floor plan does not show. Ask again with it, "
                          f"for example: wall area of {'room ' + example if example else 'all rooms'} with a 2.6 m ceiling.",
                "value": None, "unit": None, "method": "native_cad_room_takeoff", "status": "insufficient_evidence",
                "evidence": [], "warnings": [], "scope": "Selected floor drawing"}
    if kind == "wall":
        value, unit = round(total * height, 2), "m²"
        answer = (f"{_fmt(value)} m² of wall area for {where}: {_fmt(total)} m of room outline × {_fmt(height)} m "
                  "ceiling height. Door and window openings are not deducted.")
        formula = f"{_fmt(total)} m × {_fmt(height)} m = {_fmt(value)} m²"
    else:
        value, unit, formula = total, "m", outline
        answer = (f"{_fmt(total)} m of skirting for {where}, measured along the room outlines. Door openings are not deducted."
                  if kind == "skirting" else f"{_fmt(total)} m, perimeter of {where}.")
    result = _result(value, unit, chosen, "native_cad_room_takeoff", "Selected floor drawing",
                     calculation={"formula": formula, "operation": kind, "property": "closed room outline length (m)",
                                  "terms": terms, "term_unit": "m", "operand_ids": [r["id"] for r in chosen],
                                  "ceiling_height_m": height, "result": value})
    result["answer"] = answer
    return result


def _with_waste(net, percent):
    """Order quantity = net quantity x (1 + waste). The net answer and its evidence are kept."""
    if net and net.get("value") is None and net.get("method") == "native_cad_room_takeoff":
        return net  # the net quantity still needs an input, such as the ceiling height
    if (not net or net.get("unit") not in ("m", "m²", "m³", "ft²") or type(net.get("value")) not in (int, float)
            or not 0 < percent <= 50):
        return None
    value, unit, factor = round(net["value"] * (1 + percent / 100), 2), net["unit"], 1 + percent / 100
    return {**net, "value": value, "method": f"{net.get('method', 'native')}_with_waste",
            "answer": f"{_fmt(value)} {unit} including {_fmt(percent)}% waste. Net: {net['answer']}",
            "calculation": {"formula": f"{_fmt(net['value'])} {unit} × {factor:g} = {_fmt(value)} {unit}",
                            "operation": "waste_allowance", "net": net["value"], "waste_percent": percent,
                            "net_calculation": net.get("calculation"), "result": value}}


def answer(question, document, native):
    """A takeoff answer or None. `native` answers a question once its waste clause is removed."""
    waste = _WASTE.search(question)
    if waste and (waste.group(1) or waste.group(2) or waste.group(4)):
        return _with_waste(native(question[:waste.start()] + " " + question[waste.end():]),
                           float(waste.group(3).replace(",", ".")))
    return _room_quantity(question, document)

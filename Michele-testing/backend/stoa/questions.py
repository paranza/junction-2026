"""Deterministic question answering over a structured plan analysis ("facts").

Every analysis path (DXF, PDF, raster models) produces the same facts dict
(see pipeline.py). This module maps the dataset's question templates
(en / de / fr / it / fi) to exact computations on those facts. Gemini is only
used when no template matches (llm.py), and even then it receives the facts,
never the image.

answer() returns dict(value, unit, explanation, evidence=[ids]) or None.
"""
from __future__ import annotations

import re
import math
import unicodedata


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def quoted_name(q: str):
    m = re.search(r"«\s*(.+?)\s*»", q) or re.search(r"[‘“]\s*(.+?)\s*[’”]", q)
    if m:
        return m.group(1)
    m = re.search(r"'(.+)'", q)  # greedy: keeps "Cage d'escalier" intact
    return m.group(1) if m else None


NUM_RE = re.compile(r"\b([A-Z]{0,2}\d+(?:\.\d+)+)\b")
UNIT_RE = re.compile(r"(?:apartment|wohnung|appartement|appartamento|dell'appartamento|l'appartement)\s+([A-Z])\b", re.I)

LABEL = r"labelled|bezeichnung|designation|denominazione|denominati|designees|nimetty"
AREA = r"area|flache|surface|superficie|pinta-ala"
COUNT = r"how many|wie viele|combien|quant[ie]|kuinka monta"

# (regex on normalised question, object types to count). First match wins: specific first.
OBJECT_PATTERNS = [
    (r"showers? and bathtubs?|suihkua ja kylpyamme", ["shower", "bathtub"]),
    (r"sinks? and wash ?basins?|pesu- ja tiskiallas", ["washbasin", "sink"]),
    (r"bathtub|badewanne|baignoire|vasche da bagno|vasca", ["bathtub"]),
    (r"shower|dusche|douche|docce|doccia|suihku", ["shower"]),
    (r"washbasin|lavabo|lavabi|waschbecken", ["washbasin"]),
    (r"toilet bowl|wc seat|wc-istuin|toilets? \(wc\)|\bwcs?\b", ["wc"]),
    (r"window|fenster|fenetre|finestr|ikkun", ["window"]),
    (r"\bdoors?\b|\bturen\b|\bportes\b|\bporte\b|\bovea\b", ["door"]),
]
ROOM_PATTERNS = [  # counted as room categories (cubicasa-style plans)
    (r"bathroom|washroom|kylpy- tai pesuhuone", "bathroom"),
    (r"separate wc|erillist[a-z]* wc", "wc_room"),
    (r"bedroom|makuuhuone", "bedroom"),
    (r"kitchen|keitti", "kitchen"),
    (r"sauna", "sauna"),
    (r"balcon|parvek", "balcony"),
]


def _res(value, unit, explanation, evidence):
    return {"value": value, "unit": unit, "explanation": explanation, "evidence": evidence}


def _unknown(unit, explanation):
    return {**_res(None, unit, explanation, []), "status": "insufficient_evidence"}


def measured_area(room, facts):
    """Do not reuse old cached areas derived from an assumed image scale."""
    value = room.get("area_m2")
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        return None
    source = str(room.get("area_source", ""))
    scale = facts.get("scale", {})
    method = str(scale.get("method", ""))
    if (source.startswith("printed") or facts.get("source") == "dxf"
            or scale.get("verified") is True or method.startswith("calibrated")):
        return value
    return None


def _area_of(rooms, facts):
    values = [measured_area(room, facts) for room in rooms]
    return round(sum(values), 2) if values and all(v is not None for v in values) else None


def _supports(facts, capability, wanted=None):
    capabilities = facts.get("capabilities", {})
    if capability in capabilities:
        available = capabilities[capability]
        return all(item in available for item in wanted) if wanted is not None else bool(available)
    # Geometry identifies openings, not whether they are doors or windows.
    if facts.get("style") == "geometry":
        return False
    return True  # existing source-aware DXF/model facts retain their supported counts


# Questions that need extra arithmetic or assumptions go to the LLM over facts.
FREEFORM = r"\b(litres?|liters?|paint\w*|costs?|price|eur|order|need|tiles?|coats?|bags?|kg|how long|compare|which room|largest|smallest|biggest|percent)\b|€|%|\bper (m|litre|liter|square)"


def answer(question: str, facts: dict):
    q = norm(question)
    if re.search(FREEFORM, q):
        return None
    rooms = facts.get("rooms", [])
    objs = facts.get("objects", [])
    name = quoted_name(question)
    indoor = [r for r in rooms if not r.get("outdoor") and not r.get("shaft")]
    def area_result(rs, explanation):
        value = _area_of(rs, facts)
        return (_res(value, "m2", explanation, ids(rs)) if value is not None else
                _unknown("m2", "Area unavailable: every included room needs a printed area or a calibrated scale."))
    ids = lambda rs: [r["id"] for r in rs]
    same = lambda r: name is not None and r.get("name") and norm(r["name"]) == norm(name)

    if re.search(AREA, q) and re.search(r"\bm2|m²|m\?", q + question):
        num = NUM_RE.search(question)
        if num and re.search(r"\b(room|raum|piece|locale)\b", q):
            r = next((r for r in rooms if r.get("number") == num.group(1)), None)
            if r:
                return area_result([r], f"Room {r['number']} ({r.get('name') or 'unnamed'})")
        m = UNIT_RE.search(question)
        if m:
            u = m.group(1).upper()
            rs = [r for r in indoor if r.get("unit") == u]
            if rs:
                return area_result(rs, f"Sum of {len(rs)} indoor rooms of apartment {u}")
        if name and re.search(LABEL, q):
            rs = [r for r in rooms if same(r)]
            return area_result(rs, f"Sum of {len(rs)} rooms labelled '{name}'")
        if re.search(r"total|gesamt|totale|toutes|all", q):
            return area_result(indoor, f"Sum of all {len(indoor)} numbered indoor rooms")
        return None

    if re.search(COUNT, q):
        if name and re.search(LABEL, q):
            if not _supports(facts, "room_labels"):
                return _unknown("count", "Room labels were not read for this drawing style.")
            rs = [r for r in rooms if same(r)]
            return _res(len(rs), "count", f"Rooms labelled '{name}'", ids(rs))
        if re.search(r"apartment|wohnung|appartement|appartament|residential unit", q):
            if not _supports(facts, "apartment_inventory"):
                return _unknown("count", "Apartment boundaries were not classified for this drawing style.")
            us = facts.get("units", [])
            return _res(len(us), "count", "Apartment boundaries", [u["id"] for u in us])
        if re.search(r"floors \(storeys\)|kerrosta", q):
            if not _supports(facts, "storey_count"):
                return _unknown("count", "The number of separate floor drawings was not established.")
            return _res(facts.get("storeys", 1), "count", "Separate floor drawings on the sheet", [])
        for pat, cat in ROOM_PATTERNS:
            if re.search(pat, q) and not re.search(r"toilet bowl|wc seat|wc-istuin|drawn|piirretty", q):
                if not _supports(facts, "room_categories"):
                    return _unknown("count", "Room uses were not classified for this drawing style.")
                rs = [r for r in rooms if r.get("category") == cat]
                if cat == "sauna":  # a sauna stove is the unambiguous marker of a sauna
                    st = [o for o in objs if o["type"] == "sauna_stove"]
                    if len(st) > len(rs):
                        return _res(len(st), "count", "Sauna stoves detected", [o["id"] for o in st])
                return _res(len(rs), "count", f"Rooms of type {cat}", ids(rs))
        for pat, types in OBJECT_PATTERNS:
            if re.search(pat, q):
                if not _supports(facts, "object_types", types):
                    return _unknown("count", "Openings were not classified into the requested object categories.")
                hit = [o for o in objs if o["type"] in types]
                return _res(len(hit), "count", f"Detected {' + '.join(types)}", [o["id"] for o in hit])
    return None


if __name__ == "__main__":
    f = {"source": "dxf", "rooms": [{"id": "r1", "number": "2.01", "name": "Cage d'escalier", "area_m2": 5.0},
                   {"id": "r2", "number": "2.02", "name": "Bain", "area_m2": 4.0, "unit": "A"}],
         "objects": [{"id": "o1", "type": "wc"}, {"id": "o2", "type": "washbasin"}], "units": [{"id": "A"}]}
    assert answer("How many rooms labelled 'Cage d'escalier' are there on this floor?", f)["value"] == 1
    assert answer("Combien de WC sont dessinés sur ce plan ?", f)["value"] == 1
    assert answer("Quanti lavabi sono disegnati in questa pianta?", f)["value"] == 1
    assert answer("What is the net floor area of room 2.02 ('Bain') in m²?", f)["value"] == 4.0
    assert answer("Wie gross ist die Nettowohnfläche von Wohnung A in m² (Summe)?", f)["value"] == 4.0
    print("ok")

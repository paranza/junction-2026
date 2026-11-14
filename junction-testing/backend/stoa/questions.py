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
    (r"separate wc|erillist[a-z]* wc", "wc_room"),
    (r"bathroom|washroom|kylpy- tai pesuhuone", "bathroom"),
    (r"bedroom|makuuhuone", "bedroom"),
    (r"kitchen|keitti", "kitchen"),
    (r"sauna", "sauna"),
    (r"balcon|parvek", "balcony"),
]


def _res(value, unit, explanation, evidence):
    return {"value": value, "unit": unit, "explanation": explanation, "evidence": evidence}


def answer(question: str, facts: dict):
    q = norm(question)
    rooms = facts.get("rooms", [])
    objs = facts.get("objects", [])
    name = quoted_name(question)
    indoor = [r for r in rooms if not r.get("outdoor") and not r.get("shaft")]
    area_of = lambda rs: round(sum(r["area_m2"] or 0 for r in rs), 2)
    ids = lambda rs: [r["id"] for r in rs]
    same = lambda r: name is not None and r.get("name") and norm(r["name"]) == norm(name)

    if re.search(AREA, q) and re.search(r"\bm2|m²|m\?", q + question):
        num = NUM_RE.search(question)
        if num and re.search(r"\b(room|raum|piece|locale)\b", q):
            r = next((r for r in rooms if r.get("number") == num.group(1)), None)
            if r:
                return _res(r["area_m2"], "m2", f"Room {r['number']} ({r.get('name') or 'unnamed'})", [r["id"]])
        m = UNIT_RE.search(question)
        if m:
            u = m.group(1).upper()
            rs = [r for r in indoor if r.get("unit") == u]
            if rs:
                return _res(area_of(rs), "m2", f"Sum of {len(rs)} indoor rooms of apartment {u}", ids(rs))
        if name and re.search(LABEL, q):
            rs = [r for r in rooms if same(r)]
            return _res(area_of(rs), "m2", f"Sum of {len(rs)} rooms labelled '{name}'", ids(rs))
        if re.search(r"total|gesamt|totale|toutes|all", q):
            return _res(area_of(indoor), "m2", f"Sum of all {len(indoor)} numbered indoor rooms", ids(indoor))
        return None

    if re.search(COUNT, q):
        if name and re.search(LABEL, q):
            rs = [r for r in rooms if same(r)]
            return _res(len(rs), "count", f"Rooms labelled '{name}'", ids(rs))
        if re.search(r"apartment|wohnung|appartement|appartament|residential unit", q):
            us = facts.get("units", [])
            return _res(len(us), "count", "Apartment boundaries", [u["id"] for u in us])
        if re.search(r"floors \(storeys\)|kerrosta", q):
            return _res(facts.get("storeys", 1), "count", "Separate floor drawings on the sheet", [])
        for pat, cat in ROOM_PATTERNS:
            if re.search(pat, q) and not re.search(r"toilet bowl|wc seat|wc-istuin|drawn", q):
                rs = [r for r in rooms if r.get("category") == cat]
                return _res(len(rs), "count", f"Rooms of type {cat}", ids(rs))
        for pat, types in OBJECT_PATTERNS:
            if re.search(pat, q):
                hit = [o for o in objs if o["type"] in types]
                return _res(len(hit), "count", f"Detected {' + '.join(types)}", [o["id"] for o in hit])
    return None


if __name__ == "__main__":
    f = {"rooms": [{"id": "r1", "number": "2.01", "name": "Cage d'escalier", "area_m2": 5.0},
                   {"id": "r2", "number": "2.02", "name": "Bain", "area_m2": 4.0, "unit": "A"}],
         "objects": [{"id": "o1", "type": "wc"}, {"id": "o2", "type": "washbasin"}], "units": [{"id": "A"}]}
    assert answer("How many rooms labelled 'Cage d'escalier' are there on this floor?", f)["value"] == 1
    assert answer("Combien de WC sont dessinés sur ce plan ?", f)["value"] == 1
    assert answer("Quanti lavabi sono disegnati in questa pianta?", f)["value"] == 1
    assert answer("What is the net floor area of room 2.02 ('Bain') in m²?", f)["value"] == 4.0
    assert answer("Wie gross ist die Nettowohnfläche von Wohnung A in m² (Summe)?", f)["value"] == 4.0
    print("ok")

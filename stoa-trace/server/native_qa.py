"""Deterministic answers computed from native source objects, never QA labels."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import unicodedata

from .extraction import extract_cached, extract_document, linked_model, relative_path


def _normal(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text or "")).casefold()
                   if not unicodedata.combining(c))


def _compact(text):
    return re.sub(r"[^a-z0-9]", "", _normal(text))


def _evidence(objects):
    keys = ("id", "label", "type", "page", "bbox", "polygon", "source_path", "guid", "properties")
    return [{k: obj[k] for k in keys if k in obj and obj[k] is not None} for obj in objects]


def _result(value, unit, objects, method, scope, warnings=None, calculation=None):
    evidence = _evidence(objects)
    result = {"answer": f"{value:g} {unit}" if isinstance(value, (float, int)) else str(value),
              "value": value, "unit": unit, "method": method, "status": "supported",
              "evidence": evidence, "scope": scope, "warnings": warnings or [],
              "evidence_complete": len(evidence) == len(objects),
              "spatial_evidence_complete": bool(objects) and all(o.get("bbox") for o in objects)}
    if calculation:
        result["calculation"] = calculation
    return result


def _count_question(question):
    return bool(re.search(r"\b(how many|number of|count|quanti|quante|wie viele|wieviele|combien|cuantos|cuantas|monta|mitu|antal)\b", _normal(question)))


def _area_question(question):
    return bool(re.search(r"\b(area|superficie|flache|pinta-ala|pind|netop|floor area)\b|m²|m2|ft²|ft2|square feet", _normal(question)))


_QUOTED_TEXT = r'''(?:"[^"]*"|'[^']*'|«[^»]*»|“[^”]*”|„[^“]*“)'''


def _without_model_titles(question):
    """Discard an introduced source title, never arbitrary quoted constraints."""
    return re.sub(r"\b(model|building|mudelis|gebaude)(?:\s+(?:named|called))?\s+"+_QUOTED_TEXT,
                  lambda match:match.group(1),_normal(question))


def _unsupported_constraints(question, cad=False):
    q=_without_model_titles(question)
    # Native handlers deliberately have no general property-filter parser.
    # Refuse these instead of silently counting/summing the unfiltered model.
    if cad:
        q=q.replace("interior doors and entrance doors together", "doors")
    return bool(re.search(r"\b(fire|rated|rating|wider|narrower|taller|shorter|larger|smaller|greater|less|more than|at least|at most|only|without|whose|steel|wooden|external|exterior|interior|bedrooms?)\b|\b(?:by|per) (?:floor|level|type)|[<>]=?|\bof type\b",q))


def _simple_count_language(question, extra=()):
    q=_without_model_titles(question)
    # Only known, explicitly quoted native labels may be removed. Blindly
    # replacing label words could erase a qualifier in e.g. "Office doors".
    known={_normal(phrase) for phrase in extra}
    q=re.sub(_QUOTED_TEXT,lambda match:" " if _normal(match.group(0)[1:-1]) in known else match.group(0),q)
    safe=set("how many number of count total the a an are is there in on at this that selected entire whole all model building drawn shown floor plan for storey storeys stories levels floors door doors window windows room rooms space spaces wall walls column columns beam beams stair stairs sanitary fixture fixtures residential units apartments labelled labeled interior entrance together and does contain have visible objects units mitu ust akent ruumi seina posti tala treppi korrust on mudelis korruse plaanil naidatud montako kuinka monta ikkunaa pohjapiirustuksessa kuvan piirustuksessa quante quanti sono rappresentati rappresentate disegnati disegnate questa pianta piano appartamenti unita abitative locali con la denominazione wie viele wohnungen raume sind auf diesem grundriss dargestellt geschoss der die das im gebaude fenster turen".split())
    return all(token in safe for token in re.findall(r"[a-z]+",q))


def _target_class(question):
    q = _without_model_titles(question)
    rules = [
        (r"sanitary fixtures?|sanita[a-z]*\s+fixture", ("IfcSanitaryTerminal", "sanitary_fixture")),
        (r"\b(doors?|porte|portas|turen|ture|ovet|ovia|ust|uksed)\b", ("IfcDoor", "door")),
        (r"\b(windows?|finestre|fenster|ikkunat|ikkunaa|akent|aknad)\b", ("IfcWindow", "window")),
        (r"\b(rooms?|spaces?|raume|locali|ruumi|ruumid)\b", ("IfcSpace", "room")),
        (r"\b(walls?|wande|seinad|seina)\b", ("IfcWall",)),
        (r"\b(columns?|stutzen|posti|postid)\b", ("IfcColumn",)),
        (r"\b(beams?|balken|tala|talad)\b", ("IfcBeam",)),
        (r"\b(stairs?|treppen|treppi|trepid)\b", ("IfcStair",)),
        (r"\b(storeys?|stories|levels?|floors?|kerrosta|korrust|geschosse?)\b", ("IfcBuildingStorey",)),
    ]
    return next((classes for pattern, classes in rules if re.search(pattern, q)), None)


def _is_type(obj, types):
    typ = obj.get("type", "")
    return any(typ == cls or typ in {cls + "StandardCase", cls + "ElementedCase"} for cls in types)


def _load(path, root):
    return extract_cached(str(path), str(root), path.stat().st_mtime_ns)


def _ifc_scope(question, document, source_path, root):
    """Model scope and visible-floor scope are distinct and explicit."""
    q = _without_model_titles(question)
    model_path = source_path if source_path.suffix.lower() == ".ifc" else linked_model(source_path)
    if not model_path:
        return document, document.get("objects", []), "selected drawing", []
    model_doc = document if source_path.suffix.lower() == ".ifc" else _load(model_path, root)
    objects = model_doc.get("objects", [])
    storeys = model_doc.get("metadata", {}).get("storeys", [])
    scope_prefix=r"\b(?:on|of|at|in|floor|storey|level|korruse|korrusel|im)\s+[\"'«“„]?"
    selected_storeys = [s for s in storeys if s.get("name") and
                       re.search(scope_prefix + re.escape(_normal(s["name"])) + r"(?!\w)", q)]
    if not selected_storeys:
        aliases = {"ground":("erdgeschoss","ground","1.korrus","stue"),
                   "basement":("keller","basement","kelder","kælder","keldri")}
        for english,names in aliases.items():
            if re.search(r"\b"+english+r"\b",q):
                selected_storeys = [s for s in storeys if any(n in _normal(s.get("name")) for n in names)]
                break
    page_requested = document.get("metadata",{}).get("requested_scope")=="page"
    if page_requested:
        if source_path.suffix.lower()==".ifc":
            return model_doc,[],"Selected drawing page",["An IFC page must be resolved to its selected 2D view first."]
        projections={o["guid"]:o for o in document.get("objects",[]) if o.get("guid")}
        selected=[]
        for obj in objects:
            if obj.get("guid") in projections:
                p=projections[obj["guid"]]
                selected.append({**obj,**{k:p[k] for k in ("bbox","polygon","source_path","page") if k in p}})
        if selected_storeys and not any(o.get("properties",{}).get("storey_guid")==selected_storeys[0]["guid"] for o in selected):
            return model_doc,[],"Selected drawing page",["The requested storey differs from the selected page."]
        return model_doc,selected,"Visible objects on selected floor drawing",[]
    if len(selected_storeys) == 1:
        storey = selected_storeys[0]
        # If a generated floor view exists, prefer its explicitly visible GUID
        # set for a question asking what that floor plan shows.
        views = model_doc.get("metadata", {}).get("linked_views", [])
        match = [v for v in views if "_plan-" in Path(v).stem and
                 _compact(Path(v).stem.split("_plan-", 1)[1].split("-",1)[-1]) == _compact(storey["name"])]
        if len(match) == 1 and re.search(r"plan|shown|n[aä]idatud|plaan|drawing", q):
            view = root / match[0]
            if view.exists():
                view_doc = _load(view, root)
                ids = {o.get("guid") for o in view_doc["objects"] if o.get("guid")}
                if ids:
                    projection = {o["guid"]:o for o in view_doc["objects"] if o.get("guid")}
                    selected = []
                    for obj in objects:
                        if obj.get("guid") in ids:
                            p = projection[obj["guid"]]
                            selected.append({**obj, **{k:p[k] for k in ("bbox","polygon","source_path","page") if k in p}})
                    return model_doc, selected, f"Visible objects on {storey['name']}", []
        return model_doc, [o for o in objects if o.get("properties", {}).get("storey_guid") == storey["guid"]], f"Storey {storey['name']}", []
    whole = (not page_requested and bool(re.search(r"\b(model|mudel|gebaude|building)\b", q))
             and not re.search(r"this floor|selected floor|on this plan", q))
    floor_request = bool(re.search(r"(?:on|of|at) (?:the )?(?:ground|first|second|third|basement|floor|level)|this floor|selected floor|on this plan",q))
    if source_path.suffix.lower()==".ifc" and floor_request and not selected_storeys:
        return model_doc, [], "Unresolved floor scope", ["The requested floor could not be matched to one model storey."]
    if whole or (not page_requested and source_path.suffix.lower() == ".ifc" and not re.search(r"this floor|selected floor|on this plan", q)):
        return model_doc, objects, "Entire linked IFC model", []
    view_objects = document.get("objects", [])
    visible_ids = {o.get("guid") for o in view_objects if o.get("guid")}
    if visible_ids:
        projection = {o["guid"]:o for o in view_objects if o.get("guid")}
        selected = [{**o, **{k:projection[o["guid"]][k] for k in ("bbox","polygon","source_path","page") if k in projection[o["guid"]]}}
                    for o in objects if o.get("guid") in visible_ids]
        return model_doc, selected, "Visible objects on selected floor drawing", []
    return model_doc, [], "Unresolved floor scope", ["A floor must be selected before this question can be counted."]


def _native_ifc(question, document, source_path, root):
    if source_path.suffix.lower() != ".ifc" and not linked_model(source_path):
        return None
    doc, scoped, scope, warnings = _ifc_scope(question, document, source_path, root)
    if warnings or not scoped:
        return None
    q = _normal(question)
    types = _target_class(question)
    if _count_question(question) and types and not _area_question(question):
        known_storeys=[s['name'] for s in doc.get('metadata',{}).get('storeys',[])
                       if s.get('name') and re.search(
                           r"\b(?:on|of|at|in|floor|storey|level|korruse|korrusel|im)\s+[\"'«“„]?"+
                           re.escape(_normal(s['name']))+r"(?!\w)",_without_model_titles(question))]
        if not _simple_count_language(question,extra=known_storeys):
            return None
        if _unsupported_constraints(question) or re.search(r"\bwith\b|\b(?:wide|width|height|high|exclude|excluding|except)\b",q):
            return None
        # A multi-quantity question belongs to the reasoning fallback.
        if re.search(r"\b(?:and|with)\b", q) and sum(bool(re.search(p,q)) for p in
                (r"\bdoors?\b",r"\bwindows?\b",r"\brooms?\b",r"\bwalls?\b",r"\bcolumns?\b",r"\bbeams?\b",r"\bstairs?\b",r"\blevels?\b"))>1:
            return None
        selected = [o for o in scoped if _is_type(o, types)]
        if "sanitary_fixture" in types:
            sanitary = r"lavatory|sink|water closet|toilet|urinal|shower|bathtub|drinking fountain|mop basin"
            selected += [o for o in scoped if o.get("type") == "IfcFlowTerminal" and re.search(sanitary, _normal(o.get("label")))]
        unique = {o.get("guid") or o["id"]: o for o in selected}
        noun = {"IfcDoor":"doors", "IfcWindow":"windows", "IfcSpace":"rooms/spaces",
                "IfcWall":"walls", "IfcColumn":"columns", "IfcBeam":"beams",
                "IfcStair":"stairs", "IfcBuildingStorey":"storeys", "IfcSanitaryTerminal":"sanitary fixtures"}.get(types[0], "objects")
        result = _result(len(unique), "count", list(unique.values()), "native_ifc_entity_count", scope,
                         ["Counts describe modeled instances, not an independently checked as-built inventory."])
        result["answer"] = f"{len(unique)} {noun}."
        result["calculation"] = {"operation":"count_distinct_guid", "classes":list(types), "count":len(unique)}
        return result
    if _area_question(question):
        rooms = [o for o in scoped if o.get("type") == "IfcSpace"]
        quoted = re.findall(r"['\"«“„]([^'\"»”“]+)['\"»”“]", question)
        selected = []
        for room in rooms:
            p = room.get("properties", {})
            aliases = [room.get("label"), p.get("name"), p.get("long_name")]
            room_alias = f"{p.get('long_name') or ''} ({p.get('name') or ''})"
            aliases.append(room_alias)
            if any(_compact(a) == _compact(label) for a in aliases if a for label in quoted):
                selected.append(room)
        if not selected:
            selected = [o for o in rooms if len(_compact(o.get("label"))) > 3 and _normal(o.get("label")) in q]
        if selected and all("net_area_m2" in o["properties"] for o in selected):
            total = round(sum(o["properties"]["net_area_m2"] for o in selected), 4)
            return _result(total, "m²", selected, "native_ifc_quantity", scope,
                           calculation={"operation":"sum", "property":"net_area_m2",
                                        "terms":[o["properties"]["net_area_m2"] for o in selected]})
    if "software" in q or "ifc standard" in q or "ifc version" in q:
        return None  # Header text remains available for a sourced model fallback.
    return None


def _native_cad(question, document):
    objects = document.get("objects", [])
    rooms = [o for o in objects if o.get("type") == "room"]
    if not rooms:
        return None
    q = _normal(question)
    if _unsupported_constraints(question, cad=True):
        return None
    label_context=[o["label"] for o in rooms] if _target_class(question)==("IfcSpace","room") else ()
    if _count_question(question) and not _area_question(question) and not _simple_count_language(question,extra=label_context):
        return None
    units = [o for o in objects if o.get("type") == "apartment"]
    if _count_question(question) and not _area_question(question) and re.search(r"apartments?|residential units?|appartamenti|wohnungen|logements|asunto", q):
        if not units:
            return None
        result = _result(len(units), "count", units, "native_cad_unit_outlines", "Selected floor drawing")
        result["answer"] = f"{len(units)} residential units."
        return result
    if _count_question(question) and not _area_question(question):
        types = _target_class(question)
        if types and types[0] in ("IfcDoor", "IfcWindow"):
            selected = [o for o in objects if o.get("type") == types[1]]
            if selected or types[1] in document.get("metadata", {}).get("semantic_inventory", {}):
                result = _result(len(selected), "count", selected, "native_cad_symbol_inventory", "Selected floor drawing")
                result["answer"] = f"{len(selected)} {types[1]}s."
                return result
    labels = {_normal(o["label"]):o["label"] for o in rooms if o["label"] != "Room"}
    mentioned = [label for label in labels if re.search(r"(?<!\w)"+re.escape(label)+r"(?!\w)", q)]
    chosen = [o for o in rooms if _normal(o["label"]) in mentioned] if mentioned else []
    numbers = re.findall(r"\b\d+\.\d+(?:\.\d+)?\b", question)
    if numbers:
        numbered = [o for o in rooms if o["properties"].get("room_number") in numbers]
        if not numbered:
            return None
        chosen = numbered
    if _count_question(question) and mentioned and not _area_question(question):
        result = _result(len(chosen), "count", chosen, "native_cad_room_labels", "Selected floor drawing")
        result["answer"] = f"{len(chosen)} rooms labelled {', '.join(labels[x] for x in mentioned)}."
        return result
    if not _area_question(question):
        return None
    apartment = re.search(r"(?:apartment|appartamento|wohnung|appartement|unit)\s+([a-z])\b", q)
    if apartment:
        letter = apartment.group(1)
        selected_units = [u for u in units if re.search(r"\b"+re.escape(letter)+r"\b", _normal(u["label"]))]
        if len(selected_units) != 1:
            return None
        chosen = [o for o in rooms if o["properties"].get("unit_id") == selected_units[0]["id"]]
    if not chosen and re.search(r"all|total|tous|totale|gesamt|alle|insgesamt", q):
        chosen = [o for o in rooms if o["properties"].get("room_number")]
    if re.search(r"indoor|interior|interne|interni|net floor area of apartment|netta dell'appartamento|excluding|exclus|esclus|ohne", q):
        outdoors = r"balcon|balkon|loggia|terrass|outdoor|shaft|void|schacht|caved|vuoto|luftraum"
        chosen = [o for o in chosen if not re.search(outdoors, _normal(o["label"]))
                  and o["properties"].get("spatial_kind") != "shaft_or_void"]
    if not chosen or not all("net_area_m2" in o["properties"] for o in chosen):
        return None
    terms = [o["properties"]["net_area_m2"] for o in chosen]
    total = round(sum(terms), 4)
    result = _result(total, "m²", chosen, "native_cad_area_annotations", "Selected floor drawing",
                     calculation={"operation":"sum", "property":"native area annotations",
                                  "terms":terms, "result":total})
    result["answer"] = f"{total:g} m², from {len(chosen)} room area annotation{'s' if len(chosen) != 1 else ''}."
    return result


def _schedule_rows(document):
    """Identify table roles using column headers, keeping each original row."""
    doors = [o for o in document.get("objects", []) if o.get("type") == "schedule_door"]
    rooms = [o for o in document.get("objects", []) if o.get("type") == "schedule_room"]
    if doors or rooms:
        return doors, rooms
    for table in document.get("metadata", {}).get("tables", []):
        rows = table.get("rows", [])
        for row in rows:
            values = [str(v or "").replace("\n", " ").strip() for v in row["values"]]
            if not values:
                continue
            first = values[0]
            if re.fullmatch(r"\d{2,4}\.[A-Z]\d?", first):
                doors.append({"id":row["id"], "label":"Door " + first, "type":"schedule_door", "page":table["page"],
                              "bbox":row["bbox"], "source_path":document["metadata"]["source_path"],
                              "properties":{"door_number":first, "cells":values}})
            elif re.fullmatch(r"\d{2,4}", first) and any(re.search(r"\d[\d,]*\s*(?:SF|S\.F\.|ft)", v, re.I) for v in values):
                area = next((re.search(r"([\d,]+(?:\.\d+)?)\s*(?:SF|S\.F\.|ft)", v, re.I) for v in values
                             if re.search(r"\d[\d,]*\s*(?:SF|S\.F\.|ft)", v, re.I)), None)
                rooms.append({"id":row["id"], "label":"Room " + first + " · " + (values[1] if len(values)>1 else ""),
                              "type":"schedule_room", "page":table["page"], "bbox":row["bbox"],
                              "source_path":document["metadata"]["source_path"],
                              "properties":{"room_number":first, "cells":values,
                                            "area_ft2":float(area.group(1).replace(",", ""))}})
    return doors, rooms


def _native_schedule(question, document):
    q = _normal(question)
    if not re.search(r"schedule|door\s+\d|room\s+\d", q):
        return None
    doors, rooms = _schedule_rows(document)
    if doors and "door" in q:
        selected = doors
        specific = re.search(r"\bdoor\s+(\d{2,4}\.[A-Z]\d?)", question, re.I)
        if specific:
            selected = [o for o in doors if o["properties"]["door_number"].casefold() == specific.group(1).casefold()]
            if len(selected) == 1 and not _count_question(question):
                props=selected[0]["properties"]
                fields=[field for word,field in (("width","width"),("height","height"),("hardware","hardware_group"),
                        ("door material","door_material"),("door type","door_type")) if word in q and field in props]
                if fields:
                    text="; ".join(field.replace("_"," ")+": "+props[field] for field in fields)
                    return _result(text, None, selected, "native_pdf_schedule_row", "Selected door schedule")
                return None
        door_type = re.search(r"door\s+type\s+([a-z]\d+)", q)
        if door_type:
            selected = [o for o in selected if o["properties"].get("door_type", "").casefold() == door_type.group(1)]
        materials = re.findall(r"\b(wd-\d|stl-\d|al-\d)\b", q)
        if materials:
            field="frame_material" if "frame" in q else "door_material"
            selected=[o for o in selected if o["properties"].get(field,"").casefold() in materials]
        note=re.search(r"\bnotes?\s+([a-c])\b",q)
        if note:
            selected=[o for o in selected if re.search(r"\b"+note.group(1)+r"\b",_normal(o["properties"].get("notes"))) ]
        dimension=re.search(r"(\d+\s*'\s*-\s*\d+(?:\s+\d/\d+)?\s*\")\s+(wide|high)",q)
        if dimension:
            field="width" if dimension.group(2)=="wide" else "height"
            compact=lambda v:re.sub(r"\s+","",v)
            selected=[o for o in selected if compact(o["properties"].get(field,""))==compact(dimension.group(1))]
        room = re.search(r"\broom\s+(\d{2,4})\b", q)
        if room:
            selected = [o for o in selected if o["properties"]["door_number"].startswith(room.group(1)+".")]
        simple_total=bool(re.search(r"how many doors?\s*\(door numbers\)\s*are listed|how many doors? are (?:listed )?in (?:the )?door schedule\??$|total number of doors\??$",q))
        if _count_question(question) and (door_type or room or materials or note or dimension or simple_total):
            result = _result(len(selected), "count", selected, "native_pdf_schedule_rows", "Selected door schedule")
            result["answer"] = f"{len(selected)} matching door schedule rows."
            return result
    if rooms and re.search(r"room|area|finish", q):
        selected = rooms
        room = re.search(r"\broom\s+(\d{2,4})\b", q)
        if room:
            selected = [o for o in rooms if o["properties"]["room_number"] == room.group(1)]
        named = re.search(r"rooms?\s+(?:named|labelled)\s+['\"]?([a-z ]+)", q)
        if named:
            name = named.group(1).split(" in ")[0].split(" on ")[0].strip()
            selected = [o for o in rooms if name in _normal(o["label"])]
        floor = re.search(r"\b(?:floor finish|finish)\s+(f\d+)\b",q)
        base = re.search(r"\bbase\b.*?\b(b\d+)\b",q)
        if floor:
            selected=[o for o in selected if floor.group(1) in _normal(o["properties"].get("floor_finish")).split()]
        if base:
            selected=[o for o in selected if o["properties"].get("base_finish","").casefold()==base.group(1)]
        locker="locker rooms" in q
        if locker:
            selected=[o for o in selected if "locker" in _normal(o["label"])]
        total=bool(re.search(r"total area of all rooms|all rooms that have an area listed",q))
        if _area_question(question) and selected and (room or named or floor or base or locker or total):
            terms = [o["properties"]["area_ft2"] for o in selected]
            result=_result(sum(terms), "ft²", selected, "native_pdf_schedule_area", "Selected finish schedule",
                           calculation={"operation":"sum", "terms":terms})
            if _count_question(question):
                result["answer"]=f"{len(selected)} rooms; combined area {sum(terms):g} ft²."
            return result
        if _count_question(question) and not _area_question(question) and (base or floor):
            return _result(len(selected),"count",selected,"native_pdf_schedule_rows","Selected finish schedule")
    return None


def answer_native(question: str, document: dict, source_path: Path, data_root: Path) -> dict | None:
    """Return a supported native answer, or None for model/vision fallback."""
    source_path, data_root = Path(source_path), Path(data_root)
    for handler in (
        lambda: _native_ifc(question, document, source_path, data_root),
        lambda: _native_cad(question, document),
        lambda: _native_schedule(question, document),
    ):
        result = handler()
        if result is not None:
            return result
    return None


native_answer = answer_native
answer_question = answer_native

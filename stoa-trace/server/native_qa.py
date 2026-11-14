"""Deterministic answers computed from native source objects, never QA labels."""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
from pathlib import Path
import math
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


def _measurement_question(question):
    return _area_question(question) or bool(re.search(r"\b(length|volume|longueur|volumen|pikkus|pikkus|pikkuse|maht)\b", _normal(question)))


def _measurement_language_supported(question, labels=()):
    """A native quantity needs a wholly resolved question, not one matching noun."""
    q = _without_model_titles(question)
    # A drawing title is context only when explicitly introduced before a comma.
    q = re.sub(r"^on sheet [\w.-]+ of .+? drawings,\s*", "", q)
    known = {_normal(v) for v in labels if v}
    for quoted in re.findall(_QUOTED_TEXT, q):
        if _normal(quoted[1:-1]) not in known:
            return False
    for label in sorted(known, key=len, reverse=True):
        if re.fullmatch(r"\d+", label):
            # A numeric room name is consumed only in an explicit selector.
            # Removing every known number can erase an unresolved second room
            # or a numeric size/floor condition.
            q = re.sub(r"\b(?:rooms?|spaces?)\s+['\"]?"+re.escape(label)+r"['\"]?(?!\w)", " room ", q)
        else:
            q = re.sub(r"(?<!\w)"+re.escape(label)+r"(?!\w)", " ", q)
    # An apartment selector letter ("apartment B") is part of the scope, not a free word.
    q = re.sub(r"\b(apartment|appartamento|wohnung|appartement|unit)\s+[a-z]\b", r" \1 ", q)
    exclusion = re.search(r"\b(?:excluding|except|without|ohne|esclusi|exclus)\b(.+)$", q)
    if exclusion:
        outdoor_words = set("balcony balconies balcon loggia loggias terrace terraces outdoor outdoors spaces space shafts shaft void voids other and or all the any balconies loggien terrassen balkone cavedi vuoti".split())
        if any(w not in outdoor_words for w in re.findall(r"[a-z]+", exclusion.group(1))):
            return False
        q = q[:exclusion.start()]+" outdoor "
    if re.search(r"[<>]|\b(?:more than|less than|between|over|under|at least|at most|only|with|whose|having|except)\b", q):
        return False
    if re.search(r"\d", re.sub(r"\b(?:m|ft)[23]\b", "", q)):
        return False
    safe = set("what is are the a an of for in on at this that selected entire whole all total combined sum summing its their from to net gross neto netto floor side area areas length volume room rooms space spaces wall walls slab slabs deck decks beam beams column columns building model storey level plan drawing drawn shown labelled labeled named numbered indoor interior outdoor residential unit apartment apartments schedule finish fieldhouse netta superficie flache gesamt alle raume totale m mm cm metres meters metre meter ft feet foot square cubic sqm sqft count calculate give find and".split())
    return all(word in safe for word in re.findall(r"[a-z]+", q))


def _quantity_key(question, target):
    q = _normal(question)
    if re.search(r"\bnet\b", q) and re.search(r"\bgross\b", q):
        return None
    if re.search(r"\bvolume\b", q):
        return "gross_volume_m3" if re.search(r"\bgross\b", q) else "net_volume_m3" if re.search(r"\bnet\b", q) else None
    if re.search(r"\blength\b", q):
        return "gross_length_m" if re.search(r"\bgross\b", q) else "net_length_m" if re.search(r"\bnet\b", q) else "length_m"
    if _area_question(question):
        prefix = "gross" if re.search(r"\bgross\b", q) else "net"
        if target == "IfcWall":
            return prefix+"_side_area_m2" if re.search(r"\bside\b", q) else None
        return prefix+"_area_m2"
    return None


def _finite_quantity(obj, key):
    value = obj.get("properties", {}).get(key)
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


# A single-quoted label may contain an apostrophe between letters ('Cage d'escalier').
# Whole-model words in the dataset languages, including inflections (et "mudelis", da "modellen").
_MODEL_WORDS = r"(?:model|modellen|modell|modele|modello|mudel\w*|gebaude|building|bygning\w*)"

_QUOTED_TEXT = r'''(?:"[^"]*"|'(?:[^']|(?<=\w)'(?=\w))*'|«[^»]*»|“[^”]*”|„[^“]*“)'''


def _without_model_titles(question):
    """Discard an introduced source title, never arbitrary quoted constraints."""
    return re.sub(r"\b("+_MODEL_WORDS+r")(?:\s+(?:named|called))?\s+"+_QUOTED_TEXT,
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
    safe=set("how many number of count total the a an are is there in on at this that selected entire whole all model building drawn shown floor plan for storey storeys stories levels floors door doors window windows room rooms space spaces wall walls column columns beam beams stair stairs sanitary fixture fixtures light lights lighting luminaire luminaires fitting fittings toilet toilets wc washbasin washbasins sink sinks bathtub bathtubs shower showers residential units apartments labelled labeled interior entrance together and does contain have visible objects units mitu ust akent ruumi seina posti tala treppi korrust on mudelis korruse plaanil naidatud montako kuinka monta ikkunaa pohjapiirustuksessa kuvan piirustuksessa quante quanti sono rappresentati rappresentate disegnati disegnate questa pianta piano appartamenti unita abitative locali con la denominazione wie viele wohnungen raume sind auf diesem grundriss dargestellt geschoss der die das im gebaude fenster turen".split())
    return all(token in safe for token in re.findall(r"[a-z]+",q))


def _target_class(question):
    q = _without_model_titles(question)
    rules = [
        (r"\b(toilets?|wc|water closets?)\b", ("IfcSanitaryTerminal", "toilet")),
        (r"\b(washbasins?|sinks?|lavabos?)\b", ("IfcSanitaryTerminal", "washbasin")),
        (r"\b(bathtubs?|baths?|baignoires?)\b", ("IfcSanitaryTerminal", "bathtub")),
        (r"\b(showers?|douches?)\b", ("IfcSanitaryTerminal", "shower")),
        (r"sanitary fixtures?|sanita[a-z]*\s+fixture", ("IfcSanitaryTerminal", "sanitary_fixture")),
        (r"\b(light(?:ing)? fixtures?|luminaires?|light fittings?)\b", ("IfcLightFixture", "light_fixture")),
        (r"\b(doors?|porte|portas|turen|ture|ovet|ovia|ust|uksed)\b", ("IfcDoor", "door")),
        (r"\b(windows?|finestre|fenster|ikkunat|ikkunaa|akent|aknad)\b", ("IfcWindow", "window")),
        (r"\b(rooms?|spaces?|raume|locali|ruumi|ruumid)\b", ("IfcSpace", "room")),
        (r"\b(walls?|wande|seinad|seina)\b", ("IfcWall",)),
        (r"\b(slabs?|decks?)\b", ("IfcSlab",)),
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


@lru_cache(maxsize=4)
def _source_model(path, modified_ns, size):
    import ifcopenshell
    return ifcopenshell.open(path)


def _ifc_model(source_path):
    path = source_path if source_path.suffix.lower() == '.ifc' else linked_model(source_path)
    if path is None:
        return None
    try:
        stat = path.stat()
        return _source_model(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except (OSError, RuntimeError, ValueError):
        return None


def _space_footprint_quantity(obj, model):
    """Measure one explicit, closed, planar space outline, never a bbox.

    Multiple rings, curves, mappings and missing units are deliberately outside
    this narrow geometry path. A footprint is not substituted for a gross area.
    """
    try:
        import ifcopenshell.util.unit as unit_util
        from shapely.geometry import Polygon
        space = model.by_guid(obj.get('guid'))
        if not space or not space.is_a('IfcSpace'):
            return None
        projects = model.by_type('IfcProject')
        assignments = [p.UnitsInContext for p in projects if p.UnitsInContext]
        if len(assignments) != 1 or not any(getattr(u, 'UnitType', None) == 'LENGTHUNIT'
                                            for u in assignments[0].Units):
            return None
        scale = unit_util.calculate_unit_scale(model)
        if not math.isfinite(scale) or scale <= 0:
            return None
        representation = getattr(space, 'Representation', None)
        footprints = [r for r in getattr(representation, 'Representations', ())
                      if str(r.RepresentationIdentifier or '').casefold() == 'footprint']
        if len(footprints) != 1:
            return None
        curves = []
        for item in footprints[0].Items:
            if item.is_a('IfcGeometricCurveSet'):
                curves.extend(item.Elements)
            elif item.is_a('IfcPolyline'):
                curves.append(item)
            else:
                return None
        if len(curves) != 1 or not curves[0].is_a('IfcPolyline'):
            return None
        points = [tuple(float(v) for v in p.Coordinates) for p in curves[0].Points]
        if (len(points) < 4 or len({len(p) for p in points}) != 1
                or len(points[0]) not in {2, 3} or not all(math.isfinite(v) for p in points for v in p)):
            return None
        if math.dist(points[0], points[-1]) > 1e-7:
            return None
        if len(points[0]) == 3 and max(p[2] for p in points) - min(p[2] for p in points) > 1e-7:
            return None
        shape = Polygon([(p[0], p[1]) for p in points])
        if not shape.is_valid or shape.is_empty or shape.area <= 0:
            return None
        value = float(shape.area) * scale ** 2
        if not math.isfinite(value) or value <= 0:
            return None
        return {'value': value, 'unit': 'm²', 'property_path': 'IfcSpace.Representation.FootPrint',
                'unit_basis': 'project LENGTHUNIT squared', 'length_unit_scale': scale,
                'representation_id': footprints[0].id(), 'curve_id': curves[0].id(),
                'basis': 'single closed straight planar IfcSpace footprint; no bounding-box approximation'}
    except (AttributeError, ImportError, KeyError, OSError, RuntimeError, TypeError, ValueError):
        return None


def _space_floor_face_quantity(obj, model):
    """Area of the lowest downward-facing faces of the IfcSpace body, for spaces without a
    footprint representation. Exact mesh faces in world coordinates, never a bounding box."""
    try:
        import ifcopenshell.geom
        import numpy as np
        space = model.by_guid(obj.get('guid'))
        if not space or not space.is_a('IfcSpace'):
            return None
        settings = ifcopenshell.geom.settings()
        settings.set('use-world-coords', True)
        geometry = ifcopenshell.geom.create_shape(settings, space).geometry
        v = np.array(geometry.verts, dtype=float).reshape(-1, 3)
        t = np.array(geometry.faces, dtype=int).reshape(-1, 3)
        if not len(t):
            return None
        a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
        n = np.cross(b - a, c - a)
        length = np.linalg.norm(n, axis=1)
        down = n[:, 2] / np.maximum(length, 1e-12) < -0.999
        low = (a[:, 2] + b[:, 2] + c[:, 2]) / 3 < v[:, 2].min() + 0.001
        value = float(length[down & low].sum() / 2)
        if not math.isfinite(value) or value <= 0:
            return None
        return {'value': value, 'unit': 'm²', 'property_path': 'IfcSpace.Body.lowest_downward_faces',
                'unit_basis': 'world coordinates in metres (geometry kernel)',
                'basis': 'area of the lowest downward-facing faces of the space body; no bounding-box approximation'}
    except Exception:
        return None


def _room_quantity(obj, key, model):
    """Keep exact source quantities, resolving only missing/ambiguous net area."""
    props = obj.get('properties', {})
    if key in props.get('ambiguous_quantities', []):
        return None  # Geometry cannot select between conflicting explicit values.
    if _finite_quantity(obj, key):
        if props[key] != 0 or key != 'net_area_m2':
            return obj
        source = (props.get('quantity_sources') or {}).get(key)
        area_name = re.sub(r'[^a-z]', '', str(props.get('area_source', '')).rsplit('.', 1)[-1].casefold())
        if source or area_name in {'netarea', 'netfloorarea', 'nettoflache', 'nettogeschossflache', 'nutzflache'}:
            return obj  # A genuine typed zero is never replaced just for being zero.
    elif key in props:
        return None  # An invalid negative/nonfinite source value is not a missing field.
    if key != 'net_area_m2' or model is None:
        return None
    quantity = _space_footprint_quantity(obj, model) or _space_floor_face_quantity(obj, model)
    if quantity is None:
        return None
    updated = dict(props)
    if key in props:
        updated['reported_exporter_area_m2'] = props[key]
        updated['reported_exporter_area_source'] = props.get('area_source')
    updated.update(net_area_m2=quantity['value'], area_source=quantity['property_path'],
                   area_unit_basis=quantity['unit_basis'], geometry_area_m2=quantity['value'])
    updated['quantity_sources'] = {**(props.get('quantity_sources') or {}), key: quantity}
    return {**obj, 'properties': updated}


def _represented_stairs(scoped, model_doc, source_path):
    """Count stair assemblies represented by flights, never flights as stairs."""
    selected = {o.get('guid') or o['id']: o for o in scoped
                if _is_type(o, ('IfcStair',)) and not o.get('properties', {}).get('nested_in')}
    flights = [o for o in scoped if o.get('type') == 'IfcStairFlight']
    if not flights:
        return list(selected.values())
    model = _ifc_model(source_path)
    if model is None:
        return None
    records = {o.get('guid'): o for o in model_doc.get('objects', []) if o.get('guid')}
    try:
        import ifcopenshell.util.element as element_util
        for flight in flights:
            entity = model.by_guid(flight.get('guid'))
            visited = set()
            while entity and not entity.is_a('IfcStair'):
                if entity.id() in visited:
                    return None
                visited.add(entity.id())
                entity = element_util.get_aggregate(entity)
            if entity is None or entity.GlobalId not in records:
                return None
            parent = records[entity.GlobalId]
            if not _is_type(parent, ('IfcStair',)):
                return None
            copied = {**parent, 'properties': dict(parent.get('properties', {}))}
            props = copied['properties']
            props['count_basis'] = 'distinct IfcStair assembly represented by aggregated visible flights'
            previous = selected.get(entity.GlobalId, {}).get('properties', {}).get('represented_flight_guids', [])
            props['represented_flight_guids'] = sorted(set(previous) | {flight['guid']})
            selected[entity.GlobalId] = copied
    except (AttributeError, ImportError, KeyError, RuntimeError, TypeError, ValueError):
        return None
    return list(selected.values())


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
        # A storey's plan shows what the storey contains (IFC spatial containment). A rendered
        # view can omit products that are cut or hidden, so it never decides what is counted;
        # it only supplies drawing positions for the contained objects it shows.
        contained = [o for o in objects if o.get("properties", {}).get("storey_guid") == storey["guid"]]
        views = model_doc.get("metadata", {}).get("linked_views", [])
        match = [v for v in views if "_plan-" in Path(v).stem and
                 _compact(Path(v).stem.split("_plan-", 1)[1].split("-",1)[-1]) == _compact(storey["name"])]
        if len(match) == 1 and (root / match[0]).exists():
            view_doc = _load(root / match[0], root)
            projection = {o["guid"]: o for o in view_doc["objects"] if o.get("guid")}
            contained = [{**o, **{k: projection[o["guid"]][k] for k in ("bbox", "polygon", "source_path", "page")
                                  if k in projection[o["guid"]]}} if o.get("guid") in projection else o
                         for o in contained]
        return model_doc, contained, f"Storey {storey['name']}", []
    whole = (not page_requested and bool(re.search(r"\b"+_MODEL_WORDS+r"\b", q))
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
        # Without the model, a semantic plan view (SVG with IFC class + GUID per product) can
        # still answer what this floor drawing shows. Whole-model questions stay unanswered.
        visible_plan = (bool(document.get("metadata", {}).get("semantic_svg")) and _count_question(question)
                        and bool(re.search(r"\b(?:shown|drawn|plan|grundriss|dargestellt|naidatud|plaanil|vist|tegning)\b", _normal(question)))
                        and not re.search(r"\b" + _MODEL_WORDS + r"\b", _without_model_titles(question)))
        if not visible_plan:
            return None
    doc, scoped, scope, warnings = _ifc_scope(question, document, source_path, root)
    if warnings or not scoped:
        return None
    q = _normal(question)
    types = _target_class(question)
    if _count_question(question) and types and not _measurement_question(question):
        storey_names=[s['name'] for s in doc.get('metadata',{}).get('storeys',[]) if s.get('name')]
        if not storey_names and source_path.suffix.lower() != ".ifc":
            # A plan view without its model: the only floor it can describe is its own level,
            # which plan exports carry in their file name.
            storey_names=[m[1:-1] for m in re.findall(_QUOTED_TEXT, question)
                          if len(_compact(m[1:-1])) > 2 and _compact(m[1:-1]) in _compact(source_path.stem)]
        known_storeys=[name for name in storey_names
                       if re.search(
                           r"\b(?:on|of|at|in|floor|storey|level|korruse|korrusel|im)\s+[\"'«“„]?"+
                           re.escape(_normal(name))+r"(?!\w)",_without_model_titles(question))]
        if not _simple_count_language(question,extra=known_storeys):
            return None
        if _unsupported_constraints(question) or re.search(r"\bwith\b|\b(?:wide|width|height|high|exclude|excluding|except)\b",q):
            return None
        # A multi-quantity question belongs to the reasoning fallback.
        if re.search(r"\b(?:and|with)\b", q) and sum(bool(re.search(p,q)) for p in
                (r"\bdoors?\b",r"\bwindows?\b",r"\brooms?\b",r"\bwalls?\b",r"\bcolumns?\b",r"\bbeams?\b",r"\bstairs?\b",r"\blevels?\b"))>1:
            return None
        # Parts aggregated into another product are not separate instances of their class.
        selected = [o for o in scoped if _is_type(o, types) and not o.get("properties", {}).get("nested_in")]
        if types == ('IfcStair',):
            selected = _represented_stairs(scoped, doc, source_path)
            if selected is None:
                return None
        if len(types) > 1 and types[1] in {"toilet", "washbasin", "bathtub", "shower"}:
            synonyms = {"toilet": r"\b(toilet|wc|water closet|wcseat)\b", "washbasin": r"\b(sink|washbasin|lavatory|basin)\b",
                        "bathtub": r"\b(bathtub|bath|tub)\b", "shower": r"\bshower\b"}
            classified = []
            for obj in selected:
                text = _normal(str(obj.get("properties", {}).get("predefined_type") or "")+" "+obj.get("label", ""))
                if not any(re.search(pattern, text) for pattern in synonyms.values()):
                    return None
                if re.search(synonyms[types[1]], text):
                    classified.append(obj)
            selected = classified
        if "light_fixture" in types:
            selected += [o for o in scoped if o.get("type") == "IfcFlowTerminal"
                         and o.get("properties", {}).get("element_type_class") == "IfcLightFixtureType"]
        if "sanitary_fixture" in types:
            sanitary = r"lavatory|sink|water closet|toilet|urinal|shower|bathtub|drinking fountain|mop basin"
            # IFC2X3 has no IfcSanitaryTerminal: fixtures are flow terminals typed by IfcSanitaryTerminalType.
            selected += [o for o in scoped if o.get("type") == "IfcFlowTerminal" and (
                o.get("properties", {}).get("element_type_class") == "IfcSanitaryTerminalType"
                or re.search(sanitary, _normal(o.get("label"))))]
        unique = {o.get("guid") or o["id"]: o for o in selected}
        noun = {"IfcDoor":"doors", "IfcWindow":"windows", "IfcSpace":"rooms/spaces",
                "IfcWall":"walls", "IfcColumn":"columns", "IfcBeam":"beams",
                "IfcStair":"stairs", "IfcBuildingStorey":"storeys", "IfcSanitaryTerminal":"sanitary fixtures"}.get(types[0], "objects")
        result = _result(len(unique), "count", list(unique.values()), "native_ifc_entity_count", scope,
                         ["Counts describe modeled instances, not an independently checked as-built inventory."])
        result["answer"] = f"{len(unique)} {noun}."
        result["calculation"] = {"operation":"count_distinct_guid", "classes":list(types), "count":len(unique)}
        return result
    if _measurement_question(question):
        # Quoted labels are names, not element classes: 'INVA-WC (103)' is a room, not a toilet.
        types = _target_class(re.sub(_QUOTED_TEXT, " ", question))
        target = types[0] if types else "IfcSpace"
        if target not in {"IfcSpace", "IfcWall", "IfcSlab", "IfcBeam", "IfcColumn"}:
            return None
        key = _quantity_key(question, target)
        if key is None:
            return None
        labels = [s.get("name") for s in doc.get("metadata", {}).get("storeys", [])]
        labels += [o.get("label") for o in scoped]
        labels += [str(o.get("properties", {}).get(k) or "") for o in scoped for k in ("name", "long_name")]
        labels += [f"{o.get('properties', {}).get('long_name') or ''} ({o.get('properties', {}).get('name') or ''})" for o in scoped]
        if not _measurement_language_supported(question, labels):
            return None
        if target != "IfcSpace":
            selected = [o for o in scoped if _is_type(o, (target,))]
            if not re.search(r"\b(total|all|sum|combined)\b", q):
                return None
            if not selected or not all(_finite_quantity(o, key) for o in selected):
                return None
            terms = [o["properties"][key] for o in selected]
            unit = "m³" if key.endswith("m3") else "m²" if key.endswith("m2") else "m"
            return _result(round(sum(terms), 6), unit, selected, "native_ifc_quantity", scope,
                           calculation={"operation": "sum", "property": key, "terms": terms,
                                        "unit": unit, "basis": "explicit native quantities; no missing terms"})
        rooms = [o for o in scoped if o.get("type") == "IfcSpace"]
        quoted = [m[1:-1] for m in re.findall(_QUOTED_TEXT, question)]
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
        identifiers = re.findall(r"\b(?:rooms?|spaces?)\s+['\"]?([a-z]?\d+(?:[.\-]\d+)*)\b", q)
        if len(identifiers) > 1:
            return None
        identifier = re.search(r"\b(?:rooms?|spaces?)\s+['\"]?([a-z]?\d+(?:[.\-]\d+)*)\b", q)
        if identifier:
            selected = [o for o in rooms if identifier.group(1) in {
                _normal(o.get("properties", {}).get("name")), _normal(o.get("properties", {}).get("room_number"))}]
            if len(selected) != 1:
                return None
        if not selected and re.search(r"\b(?:all|total)\b", q):
            selected = rooms
        if len(selected) > 1 and not re.search(r"\b(?:all|total|sum|combined|rooms labelled|rooms labeled|rooms named)\b", q):
            return None
        if selected:
            needs_geometry = any(not _finite_quantity(o, key) or o.get('properties', {}).get(key) == 0 for o in selected)
            model = _ifc_model(source_path) if needs_geometry else None
            selected = [_room_quantity(o, key, model) for o in selected]
            if any(o is None for o in selected):
                return None
            total = round(sum(o["properties"][key] for o in selected), 4)
            unit = "m³" if key.endswith("m3") else "m²" if key.endswith("m2") else "m"
            geometry = any(o['properties'].get('area_source') in ('IfcSpace.Representation.FootPrint', 'IfcSpace.Body.lowest_downward_faces') for o in selected)
            return _result(total, unit, selected, "native_ifc_quantity", scope,
                           warnings=['Missing or zero untyped exporter areas were replaced by measurements of explicit closed IfcSpace footprints. This is geometry-derived area, not an explicit net-area quantity.'] if geometry else None,
                           calculation={"operation":"sum", "property":key,
                                        "terms":[o["properties"][key] for o in selected],
                                        "basis": 'source quantities and explicitly identified space footprint geometry' if geometry else 'source quantities'})
    if re.search(r"\b(project information|site location|building details|project name|site name)\b", q):
        # A bounded factual header view. It does not infer building usage or
        # geocode locations absent from the IFC source.
        if any(word not in set("what is are the and project information site location building details name for this model give list describe".split())
               for word in re.findall(r"[a-z]+", _without_model_titles(question))):
            return None
        selected = [o for o in doc.get("objects", []) if o.get("type") in {"IfcProject", "IfcSite", "IfcBuilding"}]
        if selected:
            lines = []
            for obj in selected:
                props = {k: v for k, v in obj.get("properties", {}).items()
                         if k in {"name", "long_name", "description", "RefLatitude", "RefLongitude", "RefElevation", "Phase", "ObjectType"} and v is not None}
                lines.append(obj["type"]+": "+"; ".join(f"{k}: {v}" for k, v in props.items()))
            return _result("\n".join(lines), None, selected, "native_ifc_project_records", "IFC project/site/building records",
                           warnings=["Only explicit IFC fields are shown; location and usage are not independently inferred."])
    if "software" in q or "ifc standard" in q or "ifc version" in q:
        return None  # Header text remains available for a sourced model fallback.
    return None


def _native_cad(question, document):
    objects = document.get("objects", [])
    rooms = [o for o in objects if o.get("type") == "room"]
    if not rooms and not document.get("metadata", {}).get("semantic_inventory"):
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
        if types and len(types) > 1 and types[1] in {"door", "window", "toilet", "washbasin", "bathtub", "shower"}:
            selected = [o for o in objects if o.get("type") == types[1]]
            if selected or types[1] in document.get("metadata", {}).get("semantic_inventory", {}):
                result = _result(len(selected), "count", selected, "native_cad_symbol_inventory", "Selected floor drawing")
                result["answer"] = f"{len(selected)} {types[1]}s."
                return result
    labels = {_normal(o["label"]):o["label"] for o in rooms if o["label"] != "Room"}
    mentioned = [label for label in labels if re.search(r"(?<!\w)"+re.escape(label)+r"(?!\w)", q)]
    # A quoted label is exact: 'Wohnen/Essen' must not also select rooms named Wohnen or Essen.
    quoted = [_normal(m[1:-1]).strip() for m in re.findall(_QUOTED_TEXT, question)]
    if any(label in labels for label in quoted):
        mentioned = [label for label in quoted if label in labels]
    chosen = [o for o in rooms if _normal(o["label"]) in mentioned] if mentioned else []
    numbers = re.findall(r"\b[A-Za-z]?\d+[.\-]\d+(?:[.\-]\d+)?\b", question)
    if numbers:
        numbered = [o for o in rooms if str(o["properties"].get("room_number", "")).casefold() in {n.casefold() for n in numbers}]
        if not numbered:
            return None
        chosen = numbered
    if _count_question(question) and mentioned and not _area_question(question):
        result = _result(len(chosen), "count", chosen, "native_cad_room_labels", "Selected floor drawing")
        result["answer"] = f"{len(chosen)} rooms labelled {', '.join(labels[x] for x in mentioned)}."
        return result
    if not _area_question(question):
        return None
    if _quantity_key(question, "IfcSpace") != "net_area_m2":
        return None
    known = [o["label"] for o in rooms]+[o.get("properties", {}).get("room_number") for o in rooms]
    if not _measurement_language_supported(question, known):
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
                  and o["properties"].get("spatial_kind") not in ("shaft_or_void", "outdoor")]
    if not chosen or not all("net_area_m2" in o["properties"] for o in chosen):
        return None
    if len(chosen) > 1 and not re.search(r"\b(?:all|total|sum|summing|combined|apartment|wohnung|appartamento|rooms labelled|rooms labeled|rooms named)\b", q):
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


def _schedule_language_supported(question, consumed=(), labels=()):
    q = _normal(question)
    q = re.sub(r"^on sheet [\w.-]+ of .+? drawings(?:\s*\([^)]*\))?,\s*", "", q)
    for text in consumed:
        if text:
            q = q.replace(_normal(text), " ")
    for label in labels:
        q = re.sub(r"(?<!\w)"+re.escape(_normal(label))+r"(?!\w)", " ", q)
    if re.search(r"[<>]", q) or re.search(r"\d", re.sub(r"\b(?:m|ft)[23]\b", "", q)):
        return False
    safe = set("how many what is are the a an of for in on at this that selected all total combined sum number numbers doors door rooms room schedule schedules finish listed list have has with which that do does shown area areas width height hardware material type group and from to square feet foot ft sf m sqm meters metres mm cm named labelled labeled floor base notes note".split())
    return all(token in safe for token in re.findall(r"[a-z]+", q))


def _dimension_metres(value):
    """Parse explicit metric values or architectural feet/inches, never bare units."""
    text = str(value or "").strip().casefold().replace("’", "'").replace("″", '"')
    metric = re.fullmatch(r"([0-9]+(?:[.,][0-9]+)?)\s*(mm|cm|m|ft|feet|in|inch|inches)", text)
    if metric:
        return float(metric.group(1).replace(",", "."))*{"mm": .001, "cm": .01, "m": 1, "ft": .3048, "feet": .3048, "in": .0254, "inch": .0254, "inches": .0254}[metric.group(2)]
    imperial = re.fullmatch(r"(\d+)\s*'\s*-?\s*(\d+)(?:\s+(\d+)\s*/\s*(\d+))?\s*\"", text)
    if imperial:
        feet, inches, numerator, denominator = imperial.groups()
        if denominator and int(denominator) == 0:
            return None
        return (int(feet)*12+int(inches)+(int(numerator)/int(denominator) if numerator else 0))*.0254
    return None


def _native_schedule(question, document):
    q = _normal(question)
    if not re.search(r"schedule|door\s+\d|room\s+\d", q):
        return None
    doors, rooms = _schedule_rows(document)
    if doors and "door" in q:
        selected = doors
        consumed = []
        specific = re.search(r"\bdoor\s+(\d{2,4}\.[A-Z]\d?)", question, re.I)
        if specific:
            consumed.append(specific.group(0))
            selected = [o for o in doors if o["properties"]["door_number"].casefold() == specific.group(1).casefold()]
            if len(selected) == 1 and not _count_question(question):
                if not _schedule_language_supported(question, consumed):
                    return None
                props=selected[0]["properties"]
                fields=[field for word,field in (("width","width"),("height","height"),("hardware","hardware_group"),
                        ("door material","door_material"),("door type","door_type")) if word in q and field in props]
                if fields:
                    text="; ".join(field.replace("_"," ")+": "+props[field] for field in fields)
                    return _result(text, None, selected, "native_pdf_schedule_row", "Selected door schedule")
                return None
        door_type = re.search(r"door\s+type\s+([a-z]\d+)", q)
        if door_type:
            consumed.append(door_type.group(0))
            if any(not o["properties"].get("door_type") for o in selected):
                return None
            selected = [o for o in selected if o["properties"].get("door_type", "").casefold() == door_type.group(1)]
        materials = re.findall(r"\b(wd-\d|stl-\d|al-\d)\b", q)
        if materials:
            consumed.extend(materials)
            field="frame_material" if "frame" in q else "door_material"
            if any(not o["properties"].get(field) for o in selected):
                return None
            selected=[o for o in selected if o["properties"].get(field,"").casefold() in materials]
        note=re.search(r"\bnotes?\s+([a-c])\b",q)
        if note:
            consumed.append(note.group(0))
            if any("notes" not in o["properties"] for o in selected):
                return None
            selected=[o for o in selected if re.search(r"\b"+note.group(1)+r"\b",_normal(o["properties"].get("notes"))) ]
        dimension=re.search(r"(\d+\s*'\s*-\s*\d+(?:\s+\d/\d+)?\s*\")\s+(wide|high)",q)
        if dimension:
            consumed.append(dimension.group(0))
            field="width" if dimension.group(2)=="wide" else "height"
            if any(not o["properties"].get(field) for o in selected):
                return None
            compact=lambda v:re.sub(r"\s+","",v)
            selected=[o for o in selected if compact(o["properties"].get(field,""))==compact(dimension.group(1))]
        comparison = re.search(r"\b(wider|narrower|taller|shorter)\s+than\s+(\d+(?:[.,]\d+)?\s*(?:mm|cm|m|ft|feet|inches|inch|in))\b", q)
        if comparison:
            consumed.append(comparison.group(0))
            comparator, raw = comparison.groups()
            threshold = _dimension_metres(raw)
            field = "width" if comparator in {"wider", "narrower"} else "height"
            measurements = [(o, _dimension_metres(o["properties"].get(field))) for o in selected]
            if threshold is None or any(value is None for _, value in measurements):
                return None
            selected = [o for o, value in measurements if (value > threshold if comparator in {"wider", "taller"} else value < threshold)]
        room = re.search(r"\broom\s+(\d{2,4})\b", q)
        if room:
            consumed.append(room.group(0))
            selected = [o for o in selected if o["properties"]["door_number"].startswith(room.group(1)+".")]
        simple_total=bool(re.search(r"how many doors?\s*\(door numbers\)\s*are listed|how many doors? are (?:listed )?in (?:the )?door schedule\??$|total number of doors\??$",q))
        if _count_question(question) and (door_type or room or materials or note or dimension or comparison or specific or simple_total):
            if not _schedule_language_supported(question, consumed):
                return None
            result = _result(len(selected), "count", selected, "native_pdf_schedule_rows", "Selected door schedule")
            result["answer"] = f"{len(selected)} matching door schedule rows."
            return result
    if rooms and re.search(r"room|area|finish", q):
        selected = rooms
        consumed = []
        room = re.search(r"\broom\s+(\d{2,4})\b", q)
        if room:
            consumed.append(room.group(0))
            selected = [o for o in rooms if o["properties"]["room_number"] == room.group(1)]
        named = re.search(r"rooms?\s+(?:named|labelled)\s+['\"]?([a-z ]+)", q)
        if named:
            name = named.group(1).split(" in ")[0].split(" on ")[0].strip()
            selected = [o for o in rooms if name in _normal(o["label"])]
            consumed.append(name)
        floor = re.search(r"\b(?:floor finish|finish)\s+(f\d+)\b",q)
        base = re.search(r"\bbase\b.*?\b(b\d+)\b",q)
        if floor:
            consumed.append(floor.group(0))
            if any("floor_finish" not in o["properties"] for o in selected):
                return None
            selected=[o for o in selected if floor.group(1) in _normal(o["properties"].get("floor_finish")).split()]
        if base:
            consumed.append(base.group(0))
            if any("base_finish" not in o["properties"] for o in selected):
                return None
            selected=[o for o in selected if o["properties"].get("base_finish","").casefold()==base.group(1)]
        locker="locker rooms" in q
        if locker:
            consumed.append("locker")
            selected=[o for o in selected if "locker" in _normal(o["label"])]
        total=bool(re.search(r"total area of all rooms|all rooms that have an area listed",q))
        labels = [str(o.get("label", "")).split("·")[-1].strip() for o in selected]
        if not _schedule_language_supported(question, consumed, labels):
            return None
        if re.search(r"\b(gross|net|interior|exterior)\b", q):
            # A finish schedule's AREA column does not establish these roles.
            return None
        if _area_question(question) and selected and (room or named or floor or base or locker or total):
            if not all(_finite_quantity(o, "area_ft2") for o in selected):
                return None
            terms = [o["properties"]["area_ft2"] for o in selected]
            result=_result(sum(terms), "ft²", selected, "native_pdf_schedule_area", "Selected finish schedule",
                           calculation={"operation":"sum", "terms":terms})
            if _count_question(question):
                result["answer"]=f"{len(selected)} rooms; combined area {sum(terms):g} ft²."
            return result
        if _count_question(question) and not _area_question(question) and (base or floor):
            return _result(len(selected),"count",selected,"native_pdf_schedule_rows","Selected finish schedule")
    return None


def _native_ruled_schedule(question, document):
    """Counts over any ruled schedule on the sheet (door, window, type schedules), by code."""
    from .schedules import answer_count
    tables = document.get("metadata", {}).get("schedule_tables", [])
    if not tables:
        return None
    found = answer_count(question, tables)
    if found is None:
        return None
    table = found["table"]
    source = document.get("metadata", {}).get("source_path")
    objects = [{"id": r["id"], "label": " | ".join(c for c in r["cells"][:3] if c), "type": "schedule_row",
                "page": table["page"], "bbox": r["bbox"], "source_path": source,
                "properties": {"cells": dict(zip(table["header"], r["cells"])), "schedule": table["title"]}}
               for r in found["rows"]]
    calculation = {"operation": "sum" if found["terms"] is not None else "count_rows", "basis": found["basis"]}
    if found["terms"] is not None:
        calculation["terms"] = found["terms"]
    result = _result(found["value"], "count", objects, "native_pdf_ruled_schedule", f"Schedule: {table['title']}",
                     calculation=calculation)
    result["answer"] = f"{found['value']} ({found['basis']} in {table['title']})."
    return result


def answer_native(question: str, document: dict, source_path: Path, data_root: Path) -> dict | None:
    """Return a supported native answer, or None for model/vision fallback."""
    source_path, data_root = Path(source_path), Path(data_root)
    for handler in (
        lambda: _native_ifc(question, document, source_path, data_root),
        lambda: _native_cad(question, document),
        lambda: _native_schedule(question, document),
        lambda: _native_ruled_schedule(question, document),
    ):
        result = handler()
        if result is not None:
            return result
    return None


native_answer = answer_native
answer_question = answer_native

"""Map each question to a cross-language family (intent) and a grounding scope.

English templates get a family by rule; translated twins (the line right after, same path and answer)
inherit the family of their English twin. Verified: every non-English line has such a twin.
"""
import re

# (source, regex on the English template or question, family, grounding)
# grounding: whole_drawing | whole_model | level | named_label_set | named_room | named_apartment
#            | table_all | table_filter | table_row | plan_detail | building_report | level_report | named_entity_report
RULES = [
    # cubicasa5k: whole-plan symbol or room counts
    ("cubicasa5k", r"windows are shown", "count_windows", "whole_drawing"),
    ("cubicasa5k", r"floors \(storeys\)", "count_storeys", "whole_drawing"),
    ("cubicasa5k", r"toilet bowls", "count_toilets", "whole_drawing"),
    ("cubicasa5k", r"sinks and wash basins", "count_sinks", "whole_drawing"),
    ("cubicasa5k", r"showers and bathtubs", "count_showers_bathtubs", "whole_drawing"),
    ("cubicasa5k", r"How many doors are shown", "count_doors", "whole_drawing"),
    ("cubicasa5k", r"saunas", "count_rooms_sauna", "whole_drawing"),
    ("cubicasa5k", r"kitchens", "count_rooms_kitchen", "whole_drawing"),
    ("cubicasa5k", r"bedrooms", "count_rooms_bedroom", "whole_drawing"),
    ("cubicasa5k", r"bathrooms or washrooms", "count_rooms_bathroom", "whole_drawing"),
    ("cubicasa5k", r"separate WC rooms", "count_rooms_wc", "whole_drawing"),
    ("cubicasa5k", r"balconies", "count_rooms_balcony", "whole_drawing"),
    # swiss_dwellings
    ("swiss_dwellings", r"How many rooms labelled", "count_rooms_by_label", "named_label_set"),
    ("swiss_dwellings", r"net floor area of room <ROOM_ID>", "area_room_by_id", "named_room"),
    ("swiss_dwellings", r"net floor area of apartment <APT>", "area_apartment", "named_apartment"),
    ("swiss_dwellings", r"all numbered indoor rooms", "area_floor_total", "whole_drawing"),
    ("swiss_dwellings", r"total net area in m² of all rooms labelled", "area_rooms_by_label", "named_label_set"),
    ("swiss_dwellings", r"How many windows", "count_windows", "whole_drawing"),
    ("swiss_dwellings", r"How many washbasins", "count_washbasins", "whole_drawing"),
    ("swiss_dwellings", r"How many toilets", "count_toilets", "whole_drawing"),
    ("swiss_dwellings", r"How many apartments", "count_apartments", "whole_drawing"),
    ("swiss_dwellings", r"How many doors", "count_doors", "whole_drawing"),
    ("swiss_dwellings", r"How many bathtubs", "count_bathtubs", "whole_drawing"),
    ("swiss_dwellings", r"How many showers", "count_showers", "whole_drawing"),
    # ifc_models
    ("ifc_models", r"net floor area of the room <Q> on <Q>", "area_room_by_name", "named_room"),
    ("ifc_models", r"total net floor area of all rooms", "area_level_spaces_total", "level"),
    ("ifc_models", r"total net side area of all walls", "area_level_wall_side", "level"),
    ("ifc_models", r"total net volume of all slabs", "volume_level_slabs", "level"),
    ("ifc_models", r"total net volume of all walls", "volume_level_walls", "level"),
    ("ifc_models", r"total length of all walls", "length_level_walls", "level"),
    ("ifc_models", r"How many (\w+(?: \(spaces\))?(?: fixtures)?) are shown on the floor plan", "count_level_{0}", "level"),
    ("ifc_models", r"How many (\w+(?: \(spaces\))?(?: fixtures)?) are there in the model", "count_model_{0}", "whole_model"),
    # opening_design (sheet-specific schedule and plan questions)
    ("opening_design", r"enlarged plan", "plan_fixture_count", "plan_detail"),
    ("opening_design", r"if every N-wide", "table_derived_calc", "table_all"),
    ("opening_design", r"has the largest area", "table_argmax", "table_all"),
    ("opening_design", r"how many rooms have floor finish .* and what is their total area", "table_filter_count_and_area", "table_filter"),
    ("opening_design", r"total area of all rooms that have an area", "table_area_sum_all", "table_all"),
    ("opening_design", r"(total|combined) area of", "table_area_sum_filter", "table_filter"),
    ("opening_design", r"what is the area of room", "table_area_lookup", "table_row"),
    ("opening_design", r"how many (doors \(door numbers\) are listed|rooms are listed|windows \(window assemblies\) are listed|items in total)", "table_count_all", "table_all"),
    ("opening_design", r"Marvin Essential sliding patio doors are scheduled in total", "table_count_filter", "table_filter"),
    ("opening_design", r"how many", "table_count_filter", "table_filter"),
    ("opening_design", r"(what|which)", "table_lookup", "table_row"),
]

# ifc_bench intents. Order matters: first match wins.
BENCH = [
    ("fire_safety", r"fire|emergency|escape"),
    ("software_standards", r"software|ifc standards|modeling standards"),
    ("project_info", r"type of building|building's type|project information|building details|building name"),
    ("building_scale_summary", r"number of levels.*(footprint|floor area|spaces)|floor area, number of levels"),
    ("space_breakdown_all_levels", r"space (distribution|breakdown) by level|complete space breakdown"),
    ("space_list_one_level", r"space breakdown of the|spaces (are )?on (level|ground|the ground|Level)|spaces in the underground|What spaces are on Level|restroom spaces|names of all the rooms|each room available|rooms are there in house|office spaces|office rooms"),
    ("space_utilization_by_function", r"space utili[sz]|utilized by function"),
    ("level_heights_elevations", r"heights of each level|elevations|floor-to-floor"),
    ("largest_room", r"largest room|room in the building is the largest"),
    ("ceiling_heights", r"ceiling heights?|tallest ceilings|height of the ceiling|heights of the ceilings"),
    ("door_widths", r"door width|widths? of the door|doors have the greatest widths|door has the largest width|types of door \(by width\)"),
    ("window_widths", r"window width|widest window|height of each window"),
    ("door_types_counts", r"door types|doors are installed|types of doors|interior doors are there|doorknobs"),
    ("window_types_counts", r"window types|types of windows|windows are there|glazed windows|glazing"),
    ("envelope_performance", r"insulation|thermal|air tightness|solar heat|vapor"),
    ("lifecycle_cost_sustainability", r"lifespan|warranty|carbon|recyclab"),
    ("slabs", r"slab"),
    ("wall_materials", r"materials? (are |is )?(used|applied|found).*walls|walls.*materials|materials are used for the walls|materials are used in each wall type|external wall construction"),
    ("wall_thickness", r"thickness"),
    ("load_bearing", r"load-bearing|structural ones"),
    ("wall_length", r"length of (inside|outside|exterior|interior)? ?walls|combined length of (the )?(exterior|inside)"),
    ("wall_types_counts", r"wall types|walls are used|types of interior wall|types of walls|curtain walls"),
    ("floor_areas", r"floor area|footprint|gross area of each floor|gross area"),
    ("coverings_finishes", r"coverings|ceiling materials|materials are applied in the ceilings|materials are used in the ceilings|flooring|tiles|tiling|skirting|painting"),
    ("furniture_sanitary_rooms", r"furniture|sanitary|toilets|bathroom|bedrooms"),
    ("stairs_circulation", r"stair|vertical circulation|steps"),
    ("railings", r"railing"),
    ("structure", r"structural|beam|column|foundation|roof|concrete volume"),
    ("mep", r"MEP|pipe|piping|heating|cooling|electrical|voltage|lighting|energy|ducts"),
    ("parking", r"parking"),
    ("facade_area", r"fa[cç]ade"),
    ("other_practitioner", r"."),
]
BENCH_RX = [(f, re.compile(r, re.I)) for f, r in BENCH]


def ifc_bench_family(q):
    for f, rx in BENCH_RX:
        if rx.search(q):
            return f
    return "other_practitioner"


NAMED_LEVEL = re.compile(r"\b(Level [A-Z]\d|level \d|ground (floor|level)|first (floor|level)|second (floor|level)|third floor|basement|attic|underground level)", re.I)
NAMED_ENTITY = re.compile(r"room [A-Z]?\d|house A|Duplex B|living room|staff room|Open-plan office|door \w{20,}")
ALL_LEVELS = re.compile(r"by level|each level|each floor|per floor|by floor|across the floors|all building levels", re.I)


def bench_grounding(q):
    if NAMED_ENTITY.search(q):
        return "named_entity_report"
    if NAMED_LEVEL.search(q) and not ALL_LEVELS.search(q):
        return "level_report"
    return "building_report"


_compiled = [(s, re.compile(r, re.I), f, g) for s, r, f, g in RULES]


def english_family(source, template, question):
    if source == "ifc_bench":
        return ifc_bench_family(question), bench_grounding(question)
    for s, rx, f, g in _compiled:
        if s != source:
            continue
        m = rx.search(template)
        if m:
            if "{0}" in f:
                f = f.format(m.group(1).split(" ")[0].lower())
            return f, g
    return "UNMATCHED", "UNMATCHED"


def assign(df):
    """Add family and grounding columns; non-English rows inherit from the preceding English twin."""
    fam, grd = [], []
    for i, r in enumerate(df.itertuples()):
        if r.lang == "en":
            f, g = english_family(r.source, r.template, r.question)
        else:
            f, g = fam[i - 1], grd[i - 1]
        fam.append(f)
        grd.append(g)
    df["family"] = fam
    df["grounding"] = grd
    return df

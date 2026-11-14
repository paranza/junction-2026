"""Profile the 5 ifc_bench IFC models: header, schema, load time, units, entity counts,
psets/qsets, materials, types, storeys, name languages. Writes profile.json + CSVs to the work dir.
Usage: python -I profile_ifc.py <dataset_dir> <work_dir>"""
import sys, os, time, json, re, collections
import ifcopenshell
import ifcopenshell.util.element as E
import ifcopenshell.util.unit as U

DS, W = sys.argv[1], sys.argv[2]
FILES = ["ac20_arc.ifc", "digital_hub_arc.ifc", "duplex_arc.ifc", "fantasy_office_building_3_arc.ifc", "hitos_arc.ifc"]

# crude language lexicons (lowercase substrings / tokens) for names
LEX = {
    "de": ["wand", "tür", "tuer", "decke", "fenster", "treppe", "stütze", "stuetze", "träger", "flur", "büro", "buero",
           "raum", "geschoss", "keller", "dach", "geländer", "gelaender", "beton", "kalksandstein", "stahlbeton",
           "basiswand", "boden", "schreibtisch", "stuhl", "lager", "zarge", "drehflügel", "ortbeton", "dämmung",
           "obergeschoss", "erdgeschoss", "aufzug", "schacht", "fassade", "objekt", "labor", "waschtisch"],
    "no": ["vegg", "dør", "dor ", "dekke", "vindu", "trapp", "etg", "kjeller", "rekkverk", "betong", "korridor",
           "kontor", "bærende", "gips", "bindingsverk", "kledning", "trappehus", "heis", "garderobe", "kjøkken",
           "lager", "bruttoareal", "glassgata", "sløyfer", "isolasjon", "himling", "sjakt", "rom"],
    "en": ["wall", "door", "window", "floor", "roof", "slab", "stair", "column", "beam", "room", "bedroom",
           "bathroom", "kitchen", "living", "office", "corridor", "toilet", "meeting", "railing", "furniture",
           "basic", "default", "level", "insulation", "brick", "concrete", "hallway", "foyer", "utility", "staircase"],
}

def lang_tags(names):
    c = collections.Counter()
    for n in names:
        s = (n or "").lower()
        hit = set()
        for lg, words in LEX.items():
            if any(w in s for w in words):
                hit.add(lg)
        for lg in hit:
            c[lg] += 1
        if not hit:
            c["unknown"] += 1
    return dict(c)

out = {}
rows_types, rows_psets, rows_mats, rows_storeys, rows_classes = [], [], [], [], []
for fn in FILES:
    p = os.path.join(DS, "data", "ifc_bench", fn)
    t0 = time.perf_counter()
    f = ifcopenshell.open(p)
    load_s = time.perf_counter() - t0
    hdr = f.header
    fname = hdr.file_name
    fdesc = hdr.file_description
    info = {
        "file": fn, "bytes": os.path.getsize(p), "schema": f.schema, "load_seconds": round(load_s, 2),
        "n_entities_total": len(list(f)),
        "file_description": list(fdesc.description),
        "originating_system": fname.originating_system, "preprocessor_version": fname.preprocessor_version,
        "time_stamp": fname.time_stamp, "authorization": fname.authorization,
    }
    # application (IfcApplication)
    info["applications"] = [(a.ApplicationFullName, a.Version, a.ApplicationIdentifier) for a in f.by_type("IfcApplication")]
    # units
    try:
        info["length_unit_scale_to_m"] = U.calculate_unit_scale(f)
    except Exception as e:
        info["length_unit_scale_to_m"] = str(e)
    units = []
    for ua in f.by_type("IfcUnitAssignment"):
        for un in ua.Units:
            if un.is_a("IfcSIUnit"):
                units.append(f"{un.UnitType}:{un.Prefix or ''}{un.Name}")
            elif un.is_a("IfcConversionBasedUnit"):
                units.append(f"{un.UnitType}:{un.Name}(conv)")
            elif un.is_a("IfcDerivedUnit"):
                units.append(f"{un.UnitType}(derived)")
    info["units"] = units
    # project / site / building
    proj = f.by_type("IfcProject")[0]
    info["project"] = {"Name": proj.Name, "LongName": proj.LongName, "Phase": proj.Phase, "Description": proj.Description}
    sites = f.by_type("IfcSite")
    info["sites"] = [{"Name": s.Name, "LongName": s.LongName, "RefLatitude": s.RefLatitude, "RefLongitude": s.RefLongitude,
                      "RefElevation": s.RefElevation} for s in sites]
    info["buildings"] = [{"Name": b.Name, "LongName": b.LongName, "Description": b.Description,
                          "ObjectType": b.ObjectType, "psets": {k: v for k, v in E.get_psets(b).items()}} for b in f.by_type("IfcBuilding")]
    # storeys
    st = []
    for s in sorted(f.by_type("IfcBuildingStorey"), key=lambda s: (s.Elevation or 0)):
        cont = [e for r in (s.ContainsElements or []) for e in r.RelatedElements]
        spaces = [e for e in E.get_decomposition(s) if e.is_a("IfcSpace")]
        st.append({"Name": s.Name, "LongName": s.LongName, "Elevation": s.Elevation, "n_contained": len(cont),
                   "n_spaces": len(spaces), "psets": list(E.get_psets(s).keys())})
        rows_storeys.append([fn, s.Name, s.LongName, s.Elevation, len(cont), len(spaces)])
    info["storeys"] = st
    # entity class counts (IfcProduct subclasses + key others)
    cls = collections.Counter(e.is_a() for e in f.by_type("IfcProduct"))
    info["product_class_counts"] = dict(cls.most_common())
    for k, v in cls.items():
        rows_classes.append([fn, k, v])
    tcls = collections.Counter(e.is_a() for e in f.by_type("IfcTypeObject"))
    info["type_class_counts"] = dict(tcls.most_common())
    info["n_IfcRelDefinesByType"] = len(f.by_type("IfcRelDefinesByType"))
    info["n_IfcRelAssociatesMaterial"] = len(f.by_type("IfcRelAssociatesMaterial"))
    info["n_IfcSystem"] = len(f.by_type("IfcSystem"))
    info["n_IfcZone"] = len(f.by_type("IfcZone"))
    info["n_IfcGroup"] = len(f.by_type("IfcGroup"))
    info["n_IfcClassificationReference"] = len(f.by_type("IfcClassificationReference"))
    info["n_IfcOpeningElement"] = len(f.by_type("IfcOpeningElement"))
    # psets / qsets
    ps = collections.Counter()
    psprops = collections.defaultdict(collections.Counter)
    for r in f.by_type("IfcRelDefinesByProperties"):
        d = r.RelatingPropertyDefinition
        if d.is_a("IfcPropertySet"):
            ps[("pset", d.Name)] += len(r.RelatedObjects)
            for pr in d.HasProperties or []:
                psprops[("pset", d.Name)][pr.Name] += 1
        elif d.is_a("IfcElementQuantity"):
            ps[("qset", d.Name)] += len(r.RelatedObjects)
            for q in d.Quantities or []:
                psprops[("qset", d.Name)][q.Name] += 1
    # psets on type objects too
    for t in f.by_type("IfcTypeObject"):
        for d in t.HasPropertySets or []:
            kind = "qset" if d.is_a("IfcElementQuantity") else "pset"
            ps[(kind + "_on_type", d.Name)] += 1
    info["n_pset_names"] = len([k for k in ps if k[0] == "pset"])
    info["n_qset_names"] = len([k for k in ps if k[0] == "qset"])
    info["top_psets"] = [(k[0], k[1], v) for k, v in ps.most_common(60)]
    for k, v in ps.items():
        rows_psets.append([fn, k[0], k[1], v, ";".join(f"{n}" for n, _ in psprops[k].most_common(25))])
    # materials
    mats = f.by_type("IfcMaterial")
    info["n_IfcMaterial"] = len(mats)
    info["materials"] = sorted({m.Name for m in mats if m.Name})[:200]
    info["n_IfcMaterialLayerSet"] = len(f.by_type("IfcMaterialLayerSet"))
    info["n_IfcMaterialLayerSetUsage"] = len(f.by_type("IfcMaterialLayerSetUsage"))
    info["n_IfcMaterialList"] = len(f.by_type("IfcMaterialList"))
    info["n_IfcMaterialConstituentSet"] = len(f.by_type("IfcMaterialConstituentSet")) if f.schema != "IFC2X3" else 0
    info["n_IfcMaterialProfileSet"] = len(f.by_type("IfcMaterialProfileSet")) if f.schema != "IFC2X3" else 0
    # material usage per element class
    mat_by_class = collections.defaultdict(collections.Counter)
    for e in f.by_type("IfcElement"):
        m = E.get_material(e, should_skip_usage=True)
        kind = m.is_a() if m else "none"
        mat_by_class[e.is_a()][kind] += 1
    info["material_kind_by_class"] = {k: dict(v) for k, v in mat_by_class.items()}
    for m in mats:
        rows_mats.append([fn, m.Name, getattr(m, "Category", None)])
    # types: name and instance count
    for t in f.by_type("IfcTypeObject"):
        n_inst = len(E.get_types(t))
        rows_types.append([fn, t.is_a(), t.Name, n_inst])
    # elements without type
    no_type = collections.Counter(e.is_a() for e in f.by_type("IfcElement") if E.get_type(e) is None)
    info["elements_without_type_by_class"] = dict(no_type.most_common())
    # names and languages
    names_space = [(s.Name or "") + " " + (s.LongName or "") for s in f.by_type("IfcSpace")]
    names_type = [t.Name or "" for t in f.by_type("IfcTypeObject")]
    names_elem = [e.Name or "" for e in f.by_type("IfcElement")]
    names_mat = [m.Name or "" for m in mats]
    info["lang_space_names"] = lang_tags(names_space)
    info["lang_type_names"] = lang_tags(names_type)
    info["lang_material_names"] = lang_tags(names_mat)
    info["lang_element_names"] = lang_tags(names_elem)
    nonascii = collections.Counter(ch for n in names_space + names_type + names_elem + names_mat for ch in n if ord(ch) > 127)
    info["non_ascii_chars"] = dict(nonascii.most_common(20))
    info["sample_space_names"] = names_space[:15]
    info["sample_type_names"] = sorted(set(names_type))[:25]
    info["n_spaces"] = len(f.by_type("IfcSpace"))
    # IsExternal availability on walls
    ext = collections.Counter()
    for w in f.by_type("IfcWall"):
        ps_ = E.get_psets(w)
        v = ps_.get("Pset_WallCommon", {}).get("IsExternal", "missing")
        ext[str(v)] += 1
    info["wall_IsExternal"] = dict(ext)
    lb = collections.Counter()
    for w in f.by_type("IfcWall"):
        v = E.get_psets(w).get("Pset_WallCommon", {}).get("LoadBearing", "missing")
        lb[str(v)] += 1
    info["wall_LoadBearing"] = dict(lb)
    out[fn] = info
    print(f"{fn}: schema={f.schema} load={load_s:.2f}s entities={info['n_entities_total']} products={sum(cls.values())}", flush=True)

json.dump(out, open(os.path.join(W, "profile.json"), "w"), indent=1, default=str, ensure_ascii=False)
import csv
for name, rows, hdr in [("types.csv", rows_types, ["file", "type_class", "type_name", "n_instances"]),
                        ("psets.csv", rows_psets, ["file", "kind", "name", "n_objects", "top_props"]),
                        ("materials.csv", rows_mats, ["file", "material", "category"]),
                        ("storeys.csv", rows_storeys, ["file", "name", "long_name", "elevation", "n_contained", "n_spaces"]),
                        ("product_classes.csv", rows_classes, ["file", "class", "count"])]:
    with open(os.path.join(W, name), "w", newline="") as fh:
        wr = csv.writer(fh); wr.writerow(hdr); wr.writerows(rows)
print("done")

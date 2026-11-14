"""Quick checks of duplex prose answers (house A/B, foundations, counts). Usage: python -I duplex_checks.py <dataset_dir> <work_dir>"""
import sys, os, re, json, csv
import ifcopenshell, ifcopenshell.util.element as E
DS, W = sys.argv[1], sys.argv[2]
ROWS = [json.loads(l) for l in open(os.path.join(W, "ifc_bench_questions.jsonl"))]
f = ifcopenshell.open(os.path.join(DS, "data", "ifc_bench", "duplex_arc.ifc"))
P = E.get_psets
sp = f.by_type("IfcSpace")
ft = f.by_type("IfcFooting")
doors = f.by_type("IfcDoor")
checks = [
    (144, "foundation concrete 'estimate' 16.528 = exact sum of 7 footing volumes", round(sum(P(x)["PSet_Revit_Dimensions"]["Volume"] for x in ft), 3) == 16.528),
    (122, "foundation 'depth' 300 mm = footing type '900 x 300' thickness (bottom elevation -1.55 m is another reading)", all("900 x 300" in x.Name for x in ft)),
    (123, "ground floor slab 127 mm / 64.78 m2 (one of TWO 127 mm slabs: 64.78 and 64.91)", any(abs(P(s)["PSet_Revit_Dimensions"]["Area"] - 64.78) < 0.005 for s in f.by_type("IfcSlab"))),
    (116, "door 1hOSvn6df7F8_7GcBWlRGQ width 1.25 m", f.by_guid("1hOSvn6df7F8_7GcBWlRGQ").OverallWidth == 1.25),
    (148, "10 interior doors (Pset_DoorCommon.IsExternal False)", sum(not P(d)["Pset_DoorCommon"]["IsExternal"] for d in doors) == 10),
    (160, "14 doors (doorknobs = 2 x 14 is an assumption)", len(doors) == 14),
    (125, "external wall thickness 417 mm (Exterior - Brick on Block layer sum)", any(abs(sum(l.LayerThickness for l in E.get_material(w).ForLayerSet.MaterialLayers) - 0.417) < 1e-6 for w in f.by_type("IfcWall") if "Exterior - Brick" in w.ObjectType)),
    (155, "4 bedrooms (LongName contains 'Bedroom')", sum("Bedroom" in (s.LongName or "") for s in sp) == 4),
    (159, "4 bathrooms", sum("Bathroom" in (s.LongName or "") for s in sp) == 4),
    (114, "21 room names (A101..B205 + R301)", len(sp) == 21 and all(s.Name in ROWS[114]["answer"] for s in sp)),
    (158, "ceiling GUID in living room A = 3bXiCStxP6Fgxdej$yc50n (IfcCovering CEILING)", f.by_guid("3bXiCStxP6Fgxdej$yc50n").is_a("IfcCovering")),
    (152, "reference lists 9 house-A rooms although 10 A-spaces exist (A105 'Stair' omitted) -> inconsistent with Q153", "A105" not in ROWS[152]["answer"] and sum(1 for s in sp if s.Name.startswith("A")) == 10),
]
with open(os.path.join(W, "duplex_checks.csv"), "w", newline="") as fh:
    wr = csv.writer(fh); wr.writerow(["idx", "check", "ok"]); wr.writerows(checks)
for c in checks:
    print(c)
print(f"{sum(c[2] for c in checks)}/{len(checks)} confirmed")

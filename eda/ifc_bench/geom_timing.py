"""Time tessellation of key element classes per model (for highlight views). Usage: python -I geom_timing.py <dataset_dir>"""
import sys, os, time, multiprocessing
import ifcopenshell, ifcopenshell.geom
DS = sys.argv[1]
CLASSES = ["IfcWall", "IfcSlab", "IfcDoor", "IfcWindow", "IfcColumn", "IfcBeam", "IfcSpace", "IfcStair", "IfcRailing", "IfcCovering", "IfcFurnishingElement"]
for fn in ["duplex_arc", "ac20_arc", "digital_hub_arc", "fantasy_office_building_3_arc", "hitos_arc"]:
    f = ifcopenshell.open(os.path.join(DS, "data", "ifc_bench", fn + ".ifc"))
    els = [e for c in CLASSES for e in f.by_type(c)]
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    t0 = time.perf_counter()
    it = ifcopenshell.geom.iterator(s, f, multiprocessing.cpu_count(), include=els)
    n = ok = 0
    if it.initialize():
        while True:
            ok += 1
            if not it.next():
                break
    print(f"{fn}: {len(els)} elements, {ok} shapes tessellated in {time.perf_counter() - t0:.1f}s")

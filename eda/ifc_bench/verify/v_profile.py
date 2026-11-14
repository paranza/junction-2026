import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Independent profile of the 5 ifc_bench models (skeptic pass).
import time, json, sys, collections
import ifcopenshell, ifcopenshell.util.unit as uu
D = _DATA + '/data/ifc_bench/'
MODELS = ['ac20_arc', 'digital_hub_arc', 'duplex_arc', 'fantasy_office_building_3_arc', 'hitos_arc']
out = {}
for m in MODELS:
    t = time.perf_counter()
    f = ifcopenshell.open(D + m + '.ifc')
    lt = time.perf_counter() - t
    hdr = f.header
    fn = hdr.file_name
    apps = [(a.ApplicationFullName, a.Version) for a in f.by_type('IfcApplication')]
    scale = uu.calculate_unit_scale(f)
    units = []
    for ua in f.by_type('IfcUnitAssignment'):
        for u in ua.Units:
            if u.is_a('IfcSIUnit'):
                units.append((u.UnitType, u.Prefix, u.Name))
            elif u.is_a('IfcConversionBasedUnit'):
                units.append((u.UnitType, 'conv', u.Name))
    cls = collections.Counter(e.is_a() for e in f.by_type('IfcProduct'))
    storeys = [(s.Name, s.Elevation) for s in f.by_type('IfcBuildingStorey')]
    nent = len(list(f))
    dist = len(f.by_type('IfcDistributionElement'))
    qsets = collections.Counter(q.Name for q in f.by_type('IfcElementQuantity'))
    out[m] = dict(schema=f.schema, load_s=round(lt, 2), entities=nent, originating=fn.originating_system,
                  preproc=fn.preprocessor_version, time=fn.time_stamp, apps=apps, len_scale=scale,
                  units=units, storeys=storeys, n_distribution=dist, top_classes=cls.most_common(40),
                  qsets=qsets.most_common(30))
    print(m, f.schema, 'load', round(lt, 2), 's entities', nent, 'scale', scale, 'dist', dist)
    print('  orig:', fn.originating_system, '| pre:', fn.preprocessor_version, '|', fn.time_stamp)
    print('  apps:', apps)
    print('  units:', [u for u in units if u[0] in ('LENGTHUNIT', 'AREAUNIT', 'VOLUMEUNIT')])
    print('  storeys:', storeys)
    print('  qsets:', qsets.most_common(12))
    print('  classes:', cls.most_common(25))
json.dump(out, open('v_profile.json', 'w'), indent=1, default=str)

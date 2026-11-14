# F10: area totals, footprint, largest room.
import sys
sys.path.insert(0, '.')
from vlib import *

def spaces(m, key):
    f = load(m)
    return [(s, flat_props(s, False).get(key)) for s in f.by_type('IfcSpace')]

# ac20
f = load('ac20')
g = sum(v for s, v in spaces('ac20', ('BaseQuantities', 'GrossFloorArea')))
n = sum(v for s, v in spaces('ac20', ('BaseQuantities', 'NetFloorArea')))
print('ac20 sum space Gross', round(g, 3), 'sum space Net', round(n, 3))
for b in f.by_type('IfcBuilding'):
    print('ac20 building props', {k: v for k, v in flat_props(b, False).items() if 'rea' in k[1]})
for st in f.by_type('IfcBuildingStorey'):
    print('ac20 storey', st.Name, {k: v for k, v in flat_props(st, False).items() if 'rea' in k[1] or 'Height' in k[1]})
for sl in f.by_type('IfcSlab'):
    p = flat_props(sl, False)
    if sname(sl) == 'Erdgeschoss' or sl.PredefinedType == 'FLOOR':
        print('ac20 slab', sl.Name, sl.PredefinedType, sname(sl), {k[1]: round(v, 2) for k, v in p.items() if isinstance(v, float) and ('Area' in k[1] or 'Volume' in k[1])})
# hitos
hs = spaces('hitos', (None, 'NetFootprintArea'))
tot = sum(v for s, v in hs)
brut = [(s.Name, s.LongName, sname(s), round(v, 2)) for s, v in hs if 'rutto' in (s.LongName or '')]
print('hitos total', round(tot, 3), 'brutto', brut, 'brutto sum', round(sum(x[3] for x in brut), 2),
      'rooms only', round(tot - sum(v for s, v in hs if 'rutto' in (s.LongName or '')), 3))
big = sorted(hs, key=lambda x: -x[1])[:6]
print('hitos largest', [(s.Name, s.LongName, sname(s), round(v, 1)) for s, v in big])
nb = sorted([x for x in hs if 'rutto' not in (x[0].LongName or '')], key=lambda x: -x[1])[:3]
print('hitos largest non-brutto', [(s.Name, s.LongName, sname(s), round(v, 1)) for s, v in nb])
print('hitos n spaces', len(hs), 'avg', round(tot / len(hs), 1))
# fantasy footprint candidates
f = load('fantasy')
print('fantasy sum rooms', round(sum(v for s, v in spaces('fantasy', ('PSet_Room', 'Area'))), 3))
for sl in f.by_type('IfcSlab'):
    p = flat_props(sl, True)
    print('fantasy slab', sl.Name, sl.PredefinedType, sname(sl), {k: v for k, v in p.items() if isinstance(v, (int, float)) and ('rea' in k[1] or 'Dicke' in k[1] or 'hick' in k[1] or 'olum' in k[1])})
for x in f.by_type('IfcSite') + f.by_type('IfcBuilding'):
    print('fantasy', x.is_a(), {k: v for k, v in flat_props(x, False).items() if isinstance(v, (int, float))})

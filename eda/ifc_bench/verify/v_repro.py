# Seed-2026 stratified sample (v_sample.json): recompute each key fact from the IFC and compare with the reference.
import sys, json, re, math, collections, statistics, csv
sys.path.insert(0, '.')
from vlib import *
from v_geom import volume, footprint
import ifcopenshell.util.placement as up
from shapely.ops import unary_union

QS = Q()
mats = lambda e: [m.Name for m in ue.get_materials(e)]
def cont(space):
    return [e for r in space.ContainsElements for e in r.RelatedElements]
def ph(v, k):  # Revit placeholder = value equal to property name
    return v in (None, '') or re.sub(r'\W', '', str(v)).lower() == re.sub(r'\W', '', k).lower()

R = {}
def rec(q, status, facts, note=''):
    R[q] = (status, facts, note)

a, d, du, f, h = (load(m) for m in ['ac20', 'dh', 'duplex', 'fantasy', 'hitos'])
# element_dimensions
w = sorted(a.by_type('IfcDoor'), key=lambda x: x.OverallWidth)[0]
rec(13, 'reproduced' if (w.OverallWidth == 1.0 and tname(w) == 'IFC Tür - Eine Öffnunsgrichtung') else 'not reproduced', f'min OverallWidth {w.OverallWidth} {tname(w)}')
pk = [p for p in d.by_type('IfcBuildingElementProxy') if (p.Name or '').startswith('Parkplatz')]
U = unary_union([footprint(p) for p in pk]); bb = (U.bounds[2]-U.bounds[0])*(U.bounds[3]-U.bounds[1])
rec(56, 'reproduced' if (len(pk) == 26 and round(bb, 2) == 637.33) else 'partial', f'{len(pk)} stalls; bbox of stall footprints {bb:.2f} m2', 'needs geometry: area = 2D bounding box of the 26 stalls')
ew = [x for x in du.by_type('IfcWall') if 'Exterior - Brick' in (x.Name or '')][0]
t = flat_props(ew).get(('PSet_Revit_Type_Construction', 'Width'))
rec(125, 'reproduced' if round(t*1000) == 417 else 'not reproduced', f'Revit Width {t*1000:.0f} mm')
# element_lookup
sp = [s for s in h.by_type('IfcSpace') if s.Name == '01.014'][0]
c = collections.Counter(tname(e) for e in cont(sp))
rec(244, 'reproduced' if c == {'SHOWER': 1, 'TOILET': 1, 'BASIN': 1} else 'not reproduced', str(dict(c)), 'via IfcRelContainedInSpatialStructure to IfcSpace')
dr = du.by_guid('1hOSvn6df7F8_7GcBWlRGQ')
rec(116, 'reproduced' if dr.OverallWidth == 1.25 else 'not reproduced', f'OverallWidth {dr.OverallWidth}')
sp = [s for s in f.by_type('IfcSpace') if (s.LongName or '').startswith('Open-plan') and sname(s) == 'EG'][0]
c = collections.Counter(e.ObjectType for e in cont(sp))
rec(177, 'reproduced' if c == {'Schreibtisch-Kombination-01:Typ1': 8} else 'not reproduced', str(dict(c)), 'via containment')
# fire
def fire(m, cls):
    n = 0
    for e in m.by_type(cls):
        for (ps, k), v in flat_props(e).items():
            if re.search('fire|feuer|brand', k, re.I) and not ph(v, k): n += 1
    return n
rec(196, 'reproduced' if fire(f, 'IfcWindow') == 0 else 'contradicted', f'fantasy windows with a fire value: {fire(f, "IfcWindow")}')
rec(235, 'reproduced' if fire(h, 'IfcWindow') == 0 else 'contradicted', f'hitos windows with a fire value: {fire(h, "IfcWindow")}')
rec(195, 'reference contradicted by model' if fire(f, 'IfcDoor') else 'reproduced', f'fantasy doors with FireRating value: {fire(f, "IfcDoor")} (EI 30)')
# inventory
ctx = [c.TrueNorth.DirectionRatios for c in du.by_type('IfcGeometricRepresentationContext') if c.TrueNorth]
site = du.by_type('IfcSite')[0]
north = 0
for wd in du.by_type('IfcWindow'):
    M = up.get_local_placement(wd.ObjectPlacement)
    if abs(M[0, 0]) > 0.9 and M[1, 3] > -1.0 and sname(wd) != 'Roof': north += 1
rec(115, 'reference contestable', f'TrueNorth {ctx}; RefLatitude {site.RefLatitude}; windows on +Y facade: {north}', 'reference says not georeferenced')
sl = f.by_type('IfcSlab')
cats = collections.Counter(s.PredefinedType for s in sl); tc = collections.Counter(tname(s) for s in sl)
ok193 = cats == {'FLOOR': 4, 'ROOF': 4, 'LANDING': 8, 'BASESLAB': 1} and tc['Massivtreppenpodest:100 mm Stärke'] == 4 and tc['Geschossdecke:STB 25.0'] == 2
rec(193, 'reproduced' if ok193 else 'partial', f'{dict(cats)}; {dict(tc)}', 'thickness read from type names (no layer thickness stored)')
cw = collections.Counter(tname(x) for x in f.by_type('IfcCurtainWall'))
rec(190, 'reproduced' if cw == {'Fassade:Raster 1.25 x 3.70m - mit Pfosten 2': 5} else 'not reproduced', str(dict(cw)))
# lengths_volumes
V = [flat_props(s, False).get((None, 'NetVolume')) for s in h.by_type('IfcSlab') if s.PredefinedType == 'FLOOR']
rec(229, 'reproduced' if (len(V) == 285 and round(sum(V), 2) == 2191.96 and round(min(V), 2) == 0.05 and round(max(V), 2) == 197.46) else 'not reproduced', f'n {len(V)} sum {sum(V):.2f} range {min(V):.2f}-{max(V):.2f}')
gv = sum(volume(s) for s in sl if s.PredefinedType in ('FLOOR', 'BASESLAB'))
rec(194, 'reproduced' if abs(gv / 690.7 - 1) <= 0.02 else 'not reproduced', f'mesh volume FLOOR+BASESLAB {gv:.2f} m3', 'reference: not available as property, manual measurement 690.7')
lay = {}
for pla in h.by_type('IfcPresentationLayerAssignment'):
    for it in pla.AssignedItems: lay[it.id()] = pla.Name
def layer(e):
    for r in (e.Representation.Representations if e.Representation else []):
        if r.id() in lay: return lay[r.id()]
        for it in r.Items:
            if it.id() in lay: return lay[it.id()]
    return ''
L = 0.0
for wl in h.by_type('IfcWall'):
    if 'Yttervegger' in layer(wl):
        for r in wl.Representation.Representations:
            if r.RepresentationIdentifier == 'Axis':
                for it in r.Items:
                    if it.is_a('IfcPolyline'):
                        P = [p.Coordinates for p in it.Points]; L += sum(math.dist(P[i][:2], P[i+1][:2]) for i in range(len(P)-1))
haslen = any('Length' in k[1] for wl in h.by_type('IfcWall')[:50] for k in flat_props(wl, False))
rec(220, 'reproduced (negative; but derivable)', f'stored Length quantity present: {haslen}; Axis polyline sum for Yttervegger walls {L/1000:.1f} m')
# levels_heights
H = sorted([(flat_props(s, False)[('Qto_SpaceBaseQuantities', 'Height')], s.LongName) for s in d.by_type('IfcSpace')], key=lambda x: -x[0])[:10]
rec(80, 'reproduced' if [round(x[0], 2) for x in H] == [10.77, 10.77, 7.77, 7.77, 7.77, 7.77, 4.4, 3.9, 3.9, 3.75] else 'not reproduced', str([(round(x[0], 2), x[1]) for x in H]))
ok9 = [s.Elevation for s in a.by_type('IfcBuildingStorey')] == [-3.0, 0.0, 3.0, 6.0, 9.0] and all(flat_props(s, False)[('BaseQuantities', 'Height')] == 3.0 for s in a.by_type('IfcBuildingStorey'))
rec(9, 'reproduced' if ok9 else 'not reproduced', 'elevations -3,0,3,6,9; storey BaseQuantities.Height 3.0')
def rh(s):
    out = {}
    def w_(dd):
        for k, v in dd.items():
            if isinstance(v, dict): w_(v.get('properties', v))
            elif k == 'ROOM HEIGHT': out['v'] = v
    w_(ue.get_psets(s)); return out.get('v')
top = sorted([(rh(s), s.Name) for s in h.by_type('IfcSpace')], key=lambda x: -x[0])[:6]
rec(231, 'reproduced' if [x[1] for x in top[:4]] == ['99.01.015', '99.01.002', '80.029', '06.04.001'] and top[4][0] == 4.0 else 'not reproduced', str(top), 'ArchiCAD ROOM HEIGHT (metres); 5th place is a tie at 4.00')
# materials
ext = [x for x in a.by_type('IfcWall') if flat_props(x).get(('ArchiCADProperties', 'Ebene')) == 'Außenwände']
mm = collections.Counter(re.sub(r'\s*\d+$', '', mats(x)[0]) for x in ext)
rec(21, 'reproduced' if mm == {'Kalksandstein': 54} else 'not reproduced', str(dict(mm)), 'needs stripping the ArchiCAD numeric suffix from material names')
by = collections.defaultdict(set)
for x in d.by_type('IfcWall'):
    if flat_props(x).get(('Pset_WallCommon', 'IsExternal')) is False: by[tname(x)].update(mats(x))
ok67 = by['Basiswand:GK 75 - Toilettentrennwand'] == {'Trockenbau - Gipsplatte', 'Dämmung - weich'} and len(by) == 5
rec(67, 'reproduced' if ok67 else 'not reproduced', f'{len(by)} interior types')
n277 = sum(1 for s in h.by_type('IfcSlab') if re.search('himling', s.Name or '', re.I) or re.match('(Dekke|Tak)', s.Name or ''))
rec(223, 'reproduced' if n277 == 277 else 'not reproduced', f'name-keyword ceiling slabs {n277}', 'non-obvious: himling|^Dekke|^Tak name filter (includes 54 decks and 20 roofing-felt slabs)')
# mep
T = f.by_type('IfcFlowTerminal'); per = collections.Counter(sname(x) for x in T)
rec(192, 'reproduced' if len(T) == 115 and set(per.values()) == {23} else 'not reproduced', f'{len(T)} terminals; per storey {dict(per)}; IfcSystem {len(f.by_type("IfcSystem"))}', 'system grouping in the reference is invented (no IfcSystem)')
rec(31, 'reproduced' if len(a.by_type('IfcFlowTerminal')) == 0 else 'contradicted', 'ac20 IfcFlowTerminal 0')
rec(248, 'reproduced' if all(tname(x) in ('BASIN', 'TOILET', 'SINK', 'SHOWER', 'URINAL') for x in h.by_type('IfcFlowTerminal')) else 'contradicted', 'hitos terminals are all sanitary types')
# metadata
p = f.by_type('IfcProject')[0]; s = f.by_type('IfcSite')[0]; b = f.by_type('IfcBuilding')[0]
rec(163, 'reproduced' if (p.Name == '130625' and s.RefLatitude[:2] == (48, 8) and b.Name == 'Bürogebäude') else 'not reproduced', f'{p.Name} {p.LongName} {s.RefLatitude} {b.Name}', 'usage Office inferred from name')
rec(50, 'reproduced' if 'ViewDefinition [ReferenceView_V1.2]' in d.header.file_description.description else 'not reproduced', str(d.header.file_description.description))
rec(0, 'reproduced' if a.by_type('IfcBuilding')[0].Name == 'Buerogebaeude' and len(a.by_type('IfcBuildingStorey')) == 5 else 'not reproduced', 'Buerogebaeude, 5 storeys', 'type inferred from name')
# performance
wp = [(k, v) for x in du.by_type('IfcWindow') for k, v in flat_props(x).items() if 'arrant' in k[1] and not ph(v, k[1])]
rec(142, 'reproduced' if not wp else 'contradicted', f'non-placeholder warranty values: {len(wp)}')
rl = [m for m in mats(du.by_type('IfcRoof')[0])]
rec(136, 'partial', str(rl), "2 membrane layers ('Roofing - Barrier', 'Roofing - EPDM Membrane'); none named vapour barrier/retarder")
ll = [k for x in du.by_type('IfcSlab') for k in flat_props(x) if re.search('live|imposed|nutzlast', k[1], re.I)]
rec(128, 'reproduced' if not ll else 'contradicted', f'live-load properties: {len(ll)}')
# spaces
bath = [s.Name for s in du.by_type('IfcSpace') if 'Bath' in (s.LongName or '')]
rec(159, 'reproduced' if len(bath) == 4 else 'not reproduced', str(bath))
fl = collections.defaultdict(float)
for s in f.by_type('IfcSpace'): fl[sname(s)] += flat_props(s, False)[('PSet_Room', 'Area')]
rec(166, 'reproduced' if round(sum(fl.values()), 2) == 1613.73 and round(fl['OG1'], 2) == 299.30 else 'not reproduced', str({k: round(v, 2) for k, v in fl.items()}))
io = collections.defaultdict(list)
for s in f.by_type('IfcSpace'):
    if (s.LongName or '').startswith('Individual office'): io[sname(s)].append(flat_props(s, False)[('PSet_Room', 'Area')])
rec(179, 'reproduced' if all(len(v) == 4 and round(sum(v), 2) == 44.34 for v in io.values()) and len(io) == 5 else 'not reproduced', str({k: (len(v), round(sum(v), 2)) for k, v in io.items()}))
# structural
rec(40, 'reproduced' if len(a.by_type('IfcBeam')) == 0 else 'contradicted', 'ac20 IfcBeam 0')
nb, nc, ns = (len(d.by_type(c)) for c in ['IfcBeam', 'IfcColumn', 'IfcSlab'])
rat = [round(100*x/(nb+nc+ns), 1) for x in (nb, nc, ns)]
rec(97, 'model facts reproduced; rest unverifiable', f'ratios {rat}', 'efficiency rating is opinion')
sc = collections.Counter(s.PredefinedType for s in a.by_type('IfcSlab'))
rec(39, 'reproduced' if (len(a.by_type('IfcColumn')) == 2 and sc == {'ROOF': 21, 'FLOOR': 5}) else 'not reproduced', f'columns {len(a.by_type("IfcColumn"))} slabs {dict(sc)}')
# takeoff
perim = sum(flat_props(s, False).get(('PSet_Revit_Dimensions', 'Perimeter')) or 0 for s in du.by_type('IfcSpace') if s.Name != 'R301')
rec(145, 'reproduced (negative; but estimable)', f'no skirting elements; sum of room perimeters {perim:.1f} m')
fa = sum(flat_props(x).get(('PSet_Revit_Dimensions', 'Area')) or 0 for x in du.by_type('IfcWall') if 'Exterior - Brick' in (x.Name or ''))
rec(143, 'reproduced (estimate within 2%)' if abs(fa/275-1) <= 0.02 else 'not reproduced', f'Exterior-Brick wall Revit Area {fa:.1f} m2 vs ~275', 'all IsExternal walls would give 410.8 (party + foundation walls)')
fv = sum(flat_props(x).get(('PSet_Revit_Dimensions', 'Volume')) or 0 for x in du.by_type('IfcFooting'))
rec(144, 'reproduced' if round(fv, 3) == 16.528 else 'not reproduced', f'footing volume sum {fv:.3f}')

sample = json.load(open('v_sample.json'))
rows = []
for cat, q, checked in sample:
    st, facts, note = R[q]
    rows.append(dict(q=q, category=cat, analyst_checked=checked, model=QS[q]['path'].split('/')[-1][:-8], status=st, facts=facts, note=note))
with open('v_repro_results.csv', 'w') as fh:
    wr = csv.DictWriter(fh, fieldnames=rows[0].keys()); wr.writeheader(); wr.writerows(rows)
for r in rows: print(r['q'], r['category'], r['status'], '|', r['facts'][:90])
cnt = collections.Counter(r['status'] for r in rows)
print(cnt)
print('unchecked subset:', collections.Counter(r['status'] for r in rows if not r['analyst_checked']))

# F6: "types with quantities" lists. Own parser + own label candidates.
import sys, re, collections, csv
sys.path.insert(0, '.')
from vlib import *

QS = Q()
M = {'ac20_arc': 'ac20', 'digital_hub_arc': 'dh', 'duplex_arc': 'duplex', 'fantasy_office_building_3_arc': 'fantasy', 'hitos_arc': 'hitos'}

def hitos_layer(f):
    lay = {}
    for pla in f.by_type('IfcPresentationLayerAssignment'):
        for it in pla.AssignedItems:
            lay[it.id()] = pla.Name
    def get(e):
        out = set()
        if e.Representation:
            for r in e.Representation.Representations:
                if r.id() in lay: out.add(lay[r.id()])
                for it in r.Items:
                    if it.id() in lay: out.add(lay[it.id()])
        return ' '.join(sorted(out))
    return get

def ext_flag(m, f):
    if m == 'ac20':
        return lambda w: flat_props(w).get(('ArchiCADProperties', 'Ebene')) == 'Außenwände'
    if m == 'hitos':
        g = hitos_layer(f)
        return lambda w: 'Yttervegger' in g(w)
    return lambda w: flat_props(w).get(('Pset_WallCommon', 'IsExternal')) is True

# q -> (class, filter, stop-regex for parsing)
JOBS = {11: ('IfcDoor', None), 58: ('IfcDoor', None), 180: ('IfcDoor', None), 208: ('IfcDoor', None),
        14: ('IfcWindow', None), 59: ('IfcWindow', None), 181: ('IfcWindow', None), 210: ('IfcWindow', None),
        17: ('IfcWall', None), 60: ('IfcWall', None), 182: ('IfcWall', None), 212: ('IfcWall', None),
        18: ('IfcWall', 'ext'), 61: ('IfcWall', 'ext'), 183: ('IfcWall', 'ext'), 213: ('IfcWall', 'ext'),
        19: ('IfcWall', 'int'), 62: ('IfcWall', 'int'), 184: ('IfcWall', 'int'), 214: ('IfcWall', 'int'),
        41: ('IfcColumn', None), 86: ('IfcColumn', None), 197: ('IfcColumn', None), 238: ('IfcColumn', None),
        85: ('IfcBeam', None), 237: ('IfcBeam', None), 35: ('IfcRailing', None), 79: ('IfcRailing', None), 230: ('IfcRailing', None),
        33: ('IfcStair', None), 228: ('IfcStair', None), 78: ('IfcCovering', None), 190: ('IfcCurtainWall', None),
        30: ('IfcFurnishingElement', None), 224: ('IfcFurnishingElement', None), 77: ('IfcSlab', 'FLOOR'), 90: ('IfcSlab', None)}
STOP = re.compile(r'^\s*(Column Materials|Furniture Types:|Related Circulation|Steel Beams|Concrete Beams|Kitchen Furniture|Available Thickness|Window types with dimensions:XX)', re.I)

def parse(ans):
    out = []
    started = False
    for line in ans.split('\n'):
        if STOP.search(line) and started:
            break
        g = re.match(r'^\s*[-•]\s*(.+):\s*(\d+)\s*(?:[A-Za-z(]|$)', line)
        if g and not re.match(r'^\s*[-•]\s*(Size|Diameter|Thickness)', line):
            out.append((g.group(1).strip(), int(g.group(2))))
            started = True
    return out

def total_of(ans):
    g = re.search(r'Total[^:\n]*:\s*(\d+)', ans)
    return int(g.group(1)) if g else None

def label_sources(e):
    t = ue.get_type(e)
    nm = e.Name or ''
    ot = getattr(e, 'ObjectType', None) or ''
    tn = t.Name if t is not None else None
    return {
        'type.Name': tn,
        'element.Name': nm,
        'element.ObjectType': ot,
        'type.Name|element.Name (fixed rule)': tn if tn else nm,
        'Name minus :id': re.sub(r':\d+$', '', nm),
        'Name before first colon': nm.split(':')[0],
        'ObjectType before colon': ot.split(':')[0] if ot else None,
        'Name minus -digit': re.sub(r'-\d+$', '', nm),
        'type family (type.Name before colon)': tn.split(':')[0] if tn else None,
    }

rows = []
for k, (cls, flt) in JOBS.items():
    q = QS[k]; m = M[q['path'].split('/')[-1][:-4]]; f = load(m)
    els = f.by_type(cls)
    if flt in ('ext', 'int'):
        ef = ext_flag(m, f)
        els = [e for e in els if ef(e) == (flt == 'ext')]
    elif flt == 'FLOOR':
        els = [e for e in els if e.PredefinedType == 'FLOOR']
    ref = parse(q['answer'])
    reft = total_of(q['answer'])
    ref = [(None if re.match(r'^(Unknown|Unnamed)', l) else l, n) for l, n in ref]
    refc = collections.Counter(dict(ref)) if len(set(l for l, _ in ref)) == len(ref) else None
    best = []
    for src in label_sources(els[0]).keys() if els else []:
        c = collections.Counter((label_sources(e)[src] or None) for e in els)
        exact = (refc is not None and dict(c) == dict(refc))
        matched = sum(1 for l, n in ref if c.get(l) == n)
        if exact: best.append(src)
        rows.append(dict(q=k, model=m, cls=cls + (('/' + flt) if flt else ''), src=src, n_el=len(els), ref_total=reft,
                         total_ok=(reft == len(els)), ref_labels=len(ref), labels_ok=matched, exact=exact,
                         count_multiset=(sorted(c.values()) == sorted(n for _, n in ref))))
    print(k, m, cls, flt, 'n_el', len(els), 'ref_total', reft, 'ref_labels', len(ref), 'exact_by', best,
          'ref_sum', sum(n for _, n in ref))
w = csv.DictWriter(open('v_types.csv', 'w'), fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

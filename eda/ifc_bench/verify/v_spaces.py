# Check every per-level space list (and level totals) against my own extraction.
import sys, re, collections, csv
sys.path.insert(0, '.')
from vlib import *

QS = Q()
CANDS = {
    'ac20': [('BaseQuantities', 'NetFloorArea'), ('BaseQuantities', 'GrossFloorArea'), ('BaseQuantities', 'SpaceNetFloorAreaBOMA'), ('BaseQuantities', 'SpaceUsableFloorAreaBOMA')],
    'dh': [('Qto_SpaceBaseQuantities', 'NetFloorArea'), ('Qto_SpaceBaseQuantities', 'GrossFloorArea')],
    'fantasy': [('PSet_Room', 'Area')],
    'hitos': [(None, 'NetFootprintArea')],
}
# question index -> (model, storey, id field used by the reference)
JOBS = {4: ('ac20', 'Keller'), 5: ('ac20', 'Erdgeschoss'), 6: ('ac20', '1. Obergeschoss'), 7: ('ac20', '2. Obergeschoss'), 8: ('ac20', 'Dachgeschoss'),
        52: ('dh', 'B01_OKRD'), 53: ('dh', 'E00_OKRD'), 54: ('dh', 'E01_OKRD'),
        167: ('fantasy', 'EG'), 168: ('fantasy', 'OG1'), 169: ('fantasy', 'OK OG2'), 170: ('fantasy', 'OK OG3'), 171: ('fantasy', 'OK OG4'),
        201: ('hitos', 'kjeller'), 202: ('hitos', '1.etg'), 203: ('hitos', '1.etg'), 204: ('hitos', '2.etg'), 205: ('hitos', '3.etg')}

def parse(m, k, ans):
    pairs = []
    if m == 'dh':
        for g in re.finditer(r'-\s*(.+?) \(([^()]+)\):\s*([\d.]+) sq m', ans):
            pairs.append((g.group(2).strip(), g.group(3)))
    elif m == 'fantasy':
        for g in re.finditer(r'-\s*([^:\n]+?):\s*([\d.]+) sq m', ans):
            pairs.append((g.group(1).strip(), g.group(2)))
    elif m == 'hitos' and k == 202:
        for g in re.finditer(r'([0-9][\w.\-]*) \(([\d.]+) sq m\)', ans):
            pairs.append((g.group(1), g.group(2)))
    else:
        for g in re.finditer(r'-\s*([^:\n]+?):\s*([^\n(]+?)\s*\(([\d.]+) sq m\)', ans):
            pairs.append((g.group(1).strip(), g.group(3)))
        for g in re.finditer(r'^\s*-\s*([^:\n]+?):\s*([\d.]+) sq m', ans, re.M):
            pairs.append((g.group(1).strip(), g.group(2)))
    tot = re.search(r'Total (?:[\w ]+ )?Area: ([\d.]+) sq m', ans) or re.search(r'Total NetFootprintArea: ([\d.]+)', ans)
    cnt = re.search(r'(\d+) spaces', ans)
    return pairs, (tot.group(1) if tot else None), (int(cnt.group(1)) if cnt else None)

rows = []
for k, (m, st) in JOBS.items():
    ans = QS[k]['answer']
    pairs, tot, cnt = parse(m, k, ans)
    f = load(m)
    sps = [s for s in f.by_type('IfcSpace') if sname(s) == st]
    idf = (lambda s: s.LongName) if m == 'fantasy' else (lambda s: s.Name)
    for cand in CANDS[m]:
        vals = collections.defaultdict(list)
        total = 0.0
        for s in sps:
            v = flat_props(s, False).get(cand)
            vals[idf(s)].append(v)
            total += v or 0
        ok = 0
        for rid, ra in pairs:
            dec = len(ra.split('.')[1]) if '.' in ra else 0
            if any(v is not None and round(v + 1e-9, dec) == float(ra) for v in vals.get(rid, [])):
                ok += 1
        dec = len(tot.split('.')[1]) if tot and '.' in tot else 1
        rows.append(dict(q=k, model=m, storey=st, cand='.'.join(str(c) for c in cand), n_spaces=len(sps), ref_count=cnt,
                         ref_pairs=len(pairs), pairs_ok=ok, ref_total=tot, my_total=round(total, 3),
                         total_ok=(tot is not None and round(total + 1e-9, dec) == float(tot)),
                         sum_of_rounded=round(sum(round(v[0] + 1e-9, 1) for v in vals.values() if v[0] is not None) if False else sum(round((x or 0) + 1e-9, dec) for xs in vals.values() for x in xs), 3)))
w = csv.DictWriter(open('v_spaces.csv', 'w'), fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
for r in rows:
    print(r)

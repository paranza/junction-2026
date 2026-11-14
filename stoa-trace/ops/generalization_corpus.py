#!/usr/bin/env python3
"""Build and score an evaluation-only corpus without sending reference answers.

All drawings, private seeds and reference labels stay under the ignored output
directory. This module is never imported by the application. No network/model
requests occur here. A reserved score requires an explicit tested code revision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import re
import secrets
from datetime import datetime, timezone

FORMATS = ('png', 'jpg', 'pdf', 'svg', 'tiff', 'webp')
QUESTIONS = {
    'doors': 'How many doors are shown on this floor plan? Count each doorway fitted with a door once.',
    'windows': 'How many windows are shown on this floor plan?',
    'printed_area': 'What is the total of the printed room areas, in square metres?',
    'dimensioned_area': 'What is the area of the rectangular footprint in square metres, using the printed overall dimensions?',
    'unscaled_area': 'What is the total floor area in square metres?',
}


def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def load_lines(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def transformed_box(box, angle, width=1200, height=1000):
    rad = math.radians(angle)
    points = []
    for x, y in ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])):
        dx, dy = x - width / 2, y - height / 2
        points.append((width / 2 + dx * math.cos(rad) - dy * math.sin(rad),
                       height / 2 + dx * math.sin(rad) + dy * math.cos(rad)))
    return [min(p[0] for p in points) / width, min(p[1] for p in points) / height,
            max(p[0] for p in points) / width, max(p[1] for p in points) / height]


def schematic(seed, area_kind):
    """Return ordinary SVG primitives and a separate evaluator reference."""
    rng = random.Random(seed)
    n = rng.randint(2, 5)
    physical_width, physical_height = rng.randint(9, 17), rng.randint(7, 11)
    angle = rng.choice((0, 90, 180, 270))
    x0, x1, y0, divider, y1 = 150, 1050, 150, rng.choice((610, 650, 690)), 800
    step = (x1 - x0) / n
    radius = rng.choice((44, 52, 58))
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1000" viewBox="0 0 1200 1000">',
           '<rect width="1200" height="1000" fill="white"/>',
           '<text x="45" y="42" font-family="Arial" font-size="21">Schematic evaluation drawing; not construction documentation</text>',
           f'<g transform="rotate({angle} 600 500)" stroke="#181818" stroke-linecap="square">']
    def line(a, b, width=7, color='#181818'):
        svg.append(f'<path d="M {a[0]:.3f} {a[1]:.3f} L {b[0]:.3f} {b[1]:.3f}" fill="none" stroke="{color}" stroke-width="{width}"/>')
    def text(x, y, value, size=22):
        svg.append(f'<text x="{x:.3f}" y="{y:.3f}" fill="#181818" stroke="none" font-family="Arial" font-size="{size}">{value}</text>')
    line((x0, y0), (x1, y0))
    line((x0, y0), (x0, y1)); line((x1, y0), (x1, y1))
    doors, windows, printed = [], [], []
    for i in range(n):
        left, right = x0 + i * step, x0 + (i + 1) * step
        if i:
            line((left, y0), (left, divider))
        center = (left + right) / 2 + rng.uniform(-step * .12, step * .12)
        reverse = rng.choice((False, True))
        gap_left, gap_right = center - radius / 2, center + radius / 2
        line((left, divider), (gap_left, divider)); line((gap_right, divider), (right, divider))
        hinge = gap_right if reverse else gap_left
        sign = -1 if reverse else 1
        line((hinge, divider), (hinge, divider - radius), 2.5)
        sweep = 1 if reverse else 0
        svg.append(f'<path d="M {hinge + sign * radius:.3f} {divider} A {radius} {radius} 0 0 {sweep} {hinge:.3f} {divider-radius}" fill="none" stroke-width="2.5"/>')
        doors.append(transformed_box([gap_left - 4, divider-radius-4, gap_right+4, divider+4], angle))
        # A double glazing line is distinct from the door leaf and quarter arc.
        wx0, wx1 = left + step * .28, left + step * .72
        line((wx0, y0), (wx1, y0), 11, 'white')
        line((wx0, y0-4), (wx1, y0-4), 2); line((wx0, y0+4), (wx1, y0+4), 2)
        line((wx0, y0-6), (wx0, y0+6), 2); line((wx1, y0-6), (wx1, y0+6), 2)
        windows.append(transformed_box([wx0-3, y0-9, wx1+3, y0+9], angle))
        text(left + step * .15, y0 + (divider-y0) * .45, f'Room {chr(65+i)}')
        area = round((physical_width / n) * physical_height * ((divider-y0)/(y1-y0)), 2)
        printed.append(area)
        if area_kind == 'printed_area':
            text(left + step * .15, y0 + (divider-y0) * .45 + 35, f'{area:g} m²')
    entry = rng.uniform(x0 + 250, x1 - 250)
    line((x0, y1), (entry, y1)); line((entry+radius, y1), (x1, y1))
    line((entry, y1), (entry, y1-radius), 2.5)
    svg.append(f'<path d="M {entry+radius:.3f} {y1} A {radius} {radius} 0 0 0 {entry:.3f} {y1-radius}" fill="none" stroke-width="2.5"/>')
    doors.append(transformed_box([entry-4, y1-radius-4, entry+radius+4, y1+4], angle))
    text(x0+80, divider+65, 'Hall')
    hall_area = round(physical_width * physical_height * ((y1-divider)/(y1-y0)), 2)
    printed.append(hall_area)
    if area_kind == 'printed_area':
        text(x0+80, divider+100, f'{hall_area:g} m²')
    if area_kind == 'dimensioned_area':
        text(x0+250, y1+65, f'Overall width {physical_width:g} m', 24)
        text(x0+250, y1+98, f'Overall height {physical_height:g} m', 24)
    if area_kind == 'unscaled_area':
        text(x0+200, y1+65, 'Scale and dimensions not supplied', 22)
    svg.append('</g></svg>')
    area = sum(printed) if area_kind == 'printed_area' else physical_width*physical_height if area_kind == 'dimensioned_area' else None
    return ''.join(svg), {'doors':len(doors), 'windows':len(windows), 'area':area,
                          'door_boxes':doors, 'window_boxes':windows, 'area_kind':area_kind}


def write_drawing(svg, path):
    import pymupdf
    from PIL import Image
    raw = svg.encode()
    if path.suffix == '.svg':
        path.write_bytes(raw); return
    with pymupdf.open(stream=raw, filetype='svg') as source:
        if path.suffix == '.pdf':
            path.write_bytes(source.convert_to_pdf()); return
        pix = source[0].get_pixmap(alpha=False)
        image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        if path.suffix == '.jpg':
            image.save(path, quality=88)
        elif path.suffix == '.webp':
            image.save(path, quality=90)
        elif path.suffix == '.tiff':
            image.save(path, compression='tiff_lzw')
        else:
            image.save(path)


def generate(output, external_metadata=None, per_format=1):
    if (output/'freeze.json').exists():
        raise ValueError('Corpus is frozen; choose a new output directory instead of changing its cases.')
    output.mkdir(parents=True, exist_ok=True)
    (output/'inputs').mkdir(exist_ok=True)
    seed_path = output/'private-seeds.json'
    seeds = json.loads(seed_path.read_text()) if seed_path.exists() else {'development':2026111401,'reserved':secrets.randbits(64)}
    dump(seed_path, seeds)
    public, all_cases = [], {'development':[], 'reserved':[]}
    for split in all_cases:
        rng = random.Random(seeds[split])
        modes=['printed_area','dimensioned_area','unscaled_area']*(2*per_format)
        rng.shuffle(modes)
        for fi, extension in enumerate(FORMATS):
            for j in range(per_format):
                seed = rng.getrandbits(64)
                area_kind = modes[fi*per_format+j]
                svg, reference = schematic(seed, area_kind)
                group = digest({'split':split,'seed':seed,'extension':extension})[:20]
                path = output/'inputs'/(group+'.'+extension)
                write_drawing(svg, path)
                for task in ('doors','windows','area'):
                    key = reference['area_kind'] if task=='area' else task
                    case = {'case_id':digest({'group':group,'task':task})[:20], 'group_id':group,
                            'path':path.relative_to(output).as_posix(), 'question':QUESTIONS[key], 'task':task,
                            'kind':'procedural','split':split,'expected_value':reference[task],
                            'unit':'m²' if task=='area' else 'count','scoreable':True,
                            'reference_basis':'Generated geometry and printed source values; evaluation-only reference, never sent to inference.'}
                    if task != 'area': case['expected_boxes']=reference[task[:-1]+'_boxes']
                    all_cases[split].append(case)
                public.append({'group_id':group,'kind':'procedural','format':extension,'split':split,
                               'sha256':digest(path.read_bytes())})
    if external_metadata:
        for row in json.loads(external_metadata.read_text()):
            path=output/row['input_path']
            if not path.is_file() or digest(path.read_bytes()) != row['sha256']:
                raise ValueError('External input is missing or changed.')
            refs=row.get('references') or [{'task':'doors'},{'task':'area'}]
            for ref in refs:
                task=ref['task']
                all_cases['reserved'].append({'case_id':digest({'external':row['source_id'],'task':task})[:20],
                    'group_id':row['source_id'],'path':row['input_path'],'question':ref.get('question') or QUESTIONS['doors' if task=='doors' else 'unscaled_area'],
                    'task':task,'kind':'external','split':'reserved','expected_value':ref.get('expected_value'),
                    'unit':'m²' if task=='area' else 'count','scoreable':bool(ref.get('reviewed')),
                    'reference_basis':ref.get('note','Unreviewed or ambiguous; excluded from numeric accuracy.')})
            public.append({k:row[k] for k in ('source_id','source_title','source_url','original_url','license','license_url','author','sha256','split')})
    for split,cases in all_cases.items():
        dump(output/(split+'-gold.json'),{'schema_version':1,'split':split,'cases':cases})
        requests=[{k:c[k] for k in ('case_id','path','question','task','kind')} for c in cases]
        (output/(split+'-requests.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in requests))
    freeze={'schema_version':1,'frozen_at':datetime.now(timezone.utc).isoformat(),'scope':'App-unseen inputs, not a claim that foundation models never saw public sources.',
            'inputs':public,'splits':{s:{'groups':len({c['group_id'] for c in rows}),'questions':len(rows),
                'request_sha256':digest((output/(s+'-requests.jsonl')).read_bytes()),'private_gold_sha256':digest((output/(s+'-gold.json')).read_bytes())} for s,rows in all_cases.items()},
            'private_seed_hash':digest(seeds),'policy':'Use development for changes. Release reserved cases only after a code freeze. Do not train on either set; inspect reserved errors only after scoring the frozen code.'}
    dump(output/'freeze.json',freeze)
    return freeze


def overlap(a,b):
    if not isinstance(a,list) or not isinstance(b,list) or len(a)!=4 or len(b)!=4:return 0
    if not all(type(x) in (int,float) and math.isfinite(x) for x in a+b):return 0
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=max(0,a[2]-a[0])*max(0,a[3]-a[1])+max(0,b[2]-b[0])*max(0,b[3]-b[1])-intersection
    return intersection/union if union>0 else 0


def score(gold, answers, code_revision):
    if not isinstance(code_revision,str) or not re.fullmatch('[a-fA-F0-9]{7,40}',code_revision):raise ValueError('Record the tested Git code revision.')
    expected={(c['path'],c['question']):c for c in gold['cases']}
    if len(expected)!=len(gold['cases']):raise ValueError('Duplicate reference request.')
    seen=set();results=[]
    for answer in answers:
        key=(answer.get('path'),answer.get('question'))
        if key not in expected:raise ValueError('Answer does not belong to the frozen reference set.')
        if key in seen:raise ValueError('Duplicate answer row.')
        seen.add(key);case=expected[key]
        value=answer.get('value');numeric=type(value) in (int,float) and math.isfinite(value)
        valid=(answer.get('status') in {'supported','computed','visual','needs_review','insufficient_evidence','not_answered','unknown'}
               and isinstance(answer.get('answer'),str) and not answer.get('error'))
        if not case.get('scoreable'):correct=None
        elif case['expected_value'] is None:correct=valid and value is None
        elif not numeric or not valid:correct=False
        elif case['unit']=='count':correct=value==case['expected_value'] and answer.get('unit')=='count'
        else:
            factors={'m²':1,'m2':1,'ft²':.09290304,'ft2':.09290304,'mm²':1e-6,'cm²':1e-4}
            converted=value*factors[answer['unit']] if answer.get('unit') in factors else None
            correct=converted is not None and abs(converted-case['expected_value'])<=max(.01,abs(case['expected_value'])*.02)
        row={'case_id':case['case_id'],'kind':case['kind'],'task':case['task'],'scoreable':case['scoreable'],
                        'reference_requires_abstention':case.get('scoreable') and case['expected_value'] is None,
                        'answered_numeric':numeric and valid,'correct':correct,'error':not valid}
        if case.get('expected_boxes') is not None:
            prediction=[e.get('bbox') for e in answer.get('evidence',[]) if not e.get('excluded')]
            reference=case['expected_boxes'];edges=[]
            for pi,pbox in enumerate(prediction):
                for ri,rbox in enumerate(reference):
                    amount=overlap(pbox,rbox)
                    if amount>=.3:edges.append((amount,pi,ri))
            used_p,used_r=set(),set()
            for _,pi,ri in sorted(edges,reverse=True):
                if pi not in used_p and ri not in used_r:used_p.add(pi);used_r.add(ri)
            row.update(evidence_tp=len(used_p),evidence_fp=len(prediction)-len(used_p),evidence_fn=len(reference)-len(used_r))
        results.append(row)
    numeric=[r for r in results if r['scoreable'] and not r['reference_requires_abstention']]
    abstain=[r for r in results if r['reference_requires_abstention']]
    located=[r for r in results if 'evidence_tp' in r]
    tp,fp,fn=(sum(r[k] for r in located) for k in ('evidence_tp','evidence_fp','evidence_fn'))
    return {'schema_version':1,'code_revision':code_revision,'split':gold.get('split'),'provided_answers':len(results),
            'unrun_cases':len(expected)-len(results),'numeric_cases':len(numeric),'numeric_correct':sum(r['correct'] for r in numeric),
            'numeric_answered':sum(r['answered_numeric'] for r in numeric),
            'numeric_accuracy':sum(r['correct'] for r in numeric)/len(numeric) if numeric else None,
            'required_abstention_cases':len(abstain),'correct_required_abstentions':sum(r['correct'] for r in abstain),
            'unscored_cases':sum(not r['scoreable'] for r in results),'errors':sum(r['error'] for r in results),
            'localized_reference_cases':len(located),'object_precision':tp/(tp+fp) if tp+fp else None,
            'object_recall':tp/(tp+fn) if tp+fn else None,'object_iou_threshold':.3,
            'results':results,'limitations':'Unrun cases and ambiguous external references are explicit; small corpus, synthetic conventions and analyst annotations do not establish universal accuracy.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    build=sub.add_parser('generate');build.add_argument('--output-dir',type=Path,required=True);build.add_argument('--external-metadata',type=Path);build.add_argument('--per-format',type=int,default=1)
    select=sub.add_parser('requests');select.add_argument('--corpus',type=Path,required=True);select.add_argument('--split',choices=('development','reserved'),required=True);select.add_argument('--kind',choices=('all','procedural','external'),default='all');select.add_argument('--tasks',default='doors,area');select.add_argument('--output',type=Path,required=True)
    grade=sub.add_parser('score');grade.add_argument('--gold',type=Path,required=True);grade.add_argument('--answers',type=Path,required=True);grade.add_argument('--code-revision',required=True);grade.add_argument('--release-reserved',action='store_true');grade.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='generate':
            if not 1<=args.per_format<=10:raise ValueError('--per-format must be from 1 to 10.')
            result=generate(args.output_dir,args.external_metadata,args.per_format)
            print(json.dumps({'frozen':str(args.output_dir/'freeze.json'),'splits':result['splits']}));return 0
        if args.command=='requests':
            tasks=set(args.tasks.split(','))
            if not tasks or not tasks<={'counts','doors','windows','area','labelled_rooms','bathtubs'}:raise ValueError('Choose counts,doors,windows,area,labelled_rooms,bathtubs tasks.')
            rows=load_lines(args.corpus/(args.split+'-requests.jsonl'))
            rows=[r for r in rows if (r['task'] in tasks or ('counts' in tasks and r['task']!='area')) and (args.kind=='all' or r['kind']==args.kind)]
            if args.output.exists():raise ValueError('Refusing to overwrite selected requests.')
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(''.join(json.dumps({k:r[k] for k in ('case_id','path','question')},ensure_ascii=False)+'\n' for r in rows))
            print(json.dumps({'requests':len(rows),'output':str(args.output)}));return 0
        gold=json.loads(args.gold.read_text())
        if gold.get('split')=='reserved' and not args.release_reserved:raise ValueError('Reserved scoring requires --release-reserved after freezing code.')
        freeze_path=args.gold.parent/'freeze.json'
        if freeze_path.exists():
            frozen=json.loads(freeze_path.read_text())['splits'][gold['split']]['private_gold_sha256']
            if digest(args.gold.read_bytes())!=frozen:raise ValueError('Reference labels changed after the freeze.')
        result=score(gold,load_lines(args.answers),args.code_revision);dump(args.output,result)
        print(json.dumps({k:v for k,v in result.items() if k!='results'}));return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        parser.error(str(exc))


if __name__=='__main__':
    raise SystemExit(main())

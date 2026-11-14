"""Frozen paired development checks for complex drawings, separate from reserves.

Input JSON is private: cases contain file/question/expected/unit/tolerance.
Expected values are used only AFTER inference and are never model inputs.
Outputs include raw responses and must stay outside version control.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cases',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--baseline-ref',default='509d050')
    parser.add_argument('--max-attempts',type=int,default=96)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--candidate-only',action='store_true')
    args=parser.parse_args()
    if not 1<=args.max_attempts<=200 or not 1<=args.workers<=3:parser.error('Bounds: 1–200 attempts, 1–3 workers.')
    args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=True)
    if any(args.output.iterdir()):parser.error('Use a fresh output directory; prior results are immutable.')
    root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
    from server.config import load_environment
    load_environment(root)
    os.environ.update(STOA_PROVIDER='gemini',STOA_MODEL='gemini-4-carbon',STOA_COMPLEX_READER='auto',
        STOA_COMPLEX_MODEL='gemini-4-argon',STOA_RUNTIME_DIR=str(args.output/'runtime'),
        STOA_DATA_ROOT=str(args.output/'empty-data'),STOA_MAX_MODEL_CALLS=str(args.max_attempts),
        STOA_GEMINI_IMAGE_RESOLUTION='high',STOA_GEMINI_THINKING_LEVEL='medium',
        STOA_GEMINI_MAX_OUTPUT_TOKENS='24000',STOA_GEMINI_TIMEOUT_SECONDS='600',
        STOA_ANNOTATION_PROFILE='none',STOA_ACCESS_TOKEN='')
    from server import deep_reader,llm,store
    from server.app import app
    from server.verification import convert_quantity
    from fastapi.testclient import TestClient
    cases=json.loads(args.cases.read_text())['cases']
    source_hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'server').glob('*.py')}
    frozen={'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'server_source_sha256':source_hashes,'cases':cases,'reference_values_sent_to_model':False,
        'max_attempts':args.max_attempts,'baseline_ref':None if args.candidate_only else args.baseline_ref,
        'source_sha256':{c['file']:hashlib.sha256(Path(c['file']).read_bytes()).hexdigest() for c in cases},'frozen_at':time.time()}
    (args.output/'freeze.json').write_text(json.dumps(frozen,indent=2))
    baseline=None
    with tempfile.TemporaryDirectory() as directory:
        if not args.candidate_only:
            previous=Path(directory)/'baseline.py'
            previous.write_bytes(subprocess.check_output(['git','show',args.baseline_ref+':stoa-trace/server/deep_reader.py'],cwd=root))
            spec=importlib.util.spec_from_file_location('server.comparison_baseline',previous)
            baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
            previous_llm=Path(directory)/'baseline_llm.py'
            previous_llm.write_bytes(subprocess.check_output(['git','show',args.baseline_ref+':stoa-trace/server/llm.py'],cwd=root))
            spec=importlib.util.spec_from_file_location('server.comparison_baseline_llm',previous_llm)
            baseline_llm=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline_llm)
            # Preserve old interpretation/preprocessing but share the current
            # request ledger, provider transport and usage accounting.
            baseline_llm._request=llm._request;baseline.llm=baseline_llm
        rows=[];lock=threading.Lock()
        with TestClient(app) as client:
            documents={}
            for name in dict.fromkeys(c['file'] for c in cases):
                p=Path(name)
                with p.open('rb') as stream:r=client.post('/api/upload',files=[('files',(p.name,stream,'application/octet-stream'))])
                r.raise_for_status();doc=r.json()['documents'][0]
                documents[name]=(store.extract(doc['id']),store.get_path(doc['id']))
            def run(job):
                variant,c=job;document,path=documents[c['file']];reader=deep_reader if variant=='candidate' else baseline
                started=time.monotonic()
                with llm.usage_scope():
                    row={'variant':variant,'id':c['id']}
                    try:
                        result=reader.answer(c['question'],document,path,c.get('page',1),c.get('scope','page'),c.get('region'))
                        row['response']=result;value=(result or {}).get('value');row['answered']=value is not None
                        if c.get('expected_abstention'):
                            row['correct']=value is None and bool((result or {}).get('answer'))
                        elif 'expected' in c:
                            numeric=convert_quantity(value,(result or {}).get('unit'),c['unit'])
                            row['correct']=numeric is not None and abs(numeric-c['expected'])<=c.get('tolerance',1e-6)
                        else:row['correct']=None
                    except Exception as exc:
                        row.update(error_type=type(exc).__name__,error=str(exc),correct=False,answered=False)
                    row.update(seconds=time.monotonic()-started,usage=llm.usage_snapshot())
                with lock:
                    rows.append(row);(args.output/'rows.json').write_text(json.dumps(rows,indent=2))
                    print(json.dumps({k:row.get(k) for k in ('variant','id','correct','answered','seconds','error_type')}),flush=True)
            variants=['candidate'] if args.candidate_only else ['baseline','candidate']
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                list(pool.map(run,[(v,c) for c in cases for v in variants]))
            with store.connection() as db:
                attempts=db.execute("select count(*) from events where kind='model_request'").fetchone()[0]
            summary={'variants':{v:{'cases':sum(r['variant']==v for r in rows),
                'correct':sum(r['variant']==v and r['correct'] is True for r in rows),
                'answered':sum(r['variant']==v and r['answered'] for r in rows),
                'errors':sum(r['variant']==v and 'error_type' in r for r in rows),
                'model_calls':sum(r['usage']['model_calls'] for r in rows if r['variant']==v)} for v in variants},
                'reserved_cases':0,'general_accuracy_claim':False,'counter':attempts, 'finished_at':time.time()}
            (args.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)

if __name__=='__main__':main()

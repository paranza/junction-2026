#!/usr/bin/env python3
"""Verify the protected remote workspace without invoking any model API."""
import argparse
import base64
import json
from pathlib import Path
import time
from urllib import request

from check_connections import HealthError, create_ssl_context, request_json
from deploy_verda import ACCESS, read_state, run_remote


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exercise',action='store_true',help='Create and review one native IFC answer')
    parser.add_argument('--restart',action='store_true',help='Restart the app container and verify the same answer persists')
    args=parser.parse_args()
    state=read_state();base=state['url'];ctx=create_ssl_context()
    values=dict(line.split('=',1) for line in ACCESS.read_text().splitlines() if '=' in line)
    credential=values['STOA_ACCESS_USERNAME']+':'+values['STOA_ACCESS_PASSWORD']
    headers={'Authorization':'Basic '+base64.b64encode(credential.encode()).decode()}
    def api(path,method='GET',payload=None):
        return request_json(base+path,headers=headers,method=method,payload=payload,
                            ssl_context=ctx,timeout=45,retries=0)
    report={'url':base,'model_calls':0}
    try:
        request_json(base+'/api/health',ssl_context=ctx,retries=0)
        raise RuntimeError('Workspace was accessible without authentication')
    except HealthError as exc:
        assert exc.http_status==401
        report['unauthenticated_status']=401
    health=api('/api/health')
    assert health['status']=='ok' and health['documents']==913
    report['health']={k:health[k] for k in ('status','documents','model_available')}
    if args.exercise:
        documents=api('/api/documents?search=bsc-esplanades_1807-ep-ar-v18.ifc&limit=10')['documents']
        doc=next(x for x in documents if x['name']=='bsc-esplanades_1807-ep-ar-v18.ifc')
        answer=api('/api/ask','POST',{'document_id':doc['id'],'question':'How many doors are there in the model?',
                                    'mode':'native','scope':'document','page':1})
        assert answer['value']==211 and len(answer['evidence'])==211
        report['native_answer']={'id':answer['id'],'value':answer['value'],
                                 'evidence_count':len(answer['evidence']),'method':answer['method']}
        req=request.Request(base+'/api/documents/'+doc['id']+'/pages/1/image?size=900',headers=headers)
        with request.urlopen(req,context=ctx,timeout=30) as response:
            assert response.headers.get_content_type()=='image/png'
            assert response.read(8)==b'\x89PNG\r\n\x1a\n'
        report['png_preview']='ok'
        reviewed=api('/api/answers/'+answer['id']+'/review','POST',{'excluded_evidence_ids':[answer['evidence'][0]['id']]})
        assert reviewed['value']==210 and reviewed.get('human_reviewed')
        # Restore the original object set so the demonstration is not left with
        # a deliberately excluded real door.
        restored=api('/api/answers/'+answer['id']+'/review','POST',{'excluded_evidence_ids':[]})
        assert restored['value']==211
        saved=api('/api/answers/'+answer['id'])
        assert json.loads(json.dumps(saved))['value']==211
        report['review_and_json_export']='ok'
        if args.restart:
            run_remote(state,'docker restart stoa-junction >/dev/null',timeout=60)
            for attempt in range(20):
                try:
                    saved=api('/api/answers/'+answer['id'])
                    assert saved['value']==211
                    break
                except HealthError:
                    if attempt==19:raise
                    time.sleep(2)
            report['restart_persistence']='ok'
    report['status']='ok'
    print(json.dumps(report,sort_keys=True))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'status':'error','error':type(exc).__name__}))
        raise SystemExit(1)

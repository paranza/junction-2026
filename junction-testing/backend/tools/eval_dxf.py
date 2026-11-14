"""Evaluate the exact DXF parser against swiss_dwellings questions. Run from backend/: python tools/eval_dxf.py"""
import json,sys,collections
sys.path.insert(0,'.')
from stoa.vector_dxf import parse_dxf
from stoa.questions import answer
import os
DS=os.environ.get('STOA_DATA','../../../preview_dataset/')
qs=[json.loads(l) for l in open(DS+'questions.jsonl',encoding='utf8') if 'swiss' in l]
cache={}
ok=collections.Counter();tot=collections.Counter();bad=[]
for x in qs:
  p=x['path'].replace('.pdf','.dxf')
  if p not in cache:
    pl=parse_dxf(DS+p)
    rooms=[dict(id=i,number=r['number'],name=r['name'],area_m2=r['area_label'] if r['area_label'] is not None else round(r['area_geom'] or 0,2),unit=r['unit'],outdoor=r['outdoor'],shaft=r['shaft']) for i,r in enumerate(pl.rooms)]
    objs=[dict(id=f'd{i}',type='door') for i,_ in enumerate(pl.doors)]+[dict(id=f'w{i}',type='window') for i,_ in enumerate(pl.windows)]+[dict(id=f'f{i}',type=f['type']) for i,f in enumerate(pl.fixtures)]
    cache[p]=dict(rooms=rooms,objects=objs,units=[dict(id=u['id']) for u in pl.units if u['id']])
  a=answer(x["question"],cache[p]); a=(a["value"],) if a else None
  key=x['type']+':'+ (x['question'][:40] if x['question'].isascii() else 'nonascii')
  key=x['type']
  tot[key]+=1
  v=a[0] if a else None
  good= v is not None and (v==x['answer'] if x['type']=='count' else abs(v-x['answer'])<=0.02*abs(x['answer']))
  ok[key]+=good
  if not good: bad.append((x['path'][-30:],x['question'][:100],x['answer'],v))
for k in tot: print(k,ok[k],'/',tot[k])
c=collections.Counter(b[1][:45] for b in bad)
for k,v in c.most_common(40): print(v,k)
for b in bad[:25]: print(b)

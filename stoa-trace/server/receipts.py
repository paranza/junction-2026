"""Exports use one persisted answer revision, never a mixture of draft and saved data."""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json


def receipt(answer):
    result = copy.deepcopy(answer)
    review = (answer.get('review') or {}).get('revision',0)
    resolution = len(answer.get('resolution_history') or [])
    result['export_revision'] = f'{review}.{resolution}'
    result['export_schema'] = 'metria-quantity-receipt-v1'
    result['receipt_sha256'] = hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
    return result


def _cell(value):
    if isinstance(value,(dict,list)):
        value = json.dumps(value,ensure_ascii=False)
    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@','\t','\r')):
        return "'" + value
    return value


def csv_receipt(answer):
    stream = io.StringIO(newline='')
    headers = ['record','answer_id','revision','question','value','unit','source_id','label','page','included','bbox','source']
    writer = csv.writer(stream)
    writer.writerow(headers)
    prefix = [answer['id'],answer['export_revision'],answer.get('question','')]
    def row(kind,value=None,unit=None,item=None,included=''):
        item = item or {}
        writer.writerow([_cell(v) for v in [kind,*prefix,value,unit,item.get('id',''),item.get('label',''),
                         item.get('page',''),included,item.get('bbox',''),item.get('source_path','')]])
    working = answer.get('working_quantity') or {}
    row('quantity',working.get('value',answer.get('value')),working.get('unit',answer.get('unit')))
    if working:
        row('machine_quantity',answer.get('value'),answer.get('unit'))
    for group in answer.get('rows') or []:
        row('group',group.get('value'),group.get('unit'),{'label':group.get('label'),'id':','.join(group.get('object_ids',[]))})
    for item in answer.get('evidence') or []:
        row('evidence',item.get('value'),item.get('unit'),item,not item.get('excluded',False))
    return stream.getvalue()

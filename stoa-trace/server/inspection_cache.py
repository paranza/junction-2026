"""Private, source-bound intermediate observations for interrupted inspections.

These are model observations, never reference answers or training examples.
Changing the source, question, coordinates, model or policy prevents reuse.
Only fully audited tiles are retained; a failed tile is always inspected again.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path
from . import store


class InspectionCache:
    def __init__(self, identity):
        folder=Path(__file__).parent
        self.identity={'context':identity,'source_transform_code':{
            name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
            for name in ('inspection_cache.py','rendering.py','drawing_tools.py','scale_alignment.py')}}
        self.root=store.RUNTIME/'cache'/'source-inspection'

    def path(self,tile):
        digest=hashlib.sha256(json.dumps([self.identity,tile],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        return self.root/(digest+'.json')

    def get(self,tile):
        try:
            body=json.loads(self.path(tile).read_text())
            return body if isinstance(body,dict) and body.get('complete') is True else None
        except (OSError,ValueError):return None

    def put(self,tile,result):
        if result.get('complete') is not True:return
        temporary=None
        try:
            self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
            with tempfile.NamedTemporaryFile(mode='w',dir=self.root,delete=False) as target:
                temporary=target.name
                json.dump(result,target,ensure_ascii=False)
            os.replace(temporary,self.path(tile))
        except OSError:
            # A cache write cannot replace an otherwise usable source result.
            pass
        finally:
            if temporary:
                try:os.unlink(temporary)
                except FileNotFoundError:pass

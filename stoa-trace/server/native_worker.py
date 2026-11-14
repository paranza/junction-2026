"""Isolate native drawing parsers from the API's concurrent request threads.

PyMuPDF does not support multithreaded use. Every task owns its process and
parser handles. A native crash becomes a file error instead of killing chats.
"""
from __future__ import annotations
import base64,json,os,subprocess,sys,threading
from pathlib import Path
_slots=threading.BoundedSemaphore(2)
def in_worker():
    return os.environ.get('METRIA_NATIVE_WORKER')=='1'
def call(operation,**arguments):
    request=json.dumps({'operation':operation,**arguments}).encode()
    env=dict(os.environ,METRIA_NATIVE_WORKER='1')
    for key in tuple(env):
        if any(value in key for value in ('API_KEY','CLIENT_SECRET','ACCESS_TOKEN','ACCESS_PASSWORD')) or key=='CLOUDINARY_URL':env.pop(key,None)
    try:
        with _slots:
            result=subprocess.run([sys.executable,'-m','server.native_worker'],input=request,
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,cwd=Path(__file__).resolve().parent.parent,
                env=env,timeout=240)
    except subprocess.TimeoutExpired:
        raise ValueError('Native drawing parser timed out') from None
    if result.returncode or len(result.stdout)>256*1024*1024:
        raise ValueError('Native drawing parser could not read this file')
    try:
        response=json.loads(result.stdout)
        if not response.get('ok'):raise ValueError()
        return response['result']
    except (ValueError,KeyError,TypeError):
        raise ValueError('Native drawing parser could not read this file') from None

def main():
    request=json.load(sys.stdin);operation=request['operation'];path=Path(request['path'])
    if operation=='extract':
        from .extraction import extract_document
        result=extract_document(path,Path(request['data_root']))
    elif operation=='render':
        from .rendering import render_page,png_bytes
        image,source=render_page(path,request['page'],request['max_edge'])
        result={'png':base64.b64encode(png_bytes(image)).decode(),'source':str(source)}
    elif operation in {'raster_region','region'}:
        from .rendering import render_region,png_bytes
        image=render_region(path,request['page'],request['region'],request['max_edge'])
        result={'png':base64.b64encode(png_bytes(image)).decode()}
    elif operation=='dxf':
        from .rendering import dxf_render
        pdf,transform=dxf_render(path)
        result={'pdf':base64.b64encode(pdf).decode(),'transform':transform}
    elif operation=='ifc_stairs':
        from .native_qa import _represented_stairs
        result=_represented_stairs(request['scoped'],request['model_doc'],path)
    elif operation=='ifc_rooms':
        from .native_qa import _ifc_model,_room_quantity
        model=_ifc_model(path)
        result=[_room_quantity(obj,request['key'],model) for obj in request['objects']]
    elif operation=='legacy_render':
        from .extraction import render_page
        result={'png':base64.b64encode(render_page(path,request['page'],request['scale'])).decode()}
    else:raise ValueError('Unsupported native operation')
    print(json.dumps({'ok':True,'result':result},allow_nan=False))
if __name__=='__main__':
    try:main()
    except Exception:
        print(json.dumps({'ok':False}));sys.exit(1)

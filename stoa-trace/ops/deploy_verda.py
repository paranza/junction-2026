#!/usr/bin/env python3
"""Deploy the Stoa workspace to one small Verda CPU VM.

Documented API: https://api.verda.com/v1/docs
All mutations have zero automatic retries. Deployment state holds resource IDs
and SSH paths only; cloud credentials never go to the application server.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib import request, error

from check_connections import DEFAULT_ENV, HealthError, create_ssl_context, load_config, load_runtime_config, request_json

ROOT=Path(__file__).resolve().parent.parent
CONFIG=Path.home()/'.config/stoa-junction-2026'
STATE=CONFIG/'verda-deployment.json'
ACCESS=CONFIG/'access.env'
API='https://api.verda.com/v1'
PREVIEW='https://fwjydgxpttajiqpfmqtj.supabase.co/storage/v1/object/public/stoa-junction-2026/junction-dataset-preview.zip'


def save(state):
    CONFIG.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd=os.open(STATE,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(state,stream,indent=2)


def read_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def client():
    config=load_config(DEFAULT_ENV)
    context=create_ssl_context()
    auth=request_json(API+'/oauth2/token',method='POST',payload={
        'grant_type':'client_credentials','client_id':config['VERDA_CLIENT_ID'],
        'client_secret':config['VERDA_CLIENT_SECRET']},ssl_context=context,retries=0)
    headers={'Authorization':'Bearer '+auth['access_token']}
    def call(path,method='GET',payload=None):
        return request_json(API+path,method=method,headers=headers,payload=payload,
                            ssl_context=context,retries=1 if method=='GET' else 0,timeout=30)
    return call,config


def public_instance(instance):
    # API responses can include Jupyter tokens. Never print/store entire bodies.
    return {k:instance.get(k) for k in ('id','ip','status','hostname','instance_type','location','price_per_hour','os_volume_id','volume_ids')}


def status(call,state):
    if not state.get('instance_id'):return {'status':'not_created'}
    obj=call('/instances/'+state['instance_id'])
    result=public_instance(obj)
    state.update({k:v for k,v in result.items() if v is not None})
    save(state)
    return result


def create(call,state,args):
    if state.get('instance_id'):
        raise RuntimeError('A managed VM already exists; use status or sync instead.')
    kind='CPU-TURIN.4V.16G'
    types=call('/instance-types?currency=eur')
    chosen=next(x for x in types if x['instance_type']==kind)
    available=call('/instance-availability')
    if not any(x['location_code']=='FIN-03' and kind in x['availabilities'] for x in available):
        raise RuntimeError('The reviewed CPU configuration has no FIN-03 capacity; no VM created.')
    images=call('/images')
    if not any(x.get('image_type')=='24.04.base' for x in images):
        raise RuntimeError('The reviewed Ubuntu image is unavailable; no VM created.')
    balance=call('/balance')
    if balance.get('amount',0)<5:
        raise RuntimeError('Project balance below the five-euro deployment reserve; no VM created.')
    CONFIG.mkdir(mode=0o700,parents=True,exist_ok=True)
    key=Path(state['ssh_key_path']) if state.get('ssh_key_path') else CONFIG/('verda-ssh-'+secrets.token_hex(5))
    if not key.exists():
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-C','stoa-junction-deployment','-f',str(key)],check=True)
    os.chmod(key,0o600)
    hostname=state.get('hostname') or 'stoa-junction-'+secrets.token_hex(3)
    state.update(ssh_key_path=str(key),hostname=hostname,created_at=time.time(),
                 intended_instance_type=kind,location='FIN-03',image='24.04.base',os_volume_gb=55)
    save(state)
    keys=call('/ssh-keys')
    registered=[item for item in keys if item.get('name')==hostname]
    ssh_id=registered[0]['id'] if len(registered)==1 else state.get('ssh_key_id')
    if not ssh_id:
        try:
            ssh_id=call('/ssh-keys','POST',{'name':hostname,'key':key.with_suffix('.pub').read_text().strip()})
            if isinstance(ssh_id,dict):ssh_id=ssh_id.get('id')
        except HealthError:
            # Some API mutations return a raw UUID despite their JSON docs.
            # Recover by unique name, never repeat the mutation blindly.
            found=[item for item in call('/ssh-keys') if item.get('name')==hostname]
            if len(found)!=1:raise
            ssh_id=found[0]['id']
    state['ssh_key_id']=ssh_id;save(state)
    # If this POST times out, do not blindly repeat: inspect the Console/list by
    # the unique hostname before retrying, to avoid duplicate paid resources.
    existing=[item for item in call('/instances') if item.get('hostname')==hostname]
    if existing:
        if len(existing)!=1:raise RuntimeError('Multiple matching instances; inspect Console.')
        state['instance_id']=existing[0]['id'];save(state)
        return {'status':'recovered_existing_instance','instance_id':state['instance_id']}
    payload={
        'hostname':hostname,'description':'Stoa Junction drawing workspace; CPU only',
        'instance_type':kind,'image':'24.04.base','location_code':'FIN-03',
        'contract':'PAY_AS_YOU_GO','is_spot':False,'ssh_key_ids':[ssh_id],
        'os_volume':{'name':hostname+'-os','size':55},
        'tags':[{'key':'project','value':'stoa-junction-2026'}]}
    try:
        response=call('/instances','POST',payload)
    except HealthError:
        found=[item for item in call('/instances') if item.get('hostname')==hostname]
        if len(found)!=1:raise
        response=found[0]
    instance_id=response.get('id') if isinstance(response,dict) else response
    if not isinstance(instance_id,str):raise RuntimeError('Unexpected deployment response; inspect Console by hostname.')
    state['instance_id']=instance_id;save(state)
    return {'status':'created','instance_id':instance_id,'hostname':hostname,
            'compute_eur_per_hour':chosen['price_per_hour'],'disk_gb':55}


def ssh_args(state):
    ip=str(ipaddress.ip_address(state['ip']))
    return ['ssh','-i',state['ssh_key_path'],'-o','IdentitiesOnly=yes',
            '-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new',
            '-o','ConnectTimeout=10','root@'+ip]


def run_remote(state,script,*,input_bytes=None,timeout=1800):
    command=ssh_args(state)+[script]
    result=subprocess.run(command,input=input_bytes,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if result.returncode:
        # Remote install logs contain no credentials, but do not echo arbitrary
        # output in case a dependency or shell ever emits environment details.
        raise RuntimeError('Remote command failed (exit '+str(result.returncode)+'). Check host logs over SSH.')
    return result.stdout


def runtime_environment(config):
    """Build a provider-specific env file; callers send it over encrypted stdin."""
    provider = config.get('STOA_PROVIDER', 'openai').strip().lower()
    if provider not in {'openai', 'gemini'}:
        raise ValueError('STOA_PROVIDER must be openai or gemini.')
    key_name = 'GEMINI_API_KEY' if provider == 'gemini' else 'OPENAI_API_KEY'
    key = config.get(key_name) or (config.get('GOOGLE_API_KEY', '') if provider == 'gemini' else '')
    if not key or any(c in key for c in '\r\n'):
        raise ValueError('A valid one-line provider runtime key is required.')
    values = {key_name: key, 'STOA_PROVIDER': provider,
              'STOA_MODEL': config.get('STOA_MODEL') or ('gemini-4-carbon' if provider == 'gemini' else 'gpt-6-astra'),
              'STOA_MAX_MODEL_CALLS': config.get('STOA_MAX_MODEL_CALLS', '50')}
    if int(values['STOA_MAX_MODEL_CALLS']) < 0:
        raise ValueError('STOA_MAX_MODEL_CALLS must be nonnegative.')
    for name in ('STOA_INPUT_USD_PER_MILLION', 'STOA_CACHED_INPUT_USD_PER_MILLION',
                 'STOA_OUTPUT_USD_PER_MILLION', 'STOA_SMALL_IMAGE_CROPS'):
        if name in config:
            values[name] = config[name]
    if any(any(c in str(value) for c in '\r\n') for value in values.values()):
        raise ValueError('Runtime settings must use one line per value.')
    return ''.join(name + '=' + str(value) + '\n' for name, value in values.items()).encode()


def sync(state,config):
    env = runtime_environment(config)
    with tempfile.TemporaryDirectory() as folder:
        archive=Path(folder)/'stoa-source.tar.gz'
        with tarfile.open(archive,'w:gz') as bundle:
            for name in ('server','frontend','Dockerfile','requirements.txt','.dockerignore'):
                path=ROOT/name
                if path.is_file():bundle.add(path,arcname=name)
                elif path.is_dir():
                    for item in path.rglob('*'):
                        if item.is_file() and not any(part in ('node_modules','dist','__pycache__') for part in item.parts):
                            bundle.add(item,arcname=str(item.relative_to(ROOT)))
        run_remote(state,'mkdir -p /srv/stoa/app /srv/stoa/data && tar -xzf - -C /srv/stoa/app',input_bytes=archive.read_bytes(),timeout=300)
    # Transfer only the selected provider key through encrypted stdin. Never put
    # it in argv, shell expansion, archives, Docker build arguments or logs.
    run_remote(state,'umask 077; cat > /srv/stoa/runtime.env; chmod 600 /srv/stoa/runtime.env',input_bytes=env,timeout=30)
    return {'status':'source_and_runtime_configuration_uploaded'}


def bootstrap(state):
    script='''set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq docker.io caddy curl python3 >/var/log/stoa-packages.log 2>&1
systemctl enable --now docker
mkdir -p /srv/stoa/data
'''
    run_remote(state,'bash -s',input_bytes=script.encode(),timeout=600)
    # Download public challenge data server-side. Validate archive paths first.
    data_script='''import pathlib,urllib.request,zipfile
root=pathlib.Path('/srv/stoa/data')
target=root/'junction-dataset-preview'
if not (target/'data').is_dir():
 archive=root/'preview.zip'
 urllib.request.urlretrieve(URL,archive)
 with zipfile.ZipFile(archive) as z:
  for item in z.infolist():
   if not (root/item.filename).resolve().is_relative_to(root.resolve()):raise ValueError('Unsafe archive member')
  z.extractall(root)
 archive.unlink()
 if not (target/'data').is_dir():
  if (root/'data').is_dir():
   target.mkdir(exist_ok=True)
   (root/'data').rename(target/'data')
  else:raise ValueError('Dataset layout unavailable')
'''.replace('URL',repr(PREVIEW))
    run_remote(state,'python3 -',input_bytes=data_script.encode(),timeout=600)
    return {'status':'docker_and_public_dataset_ready'}


def start(state):
    script='''set -eu
cd /srv/stoa/app
docker build -t stoa-junction:latest . >/var/log/stoa-build.log 2>&1
docker rm -f stoa-junction >/dev/null 2>&1 || true
docker run -d --name stoa-junction --restart unless-stopped --env-file /srv/stoa/runtime.env -v /srv/stoa/data:/data -p 127.0.0.1:8000:8000 stoa-junction:latest >/dev/null
'''
    run_remote(state,'bash -s',input_bytes=script.encode(),timeout=1800)
    return {'status':'started','url':state.get('url'),'origin_exposure':'localhost_only'}


def protect(state):
    ip=str(ipaddress.ip_address(state['ip']))
    hostname='stoa-'+ip.replace('.','-')+'.sslip.io'
    username='junction'
    if ACCESS.exists():
        values=dict(line.split('=',1) for line in ACCESS.read_text().splitlines() if '=' in line)
        password=values['STOA_ACCESS_PASSWORD']
    else:
        password=secrets.token_urlsafe(24)
        fd=os.open(ACCESS,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:
            stream.write('STOA_ACCESS_USERNAME='+username+'\nSTOA_ACCESS_PASSWORD='+password+'\n')
    hashed=run_remote(state,'caddy hash-password',input_bytes=(password+'\n').encode(),timeout=30).decode().strip()
    if not hashed.startswith('$2'):
        raise RuntimeError('Caddy did not return a bcrypt hash.')
    content=(hostname+' {\n encode gzip\n basicauth {\n '+username+' '+hashed+
             '\n }\n reverse_proxy 127.0.0.1:8000\n}\n')
    run_remote(state,'cat > /etc/caddy/Caddyfile && chown root:caddy /etc/caddy/Caddyfile && chmod 640 /etc/caddy/Caddyfile',input_bytes=content.encode(),timeout=30)
    run_remote(state,'caddy validate --config /etc/caddy/Caddyfile >/var/log/stoa-caddy-validation.log 2>&1 && systemctl enable --now caddy && systemctl restart caddy',timeout=60)
    state['url']='https://'+hostname;state['access_credentials_file']=str(ACCESS);save(state)
    return {'status':'https_and_basic_auth_configured','url':state['url'],
            'username':username,'credentials_file':str(ACCESS)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('inspect','create','status','sync','bootstrap','protect','start'))
    args=parser.parse_args()
    try:
        state=read_state()
        if args.action in ('inspect','create','status'):
            call,config=client()
        else:
            # Existing SSH access survives expiry of the short-lived Cloud
            # credential. Code updates/restarts need no Cloud API token.
            config=load_runtime_config() if args.action=='sync' else {}
        if args.action=='create':result=create(call,state,args)
        elif args.action=='inspect':result={'balance':call('/balance'),'managed_instance':status(call,state)}
        elif args.action=='status':result=status(call,state)
        elif args.action=='sync':result=sync(state,config)
        elif args.action=='bootstrap':result=bootstrap(state)
        elif args.action=='protect':result=protect(state)
        else:result=start(state)
        print(json.dumps(result,sort_keys=True))
        return 0
    except HealthError as exc:
        print(json.dumps({'status':'error','code':exc.code,'http_status':exc.http_status}));return 1
    except Exception as exc:
        # Do not render arbitrary exceptions or subprocess output containing
        # protected environment material.
        print(json.dumps({'status':'error','code':type(exc).__name__}));return 1


if __name__=='__main__':sys.exit(main())

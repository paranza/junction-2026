"""Fetch selected external annotations with HTTP ranges, CRC checks and backoff.

This downloads neither Junction labels nor the full 5.5 GB archive. All preview
image identifiers are excluded before any annotation or source image is opened.
"""
import argparse
import binascii
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import struct
import threading
import time
import zipfile
import zlib

import requests

URL = 'https://zenodo.org/records/2613548/files/cubicasa5k.zip'
ARCHIVE_SIZE = 5469495706
ARCHIVE_MD5 = '0ce0b203d1e3c125b51087b219bd23b9'
SEED = 'metria-external-symbols-v1'


class RangeFile(io.RawIOBase):
    def __init__(self): self.position = 0
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position+offset if whence == 1 else ARCHIVE_SIZE+offset
        return self.position
    def read(self, size=-1):
        end = min(ARCHIVE_SIZE, self.position+size if size >= 0 else ARCHIVE_SIZE)-1
        if end < self.position: return b''
        result = requests.get(URL, headers={'Range':f'bytes={self.position}-{end}'}, timeout=90)
        result.raise_for_status()
        if result.status_code != 206 or len(result.content) != end-self.position+1:
            raise ValueError('Dataset server did not return the exact requested byte range')
        self.position = end+1
        return result.content


def choose(folders, excluded, count):
    available = [f.strip('/') for f in folders if f.strip('/') not in excluded]
    available.sort(key=lambda value: hashlib.sha256((SEED+':'+value).encode()).hexdigest())
    for name in available:
        if '..' in PurePosixPath(name).parts or PurePosixPath(name).is_absolute():
            raise ValueError('Unsafe dataset path')
    if len(available) < count: raise ValueError('Not enough non-preview samples')
    return available[:count]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', type=Path, required=True, help='CubiCasa image directory; filenames only are read')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--index-cache', type=Path, required=True)
    parser.add_argument('--split-prefix', type=Path, help='Optional already downloaded split files PREFIX-train.txt, -val.txt, -test.txt')
    parser.add_argument('--train', type=int, default=256)
    parser.add_argument('--validation', type=int, default=64)
    parser.add_argument('--confirmation', type=int, default=16)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    excluded = {p.stem.rsplit('-',1)[0]+'/'+p.stem.rsplit('-',1)[1] for p in args.preview.iterdir()
                if p.is_file() and p.suffix.lower() in {'.png','.jpg','.jpeg'} and '-' in p.stem}
    if args.index_cache.exists():
        index = json.loads(args.index_cache.read_text())
    else:
        with zipfile.ZipFile(RangeFile()) as archive:
            index = {i.filename:{'offset':i.header_offset,'size':i.compress_size,'raw_size':i.file_size,
                                  'crc':i.CRC,'compress_type':i.compress_type} for i in archive.infolist()}
        args.index_cache.write_text(json.dumps(index))
    splits = {}
    for split in ('train','val','test'):
        cached = Path(str(args.split_prefix)+'-'+split+'.txt') if args.split_prefix else None
        if cached and cached.exists(): value = cached.read_text()
        else:
            with zipfile.ZipFile(RangeFile()) as archive: value = archive.read('cubicasa5k/'+split+'.txt').decode()
        splits[split] = value.splitlines()
    selection = {'schema':'external-symbol-training-v2','source':URL,'archive_md5_expected':ARCHIVE_MD5,
                 'license':'CC-BY-NC-4.0','excluded_junction_preview_images':len(excluded),'selection_seed':SEED,
                 'train':choose(splits['train'],excluded,args.train),
                 'validation':choose(splits['val'],excluded,args.validation),
                 'confirmation':choose(splits['test'],excluded,args.confirmation)}
    assert not set(selection['train'])&set(selection['validation'])
    assert not (set(selection['train'])|set(selection['validation']))&set(selection['confirmation'])
    target = args.output/'selection.json'
    if target.exists():
        previous = json.loads(target.read_text())
        if previous['train'] != selection['train'] or previous['validation'] != selection['validation']:
            raise ValueError('Existing selection differs; choose a fresh output directory')
    target.write_text(json.dumps(selection,indent=2))
    rate_lock = threading.Lock(); next_request = [0.]; progress_lock = threading.Lock(); done = [0]

    def request(start,end):
        for attempt in range(8):
            with rate_lock:
                time.sleep(max(0,next_request[0]-time.monotonic()))
                next_request[0] = time.monotonic()+1.5
            response = requests.get(URL,headers={'Range':f'bytes={start}-{end}'},timeout=90)
            if response.status_code == 429:
                raw = response.headers.get('Retry-After','60')
                delay = max(60,int(raw)) if raw.isdigit() else 60
                with rate_lock: next_request[0] = max(next_request[0],time.monotonic()+delay)
                print(json.dumps({'rate_limited':True,'backoff_seconds':delay}),flush=True)
                continue
            response.raise_for_status()
            if response.status_code != 206 or len(response.content) != end-start+1:
                raise ValueError('Invalid dataset byte range')
            return response.content
        raise RuntimeError('Dataset server is rate limiting; resume the same selection later')

    def valid(path,meta):
        if not path.exists(): return False
        value = path.read_bytes()
        return len(value)==meta['raw_size'] and binascii.crc32(value)&0xffffffff==meta['crc']

    def acquire(folder):
        names = [folder+'/F1_scaled.png',folder+'/model.svg']
        missing = [name for name in names if not valid(args.output/name,index['cubicasa5k/'+name])]
        if missing:
            entries = [index['cubicasa5k/'+name] for name in missing]
            start = min(e['offset'] for e in entries)
            end = max(e['offset']+30+len(('cubicasa5k/'+name).encode())+e['size']+8192 for name,e in zip(missing,entries))
            raw = request(start,end)
            for name,meta in zip(missing,entries):
                offset = meta['offset']-start
                header = struct.unpack('<IHHHHHIIIHH',raw[offset:offset+30])
                if header[0] != 0x04034b50: raise ValueError('Invalid ZIP local header')
                begin = offset+30+header[-2]+header[-1]
                compressed = raw[begin:begin+meta['size']]
                value = zlib.decompress(compressed,-15) if meta['compress_type']==8 else compressed
                if len(value)!=meta['raw_size'] or binascii.crc32(value)&0xffffffff!=meta['crc']:
                    raise ValueError('Dataset member integrity check failed')
                path = args.output/name; path.parent.mkdir(parents=True,exist_ok=True)
                temporary = path.with_suffix(path.suffix+'.part'); temporary.write_bytes(value); os.replace(temporary,path)
        with progress_lock:
            done[0] += 1
            if done[0]%16==0: print(json.dumps({'samples_ready':done[0]}),flush=True)

    folders = selection['validation']+selection['confirmation']+selection['train']
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: list(pool.map(acquire,folders))
    hashes = {name:hashlib.sha256((args.output/name).read_bytes()).hexdigest() for folder in folders
              for name in (folder+'/F1_scaled.png',folder+'/model.svg')}
    (args.output/'source-hashes.json').write_text(json.dumps(hashes,indent=2))
    (args.output/'READY').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'\n')
    print(json.dumps({'status':'ready','train':args.train,'validation':args.validation,'confirmation':args.confirmation}),flush=True)


if __name__=='__main__': main()

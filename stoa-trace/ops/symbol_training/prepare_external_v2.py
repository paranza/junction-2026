"""Freeze a larger external split, then extract only selected members of a verified ZIP."""
import argparse,binascii,hashlib,json,os,zipfile
from pathlib import Path
SEED='metria-external-symbols-v2'
EXPECTED_MD5='0ce0b203d1e3c125b51087b219bd23b9'
def choose(lines,excluded,count):
 values=sorted({line.strip('/') for line in lines if line.strip('/')} - excluded,key=lambda s:hashlib.sha256((SEED+':'+s).encode()).hexdigest())
 if len(values)<count:raise ValueError('Insufficient independent samples')
 return values[:count]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--preview',type=Path,required=True);p.add_argument('--previous-selection',type=Path,required=True);p.add_argument('--split-prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--archive',type=Path);a=p.parse_args()
 excluded={f.stem.rsplit('-',1)[0]+'/'+f.stem.rsplit('-',1)[1] for f in a.preview.iterdir() if f.is_file() and f.suffix.lower() in {'.png','.jpg','.jpeg'} and '-' in f.stem}
 previous=json.loads(a.previous_selection.read_text());released=set(previous['confirmation'])
 selection={'schema':'external-symbol-training-v3','source':'https://zenodo.org/records/2613548/files/cubicasa5k.zip','archive_md5_expected':EXPECTED_MD5,'license':'CC-BY-NC-4.0','selection_seed':SEED,'excluded_junction_preview_images':len(excluded),'excluded_released_confirmation':len(released)}
 for name,split,count in [('train','train',1024),('validation','val',128),('confirmation','test',32)]:
  selection[name]=choose(Path(str(a.split_prefix)+'-'+split+'.txt').read_text().splitlines(),excluded|(released if name=='confirmation' else set()),count)
 assert not set(selection['train'])&set(selection['validation'])
 assert not (set(selection['train'])|set(selection['validation'])|released)&set(selection['confirmation'])
 a.output.mkdir(parents=True,exist_ok=True);target=a.output/'selection.json'
 if target.exists() and json.loads(target.read_text())!=selection:raise ValueError('Selection is immutable')
 target.write_text(json.dumps(selection,indent=2))
 if not a.archive:
  print('Larger external selection frozen; source annotations remain unopened');return
 # The full archive is hashed before selected sources are opened. Individual
 # members are CRC-verified by ZipFile and assigned independent SHA256 hashes.
 digest=hashlib.md5()
 with a.archive.open('rb') as stream:
  for chunk in iter(lambda:stream.read(8*1024*1024),b''):digest.update(chunk)
 if digest.hexdigest()!=EXPECTED_MD5:raise ValueError('Publisher archive checksum mismatch')
 hashes={}
 with zipfile.ZipFile(a.archive) as archive:
  for folder in selection['train']+selection['validation']+selection['confirmation']:
   if '..' in Path(folder).parts or folder.startswith('/'):raise ValueError('Unsafe source member')
   for leaf in (['F1_scaled.png'] if folder in selection['confirmation'] else ['F1_scaled.png','model.svg']):
    name=folder+'/'+leaf;value=archive.read('cubicasa5k/'+name)
    path=a.output/name;path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix(path.suffix+'.part');temporary.write_bytes(value);os.replace(temporary,path)
    hashes[name]=hashlib.sha256(value).hexdigest()
 (a.output/'source-hashes.json').write_text(json.dumps(hashes,indent=2));(a.output/'READY').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'\n')
 print(json.dumps({'train':1024,'validation':128,'fresh_confirmation':32,'junction_preview_excluded':len(excluded),'archive_verified':True}))
if __name__=='__main__':main()

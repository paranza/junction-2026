"""Export a frozen external-validation checkpoint; no training/test labels needed."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import torch

sys.path.insert(0,str(Path(__file__).resolve().parent))
from model import SymbolNet, ExportNet


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):raise ValueError('Use a fresh export directory')
    checkpoint=torch.load(args.checkpoint,map_location='cpu',weights_only=True)
    if 'validation' not in checkpoint:raise ValueError('Checkpoint has no external validation record')
    network=SymbolNet();network.load_state_dict(checkpoint['model_state']);network.eval()
    export=ExportNet(network).eval()
    args.output.mkdir(parents=True,exist_ok=True)
    path=args.output/'symbolnet.onnx'
    image=torch.zeros((1,1,320,320))
    torch.onnx.export(export,image,str(path),input_names=['image'],output_names=['centers','extent_pixels'],
                      opset_version=18,dynamo=False)
    model_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest={'kind':'symbol_centers','name':'Metria SymbolNet external v3','model_file':path.name,'model_sha256':model_sha,
              'classes':['door','window'],'threshold':checkpoint['validation']['threshold'],'input_size':320,
              'core_size':192,'maximum_edge':1200,'nms_kernel':5,'extent_unit':'input_pixels',
              'checkpoint_sha256':hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
              'training':{'pretrained':False,'source':'https://zenodo.org/records/2613548',
                          'source_license':'CC-BY-NC-4.0','train_images':256,'validation_images':64,
                          'selection_sha256':checkpoint['configuration']['selection_sha256'],
                          'source_code_sha256':checkpoint['configuration']['source_code_sha256'],
                          'step':checkpoint['step'],'validation':checkpoint['validation'],
                          'junction_preview_excluded':True,'confirmation_used_for_selection':False},
              'calibrated':False,'limitations':'Visual candidates, not verified source quantities or measured physical extents.'}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Independent runtime parity is checked by the caller from these vectors.
    generator=torch.Generator().manual_seed(731)
    inputs=torch.rand((3,1,320,320),generator=generator)
    with torch.inference_mode():outputs=[export(row[None]) for row in inputs]
    np.savez_compressed(args.output/'parity-inputs.npz',inputs=inputs.numpy(),
                        centers=np.concatenate([o[0].numpy() for o in outputs]),
                        extent_pixels=np.concatenate([o[1].numpy() for o in outputs]))
    print(json.dumps({'model_sha256':model_sha,'threshold':manifest['threshold'],'checkpoint_step':checkpoint['step']}))


if __name__=='__main__':main()

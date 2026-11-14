"""Export our own checkpoint safely. PyTorch is a build dependency, not a runtime."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    import numpy as np
    import torch
    from plannet_definition import PlanNet
    # The team checkpoint contains NumPy numeric metrics as well as tensor weights.
    # Permit only those known numeric constructors, never arbitrary pickle globals.
    with torch.serialization.safe_globals([np._core.multiarray.scalar,np.dtype,np.dtypes.Float64DType,np.dtypes.Float32DType]):
        checkpoint=torch.load(args.checkpoint,map_location='cpu',weights_only=True)
    model=PlanNet(len(checkpoint['seg_channels']),len(checkpoint['obj_classes']))
    model.load_state_dict(checkpoint['model'])
    model.eval()
    class Heat(torch.nn.Module):
        def __init__(self):
            super().__init__();self.network=model
        def forward(self,x):
            return torch.sigmoid(self.network(x)[1])
    args.output.mkdir(parents=True,exist_ok=True)
    target=args.output/'plannet-swiss.onnx'
    if target.exists():raise SystemExit('Refusing to overwrite an existing model export.')
    torch.set_num_threads(2)
    torch.onnx.export(Heat().eval(),torch.zeros(1,1,640,640),target,input_names=['ink'],
                      output_names=['heat'],opset_version=17,dynamo=False)
    manifest={'kind':'plannet_heatmap','name':'Team PlanNet Swiss','model_file':target.name,
              'model_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
              'checkpoint_sha256':hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
              'classes':checkpoint['obj_classes'],'threshold':.35,'training_domain':'Swiss Dwellings drawing style',
              'training_note':'Earlier team model, 56 Swiss sheets with DXF-derived labels. Not a general drawing detector. No retraining in this upgrade.',
              'attribution':'Swiss Dwellings v3.0.0, Matthias Standfest and co-authors, Archilyse AG, CC BY 4.0, doi:10.5281/zenodo.7788422',
              'architecture':'MUSTA HELMI PlanNet, MIT','runtime':'onnxruntime CPU'}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'model_sha256':manifest['model_sha256'],'classes':manifest['classes'],'bytes':target.stat().st_size}))


if __name__=='__main__':main()

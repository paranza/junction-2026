# External symbol detector research

This is a separate training environment, not the application runtime. No answer
lookup, Junction reference answer, or Junction image is used for training.
Do not enable a checkpoint merely because training completed.

## Data boundary

`acquire.py` selects 256 train, 64 validation and 16 confirmation drawings from
the publisher's respective CubiCasa5K splits using a fixed SHA256 ranking. It
excludes all 241 Junction CubiCasa preview image identifiers first. Confirmation
annotations are not opened by training or threshold selection. A label-free
Gemini baseline can read those images before freezing, but cannot score them.

Source: [CubiCasa5K archive](https://zenodo.org/records/2613548).
License: CC-BY-NC 4.0. Retain attribution and the noncommercial limitation.
Images, annotation files, checkpoints and reference-bearing reports stay in a
private external directory. No training assets are bundled in the repository.
Range downloads verify ZIP entry CRCs and record individual SHA256 hashes.
They do not establish the MD5 of the complete 5.5 GB archive. The larger v2
preparation verifies the complete archive against the publisher's MD5 before
extracting selected members.

Polygon coordinates in `model.svg` are F1_scaled raster pixels, following the
publisher's loader. The SVG viewBox may differ and must not rescale labels.
`test_data.py` covers that case and checks that confirmation files are excluded
from the YOLO export.

## Reproduce

Use Python 3.12 on an NVIDIA host for transfer learning. On a V100, install the
CUDA 11.8 wheels for Torch 2.7.1 and torchvision 0.22.1 first, then
`requirements-symbol-yolo-training.txt`. Ultralytics and its pretrained weights
have their own AGPL-3.0 licensing terms. No third-party implementation or weights
are relicensed by this repository.

From `stoa-trace`, in a separate training environment:

```sh
python ops/symbol_training/acquire.py --preview /path/to/preview/data/cubicasa5k \
  --output /path/to/external-symbols --index-cache /path/to/private-index.json
python -m unittest discover -s ops/symbol_training -p 'test_*.py'
python ops/symbol_training/prepare_yolo.py --data /path/to/external-symbols \
  --output /path/to/export --runtime-root /srv/metria-training/data
```

Upload the exported train/validation data only to the temporary training host.
Place it at `/srv/metria-training/data` and run:

```sh
python ops/symbol_training/train_yolo.py --root /srv/metria-training
python ops/symbol_training/validate_yolo.py \
  --root /srv/metria-training/data \
  --weights /srv/metria-training/runs/yolo11s-external-v1/weights/best.pt \
  --output /srv/metria-training/validation-frozen.json
```

The frozen YOLO11s experiment uses 60 epochs, 1024-pixel input, batch 4 and seed
8127. Checkpoint selection uses external validation mAP; class confidence
thresholds use validation exact counts, then absolute count error. Freeze the
weights, preprocessing, thresholds and integration policy before opening the 16
confirmation annotations. Report exact counts separately from object IoU
precision/recall. Compare Gemini and the combined pipeline on identical images.
A small external sample is not an arbitrary-blueprint accuracy guarantee.

The first transfer-learning run achieved 52/128 exact validation category
counts. On 16 external confirmation drawings, Gemini alone got 14/32 exact
counts and detector-guided review got 15/32, with one gain and no regression.
It remains disabled. Grayscale training exports and RGB integration also made
that first pipeline's preprocessing inconsistent, so these results do not
validate a matched deployment.

## Larger v2 experiment

`prepare_external_v2.py` selects 1,024 training, 128 validation and 32 fresh
confirmation images from the respective official splits. All 241 Junction IDs
are excluded, and the released v1 confirmation drawings cannot enter the new
confirmation set. Pass the verified archive, official split prefix, previous
selection and an empty private output directory. Confirmation image members
are extracted without their SVG annotations.

Export train/validation with `prepare_yolo.py --rgb`. Run `train_yolo.py
--experiment v2`: pretrained YOLO11s, 1,280-pixel input, batch 8, seed 8127,
AdamW, no mosaic. `time=1.2` hours bounds training and takes precedence over the
initial 80-epoch estimate; Ultralytics adapts the epoch estimate. Record the
actual completed epochs and elapsed allocation time.

`calibrate_runtime.py` uses the frozen application decoder and its exact RGB,
PIL letterbox and suppression rules. It compares whole-page and overlapping
tile inference on external validation only. It selects confidence thresholds
by exact count, then absolute count error, and selects the mode by the same
criterion. Export the selected weights to static float32 ONNX, pin the model
and runtime hashes, and check a real validation input against ONNX Runtime.

Freeze weights, preprocessing, thresholds and the integration prompt before
opening any of the fresh 32 confirmation annotations. Compare the same images
with Gemini alone and with detector-guided review, counting failures and both
gains and regressions. Training mAP does not establish exact count accuracy.
The scripts do not enable a model in the application.

`model.py`, `data.py`, `train.py` and `export.py` retain an earlier from-scratch
center detector experiment. Its first valid 4,000-step run got only 6/128 exact
external validation category counts and was rejected. Earlier runs with incorrect
viewBox scaling or incomplete acquisition are invalid diagnostics. They are not
production accuracy measurements. The app does not load these checkpoints.

## Verda execution

Use an isolated training resource, never the protected application VM. The live
14 November experiment used `1V100.4V`, FIN-01, spot, with a quoted compute rate
of EUR 0.1088/hour and a two-hour local cleanup deadline. Spot can be interrupted.
The local controller keeps cloud credentials local, downloads artifacts, and
removes the training instance and its disk. Shutdown alone does not stop billing.
A controller watchdog is not a provider-enforced billing cap. Record elapsed
allocation time and cleanup verification. Do not publish credentials or copy
them to the training host.

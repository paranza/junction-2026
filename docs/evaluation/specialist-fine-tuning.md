# Pretrained symbol detector fine tuning

The experiment adapts pretrained YOLO11s to doors and windows. It does not
fine-tune Gemini or train a model from random initialization. The application
continues using its configured native extraction and Gemini policy.

## Training and boundary

The larger experiment used 1,024 external CubiCasa training drawings and 128
validation drawings. All 241 Junction preview image IDs were excluded. Another
32 external test drawings were selected prospectively, excluding the released
v1 confirmation cases. Their annotations remained closed until weights,
preprocessing, thresholds, prompts and all comparison predictions were frozen.
No Junction reference answer entered training or inference.

Training ran on a temporary Verda V100 with 1,280-pixel RGB input, batch 8,
AdamW and fixed seed 8127. It stopped after 130 epochs under the configured
early-stopping/time rules. Whole-page inference beat overlapping tiles on the
external validation exact-count criterion: 119/256 versus 112/256 category
counts. Door/window confidence thresholds were 0.4/0.3, selected on validation
only. ONNX export passed a real-input parity check against the trained model.

## Frozen external confirmation

Each of the 32 drawings contributes one door count and one window count.
Counts require exact equality with the publisher's visible-source annotations.
These are generic whole-visible-page inputs, a different selection and policy
from the Junction preview benchmark.

| Pipeline | Exact counts | Percentage |
|---|---:|---:|
| Gemini Argon inventory, two readings | 28/64 | 43.75% |
| Same inventory plus a blind Gemini review | 27/64 | 42.19% |
| Fine-tuned detector alone | 25/64 | 39.06% |
| Inventory plus detector-guided Gemini review | 29/64 | 45.31% |

The combined pipeline gained two previously wrong counts and lost one
previously correct count. It failed the predeclared promotion criterion of at
least four gains and no regressions. The matched blind-review control used the
same model, prompt, schema, images and prior visual candidates, with an empty
specialist proposal list. It was frozen before opening any reference values.
The small difference does not establish a reliable detector advantage.

**Decision: keep the detector and guided-review prototype disabled.** The
experiment does not justify replacing the default reader or changing the
explicit production Carbon policy. The first smaller experiment was also
rejected: 15/32 combined exact counts versus 14/32 for Gemini, and inconsistent
grayscale/RGB preprocessing limited that earlier pipeline's interpretation.

All comparison requests completed without provider errors: 64 baseline readings,
32 guided reviews and 32 matched controls, 128 actual model attempts. The
baseline/guided and control runtimes retained their separate 96/32 ceilings and
cumulative ledgers. No production model request was made for verification.

The GPU and its disk were removed after private artifact retrieval. The existing
protected application VM remained running. Allocation compute is estimated at
EUR 0.1202, excluding disk charges and billing rounding. Weights, images,
annotations and raw reference-bearing results remain private. The aggregate
record includes hashes, exact counts, IoU metrics, policy and cleanup evidence.
Retain CubiCasa's CC-BY-NC-4.0 and Ultralytics' AGPL-3.0 notices.

The local orchestration reconciled two environment issues without replaying
paid requests: the app Python lacks the newer tar extraction filter argument,
and intentionally has no Torch. Existing downloaded artifacts were extracted
after regular-file/path validation; scoring used the separate training Python.
Neither issue changed the candidate or opened reference labels early.

These confirmation labels are now released. They must not be tuned on and later
reported as a fresh independent set. Detection mAP, exact counts and general
question-answer accuracy are separate measurements.

[Aggregate evidence](../../stoa-trace/ops/reports/specialist-symbols/external-v2-summary.json),
[training tools and reproduction](../../stoa-trace/ops/symbol_training/README.md),
[separate Carbon development evaluation](development-auto-190e116.md).

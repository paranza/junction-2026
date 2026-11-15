# Evaluation scoreboard and prospective reservation

The full native baseline at `d6f5b0c` reproduced the Saturday plan's measured result: **1,682/7,990 answered**, with **1,598/7,725 numeric questions correct**. Among answered numeric questions, **1,598/1,679 were correct (95.2%)**. Three of 265 text questions were answered and require human review. Zero model calls were made. See the [compact measured report](../../stoa-trace/ops/reports/riccardo-delivery/native-full-baseline-summary.md) and [code/config hashes](../../stoa-trace/ops/reports/riccardo-delivery/native-full-baseline-summary.json).

This is a preview development baseline. The team had already inspected this dataset, run full evaluations and tuned EDA rules on it. It is not a hidden-test result and cannot establish accuracy on an arbitrary new upload. Native-mode raster abstentions do not measure the hosted visual reader.

## What is frozen

[preview-reservation.json](preview-reservation.json) fixes **48 of 317 drawing groups (15.14%)**, containing **924 of 7,990 questions**. The remaining **269 groups / 7,066 questions** form the development set. The question fraction is lower than the group fraction because groups have different numbers of questions.

The original 50-case diagnostic and 100-case competitive evaluation contain 99 drawing groups. They remain development-only so rehearsals and regression work on already discussed examples do not break the new quarantine. From the remaining 218 eligible groups, a fixed seed selects 43 CubiCasa groups (736 questions) and five Swiss building groups (188 questions), using deterministic source allocation and SHA256 group ranking. Labels do not affect selection.

**There are no reserved IFC or Opening Design groups.** All their preview groups had already appeared in the focused diagnostic/evaluation. Do not claim this reservation measures those sources. It is also not a dataset-wide semantic duplicate audit; the shared grouping function keeps Swiss building floors, matching model/plan exports, project sheets and translations together, but differently named cross-source copies may require additional review.

The record is a **prospective quarantine from its freeze time**, not a retroactively untouched test set. Do not inspect reserved errors, score the reserved subset, or use it for model selection before **Sunday 15 November 2026**. During Saturday, compare changes on the development manifest. On Sunday, record the code/config hash, score the reserved set once at the agreed milestone, and report its limited coverage and prior exposure. Do not move difficult groups into development after seeing the score.

## Reproduce local manifests without publishing gold labels

Run commands from `stoa-trace/`, with the virtual environment's Python and a separately supplied preview directory. All gold-bearing manifests and raw reports belong in ignored `.local/` paths, never application extraction, prompts, retrieval, training or Git.

```sh
mkdir -p .local/evaluation
python -c 'import json; json.dump({"cases": []}, open(".local/evaluation/no-exclusions.json", "w"))'
python ops/grouped_manifest.py --dataset-root /path/to/preview \
  --exclude-manifest .local/evaluation/no-exclusions.json \
  --count 100000 --max-per-group 100000 --languages all \
  --output .local/evaluation/full.json
python ops/freeze_holdout.py --manifest .local/evaluation/full.json \
  --dataset-root /path/to/preview --output-dir .local/evaluation/frozen \
  --membership-input ../docs/evaluation/preview-reservation.json
```

The full manifest must retain case hash `29c623293443c52ae04e9f32d04dc00e15895496f54a9338388c6b079e1fcacd`. Restoration verifies the source-question hash, full-case hash, group membership and both split hashes. It refuses to replace existing frozen files. Choose a new local output directory for a restoration check; preserve the committed membership file.

For normal interim regression runs against an already running native backend:

```sh
python ops/benchmark.py --manifest .local/evaluation/frozen/development.json \
  --base-url http://127.0.0.1:8787 --dataset-root /path/to/preview \
  --mode native --max-questions 100000 \
  --output .local/evaluation/development-result.json
```

The full 7,990-question baseline was run **before** the freeze. The Saturday plan's instruction to rerun all preview questions on each PR conflicts with reserving cases from interim debugging. After the freeze, use the development set for PR comparisons and defer reserved scoring until Sunday. Record this boundary in review notes.

## Verification

Seven focused tests pass for group/translation isolation, answer-independent deterministic selection, protected diagnostic groups, no-gold public records, immutable outputs, restoration hashes and invalid reservations. Rebuilding local manifests from the committed membership reproduced all split hashes. The full native run had zero request errors and zero recorded model attempts in a new isolated runtime with an explicitly empty model key and a zero-call cap. The test server was separate from the team's running app and shared deployment.

Per-language reporting uses question-prefix hints, including Danish Hvad/Hvor and lowercase English how. These are deterministic metadata heuristics, not a trained language-recognition score. The detailed raw result is local; the committed report contains aggregate counts and hashes only.

## Post-change development regression

After the upload/measurement guards in `c78b0b7`, all **7,066 development questions** were re-run in native mode. Compared with exactly those case IDs from the pre-freeze full baseline, the result retained **1,517/6,801 correct numeric answers**, **1,592 answered questions**, and every source's correct-answer count. There were **zero changed case outcomes, zero previously correct regressions, zero request errors and zero model calls**. The API reported solver revision `41fffb967c844f4f2697`. This demonstrates native regression stability, not a measured improvement in arbitrary-upload or visual accuracy. [Paired development report](../../stoa-trace/ops/reports/riccardo-delivery/native-development-after-generalization-summary.md)

The reserved subset was not scored or inspected. The existing paired comparator verified identical question, source, expected label, unit, type and group identities for development cases. Raw case-level results remain in ignored local storage; the public JSON contains aggregates and provenance hashes only.

## Automatic pipeline coverage check, 14 November evening

The native regression does not measure the complete model-backed app. A targeted automatic-path run resolved 12 of 13 previously unanswered Opening Design PDF development questions correctly, while a four-crop symbol reader showed no gain on 22 development questions. The same run exposed incomplete-model scope being mistaken for a full IFC model; this is now refused before model inference. These targeted results are not a new overall accuracy estimate. See [the complete coverage, precision and limitation report](model-coverage-development.md).


## Sunday one-time preview reserve, 15 November

The frozen native application at `009801f` was evaluated once on the prospectively
quarantined 48 groups / 924 questions after the development gate passed. It
answered 188 questions, all correct numerically, and abstained on 736 raster
questions. There were zero technical errors or model requests. A blank key and
zero model-attempt ceiling were enforced. No reserved errors were used for
tuning, and the independent Gemini file evaluation was not repeated.

This preview had prior EDA/full-evaluation exposure before quarantine; it is not
an untouched hidden test. Its Swiss/CubiCasa source coverage excludes IFC and
Opening Design and does not establish performance on complex Discord plans or
the model-backed path. [Frozen revision, manifest/result hashes and limitations](../../stoa-trace/ops/reports/sunday-0700/preview-reserve.json).

# Frozen development evaluation

Frozen development evaluation of Trace native extraction, Gemini visual inventory, and opt-in Gemma count review. Aggregate-only; not an untouched final test or a competition accuracy estimate.

| Run | Numeric correct / all | Numeric answered | Answered precision | Errors / unrun |
| --- | ---: | ---: | ---: | ---: |
| Native | 2929/6801 (43.07%) | 3023 (44.45%) | 96.89% | 0 / 0 |
| Gemini raster raw | 2760/3534 (78.10%) | 3534 (100.00%) | 78.10% | 0 / 0 |
| Gemini raster unique | 1380/1767 (78.10%) | 1767 (100.00%) | 78.10% | 0 / 0 |
| Gemma paired originals | 24/68 (35.29%) | 68 (100.00%) | 35.29% | 0 / 0 |
| Gemma audited | 24/68 (35.29%) | 60 (88.24%) | 40.00% | 0 / 0 |

Raster: 198 drawings, 1767 unique normalized requests. 47/198 drawings had every available question correct. Drawing-macro mean question accuracy: 76.96%. Translated pairs are correlated.

## Raster categories

| Category | Raw correct / all | Unique correct / all |
| --- | ---: | ---: |
| balcony | 96/114 (84.21%) | 48/57 (84.21%) |
| bathroom | 154/188 (81.91%) | 77/94 (81.91%) |
| bedroom | 228/260 (87.69%) | 114/130 (87.69%) |
| door | 162/288 (56.25%) | 81/144 (56.25%) |
| floor | 386/396 (97.47%) | 193/198 (97.47%) |
| kitchen | 234/270 (86.67%) | 117/135 (86.67%) |
| sauna | 254/276 (92.03%) | 127/138 (92.03%) |
| shower+bathtub | 278/370 (75.14%) | 139/185 (75.14%) |
| sink | 292/392 (74.49%) | 146/196 (74.49%) |
| toilet | 332/394 (84.26%) | 166/197 (84.26%) |
| wc_room | 182/190 (95.79%) | 91/95 (95.79%) |
| window | 162/396 (40.91%) | 81/198 (40.91%) |

## Paired count review

Predeclared English-only door/window development sample across 40 drawing hashes; not a representative all-question distribution.
The frozen backend deep-copies original_detection from the same initial inventory before replacing the final value/evidence. Comparisons use that retained original, not the separately generated bulk inventory.

| Category | Original correct / all | Audited correct / all | Audit numeric answered | Audit answered precision |
| --- | ---: | ---: | ---: | ---: |
| door | 10/28 | 12/28 | 27 | 44.44% |
| window | 14/40 | 12/40 | 33 | 36.36% |

Transitions: incorrect -> correct: 3, incorrect -> incorrect: 35, correct -> correct: 21, correct -> unanswered: 2, incorrect -> unanswered: 6, correct -> incorrect: 1.

A different-model review is not independent verification. Provisional visual answers require review. One review was unavailable and retained its original count; this is distinct from HTTP/API failure.

## Usage and cost

Raster observed model calls: 198; input/output tokens: 492,638/1,402,447. Frozen-run cost was unconfigured. Reconstructed token estimate: $15.009746, using $2.0/million input and $10.0/million output tokens, dated 2026-11-14 ([pricing basis](https://aistudio.google.com/docs/pricing)). This is an estimate before credits, not an invoice. It excludes the separate audit run and initial failed HIGH-policy requests, whose usage is unknown.
Audit observed model calls: 108; input/output tokens: 296,133/339,350; reported total token cost estimate: unknown. Known cost subtotal: $3.172880; 1 review call has unknown usage/cost, so observed token counts omit that call. Model breakdown and dated rates are in the JSON.

The initial high-thinking, 14,000-output-token diagnostic failed with six HTTP 503 requests and 3,528 unrun questions. It was a completion/transport failure, not an accuracy experiment; provider attempts, tokens and cost remain unknown. The runner stopped and preserves those failed artifacts.

## Frozen identities

Raster application: `de9e4bc`; solver: `4730063ee850a4fc3014`; manifest: `f5b772de621f06dc8c7dc8d9d83f0e99ab56a6488d2867f0a377eb6f42accb07`; selected cases: `e2a882e795c9ffb415df3feb8246010cc125095c0368fa6ce7a53eb61f283f36`.
Raster provider policy: `gemini:gemini-4-carbon:gemini-interactions-v3:2026-05-20:image_resolution=high:thinking_level=medium:max_output_tokens=24000:timeout_seconds=600`; visual recount: `False`; inventory crops: `False`.
Audit application: `89cd4b8`; solver: `50c74a4792640241dd3d`; sample manifest: `382b491970aee3ac4074a2d61f5258dce9dc62f6abd89917c1bafffba7debd9f`; auditor: `gemma-4-31b-it`; visual recount: `True`.
Native declared backend: `b01af99`; recorded solver: `50c74a4792640241dd3d`; raw-report SHA-256: `dbbecd748cd47620b045d0d692c8cf72c3e5ae2924b5a26bef9d083d16f8df58`. Native backend commit is operator-declared, not embedded in the raw report.

## Limits

- These are development results on public preview data already used in development, not an untouched held-out assessment.
- Accuracy compares supplied dataset labels with answers. Dataset ambiguities or labeling errors were not independently adjudicated.
- The raster run covers count questions only. Its floor category means number of storeys/floors, not floor area; it does not validate calibrated raster areas or arbitrary question answering.
- Localization reference boxes are absent from this evaluation, so valid box syntax does not establish IoU, correct highlights, detection precision, recall or completeness.
- A different-model review is not independent ground truth. Both initial and audited visual counts remain provisional.
- LLM inventories can differ between fresh runs despite the same source and policy. Count arithmetic over a frozen cached inventory is deterministic; fresh visual extraction is not established as deterministic.
- Raster inventory baseline disables per-question visual recounts. Audit sample uses a separate review policy; do not mix their results as one frozen pipeline.
- The native-plus-raster composite combines separate frozen development runs and is not an end-to-end production validation.
- No claim of 99.9% accuracy or reliability on arbitrary internet drawings, unsupported formats or every possible question follows from these results.
- Token costs are estimates before credits; hosting/storage are excluded. Reconstructed bulk cost is explicitly not an invoice.

CubiCasa5K, (c) 2019 CubiCasa; Kalervo et al., SCIA 2019. Dataset notices apply CC BY-NC-SA 4.0; non-commercial use only.

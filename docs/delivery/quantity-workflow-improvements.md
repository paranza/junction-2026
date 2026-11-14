# Source quantity workflow improvements

14 November 2026. Implements the product priorities from the public competitor review and integrates Matteo's room-outline takeoff and whole-chat CSV changes.

## Delivered behavior

- Gemini can plan bounded native queries with exclusions, explicit OR filters, medians, grouped counts/areas, percentages, ratios and signed differences. Python selects the source records, converts compatible units and computes the result. The model cannot return an answer literal or executable expression through this interface. Missing units, unknown IDs, unresolved joins and zero denominators are refused.
- Follow-up questions can reuse the previous source selection within the same drawing, page and region. Reviewed selections are identified as human changes. The system does not treat a reviewed count as a newly measured room property. Ambiguous selection requests can return a concrete clarification question.
- Schedule queries support material groups, numeric dimension filters, quantity multiplied by a dimensioned source column and exact-key joins across sheets. Joined answers cite both pages and refuse duplicate keys. Row count and summed quantity remain separate operations. Source cell boxes are retained where extraction supplies them.
- Chat artifacts show grouped quantities in a table with source buttons. Count corrections update the displayed draft immediately. Saving uses a revision check, so a stale tab cannot overwrite a newer correction. Per-answer JSON/CSV downloads save pending changes first and export one persisted revision, including excluded evidence and an immutable original value. The JSON receipt includes a checksum. Whole-chat CSV also includes grouped rows.
- Matteo's native outline measurements provide perimeters, skirting lengths, wall areas with an explicitly supplied height and explicitly requested waste allowances. Openings are not deducted from wall areas. Both the per-answer evidence receipt and whole-chat quantity CSV are retained.
- Health reports the loaded solver hash and current source hash separately. Requests refuse a backend whose files changed without restart, preventing a new frontend from silently running old Python functions.

## Verification and accuracy boundaries

The final build passes **371 Python tests**, **59 frontend tests** and the production frontend build. Eight live Gemini planning checks on newly authored DXF/PDF development fixtures passed: exclusion, median, signed area difference, percentage, material groups, cross-sheet fire rating, quantity multiplied by width and a selection-preserving follow-up. These are functional checks, not a held-out accuracy estimate. The sources contain the operands; no gold answers or lookup table enter application inference.

The native development regression uses the same 7,066 questions and source hashes as the previous release. The aggregate verification record accompanies this document. Native raster abstentions do not measure hosted vision quality. The separate 924-question reserve and the previously released independent evaluation were not scored or inspected.

Browser verification exercised an uploaded DXF, grouped results, a count correction from two to one, saving and downloading the same CSV revision, and restoration after refresh. The isolated test runtime's model allowance was also exhausted deliberately by development work: the app displayed the allowance error and still answered a subsequent native query without another model request. Existing user runtimes have separate counters and policies.

## Detector and inference experiments

An optional checksum-verified ONNX heatmap adapter and an export tool for the team's old PlanNet checkpoint are included. Weights are not committed or enabled. The recovered checkpoint predicted no usable detections at its fixed threshold on eight development drawings, giving **0/14 exact door/window counts**. PyTorch/ONNX outputs agreed within 1.61e-7; conversion was not the cause. This is an unsuccessful experiment, not an accuracy improvement.

A separately cached focused door/window reader was compared with the standard inventory on 12 preselected development drawings, comprising 22 English questions. Both returned **12/22 correct**: doors 8/10 and windows 4/12. Every focused count matched its baseline count. The study used 68 actual model attempts. The focused reader remains an experimental opt-in, with the standard reader retained.

An adaptive reading policy can skip the second reading when the first reports complete, unambiguous candidates. Its live check on the first preselected drawing instead required two readings, took about 318 seconds and remained incorrect. A warm repeat used zero model requests and preserved its value. Completeness and self-reported certainty do not establish correctness. The reviewed default remains two readings with `repeat`; no accuracy or latency gain is claimed from this experiment. The full isolated development session used 80 model attempts, including planning checks, browser checks and the studies. Pricing was unconfigured for these models, so token cost remains unknown rather than zero.

## Configuration and limits

`STOA_INVENTORY_POLICY=repeat` and `STOA_SYMBOL_READER=standard` preserve reviewed behavior. `adaptive` and `focused` are experimental alternatives. Leave `STOA_DETECTOR_MANIFEST` unset for the release. Optional detector dependencies are isolated in `requirements-detector.txt`; core deployment does not install Torch or model weights.

The query planner has bounded operations and a preview of source records, not arbitrary SQL or code execution. It can still misunderstand a question. Cross-sheet joins require real unique keys and extracted tables. Region membership uses registered object anchors/centers, not clipped polygon area. Image-only detection remains the largest measured weakness; these changes do not establish 99.9% accuracy or support every arbitrary file. The strongest demonstrable difference is an inspectable path from question to source operands, correction and reusable quantities.

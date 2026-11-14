# Full-path model coverage development check

14 November 2026. This check measures the application's automatic path, including Gemini, rather than treating a native-only regression score as the complete product score.

## Newly verified coverage

All 33 numeric failures outside CubiCasa from the previous 7,066-question native development run were selected before inference. Requests contained the source document, question and scope, never the expected answer. The existing main code used Gemini Argon with ultra-high images, high thinking, repeated inventories and a 600-second timeout in an isolated development runtime.

| Source cohort | Questions | Numeric answers | Correct | Request errors |
| --- | ---: | ---: | ---: | ---: |
| Opening Design PDFs previously unanswered in native mode | 13 | 12 | 12 | 1 |
| IFC-derived drawing questions previously unanswered in native mode | 20 | 12 | 2 | 0 |
| Total targeted development cohort | 33 | 24 | 14 | 1 |

The first row demonstrates **12 correct additional answers relative to native-only mode**, including room-area sums, filtered schedule quantities, window-unit multiplication and visual fixture counts. Ten answers used model-planned schedule execution; two used the visual path. The remaining schedule question ended with a model analysis failure after three attempts. This is **12/13 correct across that selected PDF cohort**, not a new whole-platform accuracy score or a before/after comparison against the prior automatic pipeline.

## Whole-model scope failure and correction

The 20 IFC-source cases point to a projected upper-floor PDF/SVG whose complete linked IFC is absent. Eight requests concern quantities unavailable from the extracted projection. Twelve requests ask for whole-model entity counts. The model incorrectly treated visible projection records or visible image objects as the full model: ten answers were wrong and two happened to match the reference count without establishing whole-model coverage.

The application now detects this missing source scope before any model fallback. It requests the IFC or a question about the visible plan, with no fabricated numeric total. Live verification on all 12 model-count requests returned `needs_input` with zero model calls. It deliberately removes the two coincidentally correct but unsupported totals as well. Do not describe this as a higher exact-match score across all 33 questions: it improves source validity and precision by abstaining where full-model evidence is missing. Native IFC attachments and explicitly visible-plan questions remain available.

## Additional visual experiment

The same predeclared 12-drawing development sample from the prior symbol study was read through four independent overlapping crop requests per drawing. Each request also received the full page for context. Python mapped boxes back to the source, assigned detections to non-overlapping core regions and associated duplicate observations. No answer labels, counts or reference boxes entered inference.

The experiment used 48 real model calls. It returned **12/22 exact door/window counts**, the same as the standard inventory. Only one predicted count changed, and it remained wrong. Independent crop requests therefore were not integrated into the release. The application model-path study used another 32 attempts, for 80 isolated development attempts in total. Unconfigured token pricing remains unknown, not zero cost.

## Interpretation and next accuracy gate

Track three separate metrics on the same frozen cases: answered fraction, correct fraction across all answerable cases and precision among answered cases. Report failures and unsupported source scope alongside them. A model that invents more numbers increases apparent coverage while reducing usefulness.

The tested source-query path already expands coverage beyond deterministic handlers. The remaining visual weakness needs a materially different signal, such as a separately trained detector/segmenter and explicit assembly-boundary evaluation; more repetitions of the same model have not shown a gain. Any future candidate should beat the standard reader on both an exposed development sample and a separate predeclared development confirmation sample before release. Do not use the protected preview reserve or rerun the released independent evaluation to select it.

The native regression, build checks and live scope verification are recorded with this release. No reserved files were scored or inspected, and no paid requests were made against production.

# Complete development selection with Gemini Carbon

The frozen automatic run used application revision `190e116`, Gemini Carbon,
high image resolution, medium thinking, 24,000 output tokens, no small-image
crops, two inventory readings and the standard reader. No specialist detector
or failure fallback was enabled. Later source changes are not measured here.

Only the frozen 7,066-question development selection was eligible. The separate
924-question preview reserve was not inspected or scored. The independent
reserved-file evaluation already released for the final policy was not rerun.
Reference answers were used only by the local scorer, never inference.

| Outcome | Questions |
|---|---:|
| Selected | 7,066 |
| Executed | 6,967 |
| Returned an answer | 6,828 |
| No useful answer or clarification needed | 132 |
| Technical failure | 7 |
| Not executed after a drawing failed | 99 |

Of 6,801 numeric questions, 6,669 received a numeric answer: 6,305 correct and
364 incorrect. Answered numeric precision was **94.54%**. Correct numeric
answers divided by all selected numeric questions was **92.71%**, including
abstentions, technical failures and skipped cases as incorrect. Counts require
exact equality; measurements allow the frozen 2% relative tolerance.

There were 159 returned free-text answers. They require manual assessment and
are not credited as correct in either numeric metric.

| Source | Selected | Answered | Correct numeric / answered numeric |
|---|---:|---:|---:|
| CubiCasa5K | 3,534 | 3,426 | 3,063 / 3,426 (89.40%) |
| Swiss Dwellings | 2,170 | 2,170 | 2,170 / 2,170 |
| IFC models | 1,049 | 1,025 | 1,025 / 1,025 |
| Opening Design | 64 | 64 | 47 / 48 |
| IFC Bench | 249 | 143 | Free text, ungraded |

The CubiCasa result measures the visual inventory used by the application.
Whole-app precision also includes native methods and must not be described as
Gemini-only accuracy. High source-specific precision does not imply complete
coverage: IFC models include one technical failure and 21 skipped questions;
CubiCasa includes six technical failures and 78 skipped questions.

The cumulative SQLite ledger contains 879 model attempts under a 1,000-attempt
ceiling, including earlier retained attempts. Response usage alone misses some
failed or reconciled requests. Cached inventories let many questions share an
extraction. Raw checkpoints and gold-bearing reports remain private; the
aggregate report contains hashes, policy, outcomes and source-level metrics.

The run finished with incomplete coverage. Failed drawings were not silently
replayed to replace outcomes. A scheduler stopped when it reached an output
already owned by another source runner; that source's owning run completed.
This is a development measurement, not an untouched generalization result or
evidence of 99.9% accuracy.

# Native development regression after generalization guards

Tested Trace code `c78b0b7c37b7397b60130abb199470b844375c35` against pre-change `d6f5b0c908ec3f2e3fa907e22d5ab16e01314616`.

**Development only:** all 7,066 development questions were re-run. The reference uses exactly those case IDs from the pre-freeze full baseline. Question, path, label, unit, type and group identity were checked by the existing paired comparator. No reserved subset was scored or inspected.

| Metric | Before | After |
| --- | ---: | ---: |
| Questions | 7066 | 7066 |
| Answered | 1592 | 1592 |
| Numeric questions | 6801 | 6801 |
| Correct numeric answers | 1517 | 1517 |
| Answered numeric questions | 1589 | 1589 |
| Request errors | 0 | 0 |

| Source | Correct numeric before | Correct numeric after | Change |
| --- | ---: | ---: | ---: |
| cubicasa5k | 0/3534 | 0/3534 | +0 |
| ifc_bench | 0/0 | 0/0 | +0 |
| ifc_models | 483/1049 | 483/1049 | +0 |
| opening_design | 10/48 | 10/48 | +0 |
| swiss_dwellings | 1024/2170 | 1024/2170 | +0 |

Previously correct development cases becoming incorrect: **0**. Changed case outcomes: **0**. Every source retained its number of correct native answers.

Model calls, tokens and inference spend: **zero**. Text answers remain subject to manual review. The measured native behavior is unchanged by the upload/measurement guards; this is a regression check, not an accuracy improvement claim.

The JSON records API solver revisions, source-file hashes and the frozen development manifest hash. Timing is not a fair speed comparison because the reference was selected from a differently ordered full run. Hosted vision and novel-file behavior need separate checks.

# Native development regression after IFC quality fixes

Application code `4f0d8e2`, compared with `48d932c3`, on the same frozen development partition only. No reserved inputs were scored.

- Numeric correct: **2929/6801** (43.07%), with unanswered questions counted as failures.
- Answered: **3026/7066**, including 3 text answers requiring human review.
- Answered numeric precision: 96.89%; this is not all-question accuracy.
- All 2903 previously correct answers retained; **0 regressions**.
- 22 previous wrong answers became correct; 4 previous abstentions became correct.
- Errors: 0; model calls: 0.

The fixes derive missing/custom-zero room areas from explicit validated IFC space footprints and resolve stair assemblies through source aggregation. No file-specific answers or evaluation references enter inference. The preview informed development, so this is a regression measure rather than an untouched generalization estimate. The 99.9% supported-question target remains unmet.

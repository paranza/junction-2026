# Full preview native baseline

Code: `d6f5b0c908ec3f2e3fa907e22d5ab16e01314616`. Recorded: 2026-11-14T08:06:40.251542+00:00.

This full preview run preceded the prospective reservation. It is an exposed development baseline, not an untouched test. Gold-bearing cases and detailed answers remain in ignored local evaluation files.

- 1,682/7,990 answered (21.1%).
- 1,598/7,725 numeric questions correct (20.7%, counting abstentions as incorrect).
- 1,598/1,679 answered numeric questions correct (95.2%).
- 3 text answers need manual review; 265 text questions excluded from automatic accuracy.
- 0 recorded model attempts, zero model tokens, no inference spend. 0 request errors.
- Request latency total 77.06 seconds. Native source extraction used a new isolated local runtime; do not compare this directly with cached competitor latency.

## By source

| Source | Questions | Answered | Numeric correct/all | Numeric correct/answered |
| --- | ---: | ---: | ---: | ---: |
| cubicasa5k | 4270 | 0 | 0/4270 | 0/0 |
| ifc_bench | 249 | 1 | 0/0 | 0/0 |
| ifc_models | 1049 | 505 | 483/1049 | 483/505 |
| opening_design | 64 | 12 | 10/48 | 10/10 |
| swiss_dwellings | 2358 | 1164 | 1105/2358 | 1105/1164 |

## By language hint

Language identification is a question-prefix heuristic. Danish Hvad/Hvor and lowercase English how are explicitly included; no answer labels were used to infer language.

| Language | Questions | Answered | Numeric correct/all |
| --- | ---: | ---: | ---: |
| da | 197 | 0 | 0/197 |
| de | 422 | 22 | 20/422 |
| en | 4152 | 1593 | 1523/3887 |
| et | 315 | 25 | 17/315 |
| fi | 2135 | 0 | 0/2135 |
| fr | 395 | 0 | 0/395 |
| it | 374 | 42 | 38/374 |

## Limits

Hosted vision and trained raster inference were not exercised. The preview was already used for EDA and tuning. This is not a competition score or an estimate for arbitrary uploaded drawings. Normalized evidence geometry was checked syntactically, without human citation truth labels. The JSON records code hashes, source-question hash and aggregate usage.

# Ready-to-paste team update

Prepared for Riccardo; not sent automatically.

Current `main` baseline reproduced at `d6f5b0c`, native mode on all 7,990 preview questions, zero model calls and zero request errors:

| Source | Questions | Answered | Numeric correct/all |
| --- | ---: | ---: | ---: |
| CubiCasa | 4,270 | 0 | 0/4,270 |
| Swiss | 2,358 | 1,164 | 1,105/2,358 |
| IFC models | 1,049 | 505 | 483/1,049 |
| IFC-Bench | 249 text | 1 | Not automatically scored |
| Opening Design | 64, including 16 text | 12 | 10/48 |

Overall: **1,682/7,990 answered (21.1%)**; **1,598/7,725 numeric correct (20.7%)**; **1,598/1,679 answered numeric correct (95.2%)**. Three text answers need review. Request latency total was 77.06 seconds on a new isolated native runtime.

Numeric correct/all by language hint: **English 1,523/3,887; Finnish 0/2,135; French 0/395; Danish 0/197; German 20/422; Estonian 17/315; Italian 38/374**. Coverage remains the principal native gap. This does not measure hosted vision or the separate trained-model app.

Prospective quarantine is frozen: **48/317 groups (15.14%), 924 questions**, fixed seed `trace-saturday-reservation-20261114-v1`; membership hash `f63657ea0b2038376fdeedf83738635c8b7569831d74b1766b2c0cd939f237fc`. Development has **269 groups / 7,066 questions**. Existing diagnostic/demo groups stay in development. There are no reserved IFC/Opening Design groups; all their preview groups had already appeared in focused checks. The team already exposed the preview through EDA and full evaluation, so this is a future quarantine, not an untouched holdout. Do not score or debug the reserved cases until Sunday. Use the development manifest for Saturday PR comparisons.

See [evaluation protocol](README.md) and [measured summary](../../stoa-trace/ops/reports/riccardo-delivery/native-full-baseline-summary.md). No gold-bearing manifests or raw expected-answer cases were added to Git.

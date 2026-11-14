# Trace dataset benchmark

Mode: **vision**. Suite: **full**. Frozen manifest: `053bde068a0747ba53d9697f9407e5d548cc81e4eab1315679eaf18a04c53412`.

Gold answers were used only by the evaluator. Text needs manual review. Geometry validation does not establish citation correctness.

Answered 3/3 (100.0%). Numeric accuracy: 66.7% across all numeric cases; 66.7% across answered numeric cases.
Text cases: 0, answered for manual review: 0. Request latency p50/p95: 8182.8 / 26044.02 ms.

| Source | Cases | Coverage | Numeric correct/all | Numeric accuracy answered |
|---|---:|---:|---:|---:|
| cubicasa5k | 1 | 100.0% | 0/1 | 0.0% |
| opening_design | 1 | 100.0% | 1/1 | 100.0% |
| swiss_dwellings | 1 | 100.0% | 1/1 | 100.0% |

| Type | Cases | Coverage | Correct/all numeric |
|---|---:|---:|---:|
| area | 2 | 100.0% | 2/2 |
| count | 1 | 100.0% | 0/1 |

## Case results

| Case | Source line | Outcome | Method | Milliseconds |
|---|---:|---|---|---:|
| stoa-f11b23fc14c5 | 5653 | correct | vision | 5610.7 |
| stoa-c238f3b0dd7b | 5593 | correct | vision | 8182.8 |
| stoa-8345b9b3fde2 | 1219 | incorrect | vision | 26044.0 |

# End-to-end evaluation

14 November 2026, commit `d0c9fcd` on main, on the whole preview question set: 7,990 questions, of which 7,725 have a numeric answer and 265 are free text that needs manual review. The code solvers answered every source with no model calls. The CubiCasa plans were then answered through the application's own API in automatic mode with `ops/bulk_evaluate.py`: gemini-4-argon, ultra-high image resolution, two readings per page and the CubiCasa annotation profile, which are the defaults. Answer labels were read only by the evaluators.

## Result

| Source | Numeric questions | Correct |
| --- | ---: | ---: |
| swiss_dwellings | 2,358 | 2,358 (100%) |
| ifc_models | 1,049 | 1,029 (98.1%) |
| opening_design | 48 | 35 |
| cubicasa5k | 4,270 | 3,796 (88.9%) |
| **Total** | **7,725** | **7,218 (93.4%)** |

Free text was not scored: 249 ifc_bench questions and 16 opening_design questions.

The code solvers answered 3,422 numeric questions and all 3,422 were right. The 20 ifc_models and 13 opening_design numeric questions they did not answer count as wrong. Three free-text questions received an answer for manual review.

## By language

| Language | Numeric questions | Correct |
| --- | ---: | ---: |
| English | 3,887 | 3,627 (93.3%) |
| Finnish (all CubiCasa) | 2,135 | 1,898 (88.9%) |
| German | 422 | 412 (97.6%) |
| French | 395 | 395 (100%) |
| Italian | 374 | 374 (100%) |
| Estonian | 315 | 315 (100%) |
| Danish | 197 | 197 (100%) |

Translated questions are copies of English ones with the same answers, so they are not independent evidence.

## CubiCasa plans

3,796 of 4,270 answers were right. English and Finnish twins scored the same, 1,898 each, because both reach the same inventory.

| Plans | English questions | Correct |
| --- | ---: | ---: |
| 54 held out, never used for a decision | 482 | 425 (88.2%) |
| 187 development | 1,653 | 1,473 (89.1%) |

By question type, English and Finnish together:

| Category | Correct |
| --- | ---: |
| windows | 246 / 482 |
| doors | 262 / 352 |
| showers and bathtubs | 406 / 454 |
| sinks and wash basins | 436 / 478 |
| bedrooms | 288 / 308 |
| toilets | 472 / 480 |
| kitchens | 314 / 322 |
| bathrooms | 216 / 222 |
| floors | 476 / 482 |
| saunas | 326 / 330 |
| balconies | 132 / 136 |
| separate WC rooms | 222 / 224 |

One plan, `high_quality_architectural-13794`, failed because Gemini returned a server error on both readings; its 23 questions were not run and count as wrong. The run made 480 model calls.

Repeated readings: where the two readings gave the same count, 3,556 of 3,898 answers were right (91.2%); where they differed, 46 of 118 (39.0%). The other 254 answers have no agreement record, because one reading failed, no count was given or the plan's questions did not run.

## Reproduce

From `stoa-trace/`, with the preview in `~/stoa-data/junction-dataset-preview` and a Gemini key in the environment:

```sh
echo '{"cases": []}' > /tmp/no-exclusions.json
python ops/grouped_manifest.py --dataset-root ~/stoa-data/junction-dataset-preview \
  --exclude-manifest /tmp/no-exclusions.json --count 100000 --max-per-group 100000 \
  --languages all --output /tmp/full-manifest.json
STOA_PROVIDER=gemini STOA_MAX_MODEL_CALLS=700 STOA_RUNTIME_DIR=/tmp/trace-e2e \
  python -m uvicorn server.app:app --host 127.0.0.1 --port 8799
python ops/benchmark.py --manifest /tmp/full-manifest.json --base-url http://127.0.0.1:8799 \
  --mode native --max-questions 100000 --output /tmp/native.json
python ops/bulk_evaluate.py --manifest /tmp/full-manifest.json --source cubicasa5k \
  --base-url http://127.0.0.1:8799 --mode auto --allow-paid --concurrency 8 \
  --max-model-calls 600 --code-revision d0c9fcd --output /tmp/cubicasa.jsonl --summary /tmp/cubicasa-summary.json
```

The manifest must report 7,990 cases with a `cases_sha256` starting `29c62329`.

## Limits

- The preview was used for development: the dataset analysis, the code solvers' rules and the CubiCasa prompt were all shaped on these questions. Only the 54 held-out CubiCasa plans were never used for a decision.
- Free-text answers are not included in the total.
- Gemini output varies slightly between runs, by about two to four answers in 524 on repeated readings.

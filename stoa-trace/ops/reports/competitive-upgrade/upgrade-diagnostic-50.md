# Trace dataset benchmark

Mode: **native**. Suite: **full**. Frozen manifest: `053bde068a0747ba53d9697f9407e5d548cc81e4eab1315679eaf18a04c53412`.

Gold answers were used only by the evaluator. Text needs manual review. Geometry validation does not establish citation correctness.

Model calls: 0. Application cache hits: 0. Input/output tokens: 0 / 0. Estimated request cost: 0.0 USD.

Answered 30/50 (60.0%). Numeric accuracy: 63.6% across all numeric cases; 100.0% across answered numeric cases.
Text cases: 6, answered for manual review: 2. Request latency p50/p95: 26.97 / 2015.71 ms.

| Source | Cases | Coverage | Numeric correct/all | Numeric accuracy answered |
|---|---:|---:|---:|---:|
| cubicasa5k | 12 | 0.0% | 0/12 | n/a |
| ifc_bench | 4 | 25.0% | 0/0 | n/a |
| ifc_models | 14 | 78.6% | 11/14 | 100.0% |
| opening_design | 6 | 66.7% | 3/4 | 100.0% |
| swiss_dwellings | 14 | 100.0% | 14/14 | 100.0% |

| Type | Cases | Coverage | Correct/all numeric |
|---|---:|---:|---:|
| area | 12 | 100.0% | 12/12 |
| count | 28 | 50.0% | 14/28 |
| length | 2 | 50.0% | 1/2 |
| text | 6 | 33.3% | 0/0 |
| volume | 2 | 50.0% | 1/2 |

## Case results

| Case | Source line | Outcome | Method | Milliseconds |
|---|---:|---|---|---:|
| stoa-5215fd19196a | 4520 | correct | native_ifc_entity_count | 2015.7 |
| stoa-5ccbe432c27c | 4521 | correct | native_ifc_entity_count | 750.1 |
| stoa-2e8b6c0f4de5 | 4523 | correct | native_ifc_entity_count | 78.8 |
| stoa-553ab80f9377 | 5151 | correct | native_ifc_entity_count | 2237.7 |
| stoa-b389a915ba5f | 5633 | correct | native_cad_unit_outlines | 6.9 |
| stoa-540bf3d2b657 | 5635 | correct | native_cad_room_labels | 8.4 |
| stoa-f11b23fc14c5 | 5653 | correct | native_cad_area_annotations | 5.8 |
| stoa-e510fda982b8 | 5657 | correct | native_cad_area_annotations | 7.7 |
| stoa-55ae4ebc6463 | 5569 | correct | native_pdf_schedule_rows | 174.3 |
| stoa-c238f3b0dd7b | 5593 | correct | native_pdf_schedule_area | 8.6 |
| stoa-53847bf46b4d | 87 | unanswered | native | 5.9 |
| stoa-6393ce817660 | 341 | unanswered | native | 3.9 |
| stoa-0c688e085705 | 673 | unanswered | native | 6.1 |
| stoa-e020e323ec1f | 803 | unanswered | native | 5.4 |
| stoa-8251a1479b86 | 933 | unanswered | native | 7.0 |
| stoa-8345b9b3fde2 | 1219 | unanswered | native | 13.9 |
| stoa-e552efbf5e6f | 1337 | unanswered | native | 11.8 |
| stoa-ddc156244165 | 1611 | unanswered | native | 7.6 |
| stoa-0ed59261f807 | 2799 | unanswered | native | 22.1 |
| stoa-088b0233025b | 3699 | unanswered | native | 61.4 |
| stoa-8c8a836b7d71 | 3743 | unanswered | native | 85.1 |
| stoa-51cbf40ce1a6 | 3873 | unanswered | native | 25.0 |
| stoa-5a344b50e420 | 4271 | unanswered | native | 559.3 |
| stoa-c53fb13fb674 | 4319 | unanswered | native | 311.3 |
| stoa-3cc81511e3b0 | 4383 | unanswered | native | 80.8 |
| stoa-bbee739ae0f0 | 4434 | manual_review | native_ifc_project_records | 294.6 |
| stoa-e1792074505b | 4543 | correct | native_ifc_quantity | 612.5 |
| stoa-3de0f151bfde | 4913 | correct | native_ifc_quantity | 13.2 |
| stoa-1de5c295c30b | 5153 | correct | native_ifc_entity_count | 48.4 |
| stoa-052a20061b71 | 5173 | correct | native_ifc_quantity | 12.8 |
| stoa-f0d8bd3b97dc | 5213 | correct | native_ifc_quantity | 2245.3 |
| stoa-79440545ee25 | 5241 | correct | native_ifc_quantity | 42.4 |
| stoa-4bff20999adc | 5245 | correct | native_ifc_quantity | 41.2 |
| stoa-7366be9ccdd9 | 5545 | unanswered | native | 12.8 |
| stoa-7c4a0b55d02d | 5561 | unanswered | native | 2.7 |
| stoa-2e7e3213f261 | 5565 | unanswered | native | 3.1 |
| stoa-c998c62ce87c | 5572 | unanswered | native | 6.2 |
| stoa-fb4aafd7adec | 5586 | manual_review | native_pdf_schedule_row | 190.8 |
| stoa-23e78fba41ef | 5597 | correct | native_pdf_schedule_area | 28.9 |
| stoa-beb726b3bf24 | 5623 | unanswered | native | 96.1 |
| stoa-e1171b65035e | 5643 | correct | native_cad_symbol_inventory | 13.8 |
| stoa-250e6a10214d | 5645 | correct | native_cad_symbol_inventory | 7.4 |
| stoa-5cb1a3d69c42 | 5701 | correct | native_cad_unit_outlines | 136.9 |
| stoa-813eeadde81d | 5707 | correct | native_cad_room_labels | 6.9 |
| stoa-c1e40dbddfc3 | 5721 | correct | native_cad_symbol_inventory | 5.9 |
| stoa-41fe201e8f6a | 6063 | correct | native_cad_area_annotations | 45.7 |
| stoa-a0acae81b4f2 | 6287 | correct | native_cad_area_annotations | 82.2 |
| stoa-88671673d197 | 6559 | correct | native_cad_area_annotations | 83.3 |
| stoa-1c15a43ad741 | 7571 | correct | native_cad_symbol_inventory | 100.9 |
| stoa-33700bcca7a2 | 7631 | correct | native_cad_area_annotations | 137.6 |

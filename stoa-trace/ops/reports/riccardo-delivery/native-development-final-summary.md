# Native development regression

Evaluated source commit: `48d932c3bb2708744eb14056306b080623a84c79`.

Only the frozen 7,066-question development partition was run. The reserved partition and independent frozen drawings were not evaluated. Both provider keys were empty, model allowance was zero, and the isolated runtime recorded zero model-request events.

This development set has informed changes. These results are not held-out validation and do not establish 99.9% accuracy on unseen drawings.

| Metric | Previous baseline, same development IDs | Current |
|---|---:|---:|
| Questions | 7066 | 7066 |
| Answered, including text | 1592 | 3022 |
| Numeric questions | 6801 | 6801 |
| Answered numeric | 1589 | 3019 |
| Correct numeric | 1517 | 2903 |
| Incorrect answered numeric | 72 | 116 |
| Errors | 0 | 0 |
| Model calls | 0 | 0 |
| Coverage, including text | 22.53% | 42.77% |
| Numeric accuracy over all numeric questions | 22.31% | 42.68% |
| Numeric accuracy among answered numeric questions | 95.47% | 96.16% |

## Paired numeric changes

| Change | Questions |
|---|---:|
| correct retained | 1517 |
| correct to incorrect | 0 |
| correct to unanswered | 0 |
| incorrect to correct | 7 |
| unanswered to correct | 1379 |
| unanswered to incorrect | 51 |
| incorrect retained | 65 |
| incorrect to unanswered | 0 |

## Incorrect answered quantities

No previously correct development answer became incorrect or unanswered. Newly answered cases include incorrect answers; increased coverage must not be described as 99.9% precision.

### all answered numeric

Questions: 116.

| Native method | Incorrect answers |
|---|---:|
| native_cad_area_annotations | 18 |
| native_cad_room_labels | 6 |
| native_cad_symbol_inventory | 46 |
| native_cad_unit_outlines | 18 |
| native_ifc_entity_count | 8 |
| native_ifc_quantity | 20 |
### newly answered numeric

Questions: 51.

| Native method | Incorrect answers |
|---|---:|
| native_cad_area_annotations | 9 |
| native_cad_room_labels | 3 |
| native_cad_symbol_inventory | 23 |
| native_cad_unit_outlines | 3 |
| native_ifc_entity_count | 3 |
| native_ifc_quantity | 10 |

## Source

| Source | Cases | Baseline correct/all numeric | Current correct/all numeric | Current answered numeric | Current precision on answered numeric | Correct lost | Errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| cubicasa5k | 3534 | 0/3534 | 0/3534 | 0 | n/a | 0 | 0 |
| ifc_bench | 249 | 0/0 | 0/0 | 0 | n/a | 0 | 0 |
| ifc_models | 1049 | 483/1049 | 931/1049 | 959 | 97.08% | 0 | 0 |
| opening_design | 64 | 10/48 | 10/48 | 10 | 100.00% | 0 | 0 |
| swiss_dwellings | 2170 | 1024/2170 | 1962/2170 | 2050 | 95.71% | 0 | 0 |

## Language hint

| Language hint | Cases | Baseline correct/all numeric | Current correct/all numeric | Current answered numeric | Current precision on answered numeric | Correct lost | Errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| de | 383 | 18/383 | 337/383 | 352 | 95.74% | 0 | 0 |
| en | 3689 | 1444/3425 | 1457/3425 | 1515 | 96.17% | 0 | 0 |
| et | 315 | 17/315 | 300/315 | 311 | 96.46% | 0 | 0 |
| fi | 1767 | 0/1767 | 0/1767 | 0 | n/a | 0 | 0 |
| fr | 340 | 0/340 | 305/340 | 319 | 95.61% | 0 | 0 |
| it | 374 | 38/374 | 339/374 | 354 | 95.76% | 0 | 0 |
| unknown | 198 | 0/197 | 165/197 | 168 | 98.21% | 0 | 0 |

## Type

| Type | Cases | Baseline correct/all numeric | Current correct/all numeric | Current answered numeric | Current precision on answered numeric | Correct lost | Errors |
|---|---:|---:|---:|---:|---:|---:|---:|
| area | 1541 | 668/1541 | 1331/1541 | 1369 | 97.22% | 0 | 0 |
| count | 5210 | 835/5210 | 1544/5210 | 1622 | 95.19% | 0 | 0 |
| length | 16 | 7/16 | 14/16 | 14 | 100.00% | 0 | 0 |
| text | 265 | 0/0 | 0/0 | 0 | n/a | 0 | 0 |
| volume | 34 | 7/34 | 14/34 | 14 | 100.00% | 0 | 0 |

## Limits

- These development questions have informed changes; this is not held-out validation or a 99.9% accuracy claim.
- Correctness means agreement with supplied development labels, not independent engineering ground truth.
- Native mode does not measure raster model accuracy; unsupported native requests may abstain.
- Text is excluded from numeric accuracy and requires manual review.
- Language hints are evaluation metadata rather than a claim of universal language understanding.
- Only aggregate metrics are published; no question text, answer labels, case identifiers, raw responses or local paths are included.

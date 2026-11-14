# Trace dataset benchmark

Mode: **native**. Suite: **full**. Frozen manifest: `a97b1ab16f6786e8eea6c18f0d927860cd63cdf53d8334fd9b0860c371144bc9`.

Gold answers were used only by the evaluator. Text needs manual review. Geometry validation does not establish citation correctness.

Model calls: 0. Application cache hits: 0. Input/output tokens: 0 / 0. Estimated request cost: 0.0 USD.

Answered 58/100 (58.0%). Numeric accuracy: 56.7% across all numeric cases; 94.8% across answered numeric cases.
Text cases: 3, answered for manual review: 0. Request latency p50/p95: 7.24 / 159.02 ms.

| Source | Cases | Coverage | Numeric correct/all | Numeric accuracy answered |
|---|---:|---:|---:|---:|
| cubicasa5k | 33 | 0.0% | 0/33 | n/a |
| ifc_bench | 3 | 0.0% | 0/0 | n/a |
| swiss_dwellings | 64 | 90.6% | 55/64 | 94.8% |

| Type | Cases | Coverage | Correct/all numeric |
|---|---:|---:|---:|
| area | 32 | 84.4% | 26/32 |
| count | 65 | 47.7% | 29/65 |
| text | 3 | 0.0% | 0/0 |

## Case results

| Case | Source line | Outcome | Method | Milliseconds |
|---|---:|---|---|---:|
| grouped-005a5461bf7df41b | 2461 | unanswered | native | 10.3 |
| grouped-041c502afd640c35 | 4476 | unanswered | native | 1642.9 |
| grouped-019a7cb9baf3e8b1 | 7501 | correct | native_cad_area_annotations | 474.6 |
| grouped-0074658fdaf51ca2 | 6581 | correct | native_cad_symbol_inventory | 57.5 |
| grouped-0066440721aea02d | 3679 | unanswered | native | 7.3 |
| grouped-051cdceb865b3a27 | 4518 | unanswered | native | 12.9 |
| grouped-01ed8f4cfa941de9 | 6771 | correct | native_cad_area_annotations | 53.6 |
| grouped-007e3c73fe989034 | 6907 | unanswered | native | 102.8 |
| grouped-0068ee5f55373aca | 2879 | unanswered | native | 4.5 |
| grouped-06d776b41efd49ab | 4483 | unanswered | native | 11.1 |
| grouped-0368e16bb6fadec1 | 7793 | correct | native_cad_area_annotations | 54.1 |
| grouped-00c59a6513d6d89b | 7749 | correct | native_cad_symbol_inventory | 96.3 |
| grouped-008271cc4c952e16 | 1303 | unanswered | native | 4.4 |
| grouped-04b6e43aaea17ccf | 6891 | correct | native_cad_area_annotations | 77.6 |
| grouped-0121ee4e63d7ed2a | 7123 | correct | native_cad_room_labels | 75.9 |
| grouped-008babfeebe5a62e | 1705 | unanswered | native | 4.6 |
| grouped-05d9baa5119cd8f8 | 7279 | correct | native_cad_area_annotations | 38.7 |
| grouped-0131cb5c61156328 | 6661 | correct | native_cad_symbol_inventory | 50.9 |
| grouped-00987e6ea3006653 | 1887 | unanswered | native | 4.7 |
| grouped-07d262fa9ce0f044 | 6857 | incorrect | native_cad_area_annotations | 90.7 |
| grouped-014d062b57aa88e8 | 6603 | correct | native_cad_room_labels | 89.5 |
| grouped-009cf998350ebac6 | 4145 | unanswered | native | 4.0 |
| grouped-08db70cbad107dff | 6243 | correct | native_cad_area_annotations | 82.6 |
| grouped-027103665e3bf192 | 6289 | correct | native_cad_unit_outlines | 91.4 |
| grouped-00eccbcc1f04ed58 | 3861 | unanswered | native | 5.3 |
| grouped-097aa58d60c466f3 | 6487 | correct | native_cad_area_annotations | 48.3 |
| grouped-02a7dbf51facf28e | 6867 | correct | native_cad_room_labels | 5.4 |
| grouped-010eda146b504d3a | 1349 | unanswered | native | 12.1 |
| grouped-09cc75d4b12b8bdc | 7321 | unanswered | native | 79.1 |
| grouped-035481c884d45a94 | 7933 | incorrect | native_cad_symbol_inventory | 173.2 |
| grouped-0118a61da5edce2a | 995 | unanswered | native | 4.5 |
| grouped-09ea86ad8119ad81 | 6775 | correct | native_cad_area_annotations | 5.7 |
| grouped-038b48bdf5b38204 | 7129 | correct | native_cad_symbol_inventory | 12.5 |
| grouped-012588b1ee882c5c | 99 | unanswered | native | 5.2 |
| grouped-0a7437ab08939137 | 7955 | correct | native_cad_area_annotations | 18.7 |
| grouped-03a0a0b560e8dcdc | 6079 | correct | native_cad_symbol_inventory | 111.9 |
| grouped-01397e771a6767a9 | 33 | unanswered | native | 4.2 |
| grouped-0ad7a90ea0fb0297 | 6927 | correct | native_cad_area_annotations | 5.6 |
| grouped-03d845b7a732da25 | 5797 | correct | native_cad_symbol_inventory | 89.2 |
| grouped-0144896c3b7822b6 | 1595 | unanswered | native | 5.7 |
| grouped-0be70b2f78ebf053 | 7499 | correct | native_cad_area_annotations | 8.5 |
| grouped-048b15bc811fe1d2 | 6459 | correct | native_cad_room_labels | 7.2 |
| grouped-016d1ac9b24eb3cc | 983 | unanswered | native | 5.0 |
| grouped-0c239e93acaca763 | 7217 | unanswered | native | 336.0 |
| grouped-0520fb2a4a06bdd4 | 7781 | correct | native_cad_symbol_inventory | 7.0 |
| grouped-01d0b8313c0f945c | 4229 | unanswered | native | 4.5 |
| grouped-0f4f17109ff941f7 | 7103 | correct | native_cad_area_annotations | 159.0 |
| grouped-052135f9673e2f10 | 6475 | correct | native_cad_symbol_inventory | 4.6 |
| grouped-01f51ec3a34fb64c | 3149 | unanswered | native | 3.8 |
| grouped-0ff712e1e9f2e946 | 5989 | unanswered | native | 350.2 |
| grouped-05e6d6f71dcefc6c | 6119 | correct | native_cad_symbol_inventory | 48.2 |
| grouped-020964d7c42879bb | 3367 | unanswered | native | 4.5 |
| grouped-100e374b747e5fec | 5695 | correct | native_cad_area_annotations | 94.7 |
| grouped-0603e46294130c4c | 6865 | correct | native_cad_room_labels | 5.0 |
| grouped-023de812c9841ca2 | 1423 | unanswered | native | 3.7 |
| grouped-1136cdaf7bf6a78f | 6697 | correct | native_cad_area_annotations | 30.7 |
| grouped-0671cd2e6a70187d | 7447 | correct | native_cad_room_labels | 52.2 |
| grouped-0248758f8ee17909 | 1183 | unanswered | native | 4.6 |
| grouped-12430469cf07ced6 | 7323 | correct | native_cad_area_annotations | 6.6 |
| grouped-0695ceff3d933fdd | 6145 | correct | native_cad_room_labels | 62.1 |
| grouped-025c99f7ed45e057 | 3407 | unanswered | native | 4.8 |
| grouped-13ce66800306136c | 7951 | unanswered | native | 5.4 |
| grouped-06e4a1eba11e7a73 | 7059 | correct | native_cad_symbol_inventory | 153.2 |
| grouped-02cf5a983f4bb48c | 1871 | unanswered | native | 4.7 |
| grouped-1452ff387139f320 | 7831 | correct | native_cad_area_annotations | 39.4 |
| grouped-071172018efa4cb2 | 7083 | correct | native_cad_room_labels | 9.1 |
| grouped-02d560f64ff44db7 | 3075 | unanswered | native | 6.2 |
| grouped-1473ccfb3db11141 | 6019 | correct | native_cad_area_annotations | 29.1 |
| grouped-073aac821f8672f3 | 7829 | correct | native_cad_symbol_inventory | 4.4 |
| grouped-02f5b7cd6af70718 | 3997 | unanswered | native | 4.0 |
| grouped-171975c8e4673341 | 6591 | correct | native_cad_area_annotations | 5.3 |
| grouped-07a315c8205fb658 | 6299 | correct | native_cad_room_labels | 5.1 |
| grouped-031ae3d882c6998c | 549 | unanswered | native | 4.0 |
| grouped-178014f1abb2d7cc | 6135 | correct | native_cad_area_annotations | 9.9 |
| grouped-08145e161acad637 | 5819 | correct | native_cad_room_labels | 42.9 |
| grouped-0324df36cb5e88c2 | 4239 | unanswered | native | 3.6 |
| grouped-197679d2df775d4f | 6957 | correct | native_cad_area_annotations | 60.0 |
| grouped-08f3df1eb56f91b9 | 6565 | correct | native_cad_room_labels | 6.1 |
| grouped-036e3c4cf24f54fb | 3295 | unanswered | native | 3.9 |
| grouped-1cde32e2f544a68d | 6425 | correct | native_cad_area_annotations | 43.5 |
| grouped-0a1f88116f0b8fbd | 5931 | correct | native_cad_unit_outlines | 93.1 |
| grouped-0386458d3dfeccc9 | 4189 | unanswered | native | 4.1 |
| grouped-1d2d7f72bf24d42d | 6165 | unanswered | native | 4.7 |
| grouped-0a247fa257415ef8 | 6619 | incorrect | native_cad_symbol_inventory | 11.4 |
| grouped-0391712c3d189e4e | 2185 | unanswered | native | 4.2 |
| grouped-1e330d0dd7fdc90d | 7981 | correct | native_cad_area_annotations | 79.2 |
| grouped-0a3d56e23b5d43ab | 6621 | correct | native_cad_symbol_inventory | 7.1 |
| grouped-03b7a4237ddb0450 | 195 | unanswered | native | 3.7 |
| grouped-1f30ea3b328dbec7 | 7141 | correct | native_cad_area_annotations | 4.9 |
| grouped-0ad9969dda9b2f1d | 7209 | correct | native_cad_symbol_inventory | 9.3 |
| grouped-03cf04dcb0fabb46 | 821 | unanswered | native | 3.8 |
| grouped-1f4dcbb17e49d729 | 5985 | correct | native_cad_area_annotations | 6.3 |
| grouped-0b861f62b3aca696 | 7435 | correct | native_cad_unit_outlines | 4.7 |
| grouped-03e178cf6c0cbcbf | 1375 | unanswered | native | 3.9 |
| grouped-1fe9ffad227c6fcb | 6519 | correct | native_cad_area_annotations | 40.7 |
| grouped-0cc454f97dae696d | 6901 | correct | native_cad_room_labels | 6.7 |
| grouped-041609f602390500 | 1905 | unanswered | native | 5.9 |
| grouped-2055aa8f6765cfff | 6089 | correct | native_cad_area_annotations | 5.4 |
| grouped-0d78ed0b947e87c8 | 7403 | correct | native_cad_room_labels | 54.3 |
| grouped-041e5509a994c5c7 | 1133 | unanswered | native | 4.5 |

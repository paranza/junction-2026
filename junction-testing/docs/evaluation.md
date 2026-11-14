# Evaluation

Scoring follows the dataset README: counts must be exact, areas within 2 %.
All numbers below were produced by the scripts named next to them. "Calibrated on" means the
rules were tuned while looking at those questions, so the number is an upper bound, not a
held-out estimate.

## 1. Exact DXF path (no ML) — `python tools/eval_dxf.py`

Swiss Dwellings, all 65 preview drawings, all count and area questions in en/de/fr/it.

| Type | Correct | Accuracy |
| --- | ---: | ---: |
| count | 1614 / 1614 | 100.0 % |
| area | 732 / 744 | 98.4 % |

Calibrated on these questions (drawing conventions: washbasin = oval with drain dot; double door =
two arcs meeting mid-opening; apartments = tagged unit outlines; number-only rooms without fixtures
are shafts). The 12 area misses are apartment/total areas where the dataset's room-to-apartment or
shaft rules differ from ours on a few rooms.

## 2. CubiCasa ground truth and question routing — label check

Our SVG parser (`stoa/cubicasa.py`) + question templates on the 241 preview CubiCasa plans, using
the SVG annotations instead of model predictions. This is the ceiling for the CubiCasa model:

| Question | Correct |
| --- | ---: |
| windows | 241 / 241 |
| doors (with leaf) | 176 / 176 |
| toilet bowls | 240 / 240 |
| sinks and wash basins | 235 / 239 |
| showers and bathtubs | 217 / 227 |
| floors (storeys) | 241 / 241 |
| saunas | 164 / 165 |
| kitchens | 161 / 161 |
| bedrooms | 154 / 154 |
| separate WC rooms | 105 / 112 |
| bathrooms | 103 / 111 |
| balconies | 68 / 68 |
| **all, en + fi** | **4210 / 4270 (98.6 %)** |

## 3. Raster models on held-out images — `python tools/eval_raster.py`

Pending: filled in after training finishes (see PROGRESS.md).

- Swiss: 9 held-out sheets (every 8th drawing), PNG only, PlanNet + GlyphNet.
- CubiCasa: 241 preview plans, never used for training, original resolution (F1_original).

## 4. Inference cost

| Path | Model calls | Typical time (laptop CPU) |
| --- | --- | --- |
| DXF | none | < 1 s |
| PNG / PDF | PlanNet + GlyphNet locally | a few seconds per sheet |
| Template question | none | milliseconds |
| Free-form question | 1 Gemini flash-lite call, ~1.5k input tokens, no image | ~1-2 s |

Measured example: "Which apartment has the largest kitchen?" on a 31-room Swiss floor: 1,445 input
and 167 output tokens with `gemini-3.5-flash-lite`.

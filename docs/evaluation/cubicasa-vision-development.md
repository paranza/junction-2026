# CubiCasa vision development

Evaluation notes for the visual inventory on CubiCasa5K plans, 14 November 2026. Every run scored exact counts on the English questions only; the Finnish twins have the same answers and reuse the same inventory through the question normalizer. Plans were split by a hash of the image name: one in five is held out, and the held-out plans were scored only once, with the final settings on the evaluation branch used before the port to main. Answer labels stayed in the evaluator and never reached a prompt.

## Model and input settings (development plans)

Round 1, 40 plans and 355 questions. Always answering the most common value gets 193.

| Setup | Correct |
| --- | ---: |
| gemini-4-hydrogen, high resolution, CubiCasa rules v1 | 300 |
| same, with enlarged overlapping crops for small plans | 306 |
| gemini-4-argon instead of hydrogen | 314 |
| ultra-high image resolution | 309 |
| one call per group of categories | 306 |
| median of three runs with differently cut crops | 303 |
| xhigh reasoning (stopped after 13 plans) | 106, same as the baseline on those plans |
| gemini-4-carbon (stopped after 5 plans, several times slower) | 49, same as the baseline on those plans |

On the 39 plans where both finished, the enlarged crops scored 297 of 344 against 290, mostly from windows (23 of 39 against 18). One plan spent the whole 32,768-token output budget on reasoning, so Gemini inventories now allow 65,536 tokens.

An error analysis of the 49 remaining misses, made by viewing each failed plan with its boxes, found mostly annotation conventions and label noise. Its rules became the second version of the CubiCasa rules.

Round 2, 60 fresh development plans and 524 questions, all with gemini-4-argon. The most common value gets 300.

| Setup | Correct |
| --- | ---: |
| rules v1 | 462 |
| rules v2 | 460 |
| rules v2, ultra-high resolution | 464 |
| main's Interactions adapter, generic prompt, ultra-high, enlarged crops | 418 |
| same, with the CubiCasa annotation profile (rules v2) | 463 |

## Held-out plans

54 plans and 482 questions, scored once with gemini-4-argon, ultra-high resolution, enlarged crops and rules v2 on the evaluation branch before the port to main (its development score was 464 of 524). The most common value gets 276; the configuration got 421 (87.3%). Main's own adapter has not been scored on these plans yet.

| Question type | Plans | Correct |
| --- | ---: | ---: |
| windows | 54 | 24 |
| toilet bowls | 54 | 52 |
| sinks and wash basins | 54 | 48 |
| floors | 54 | 52 |
| showers and bathtubs | 50 | 46 |
| bedrooms | 38 | 35 |
| kitchens | 38 | 37 |
| saunas | 38 | 38 |
| doors | 37 | 24 |
| separate WC rooms | 26 | 26 |
| bathrooms or washrooms | 25 | 25 |
| balconies | 14 | 14 |

Window errors are mostly undercounts on black-and-white architectural sheets, where the answers split windows inconsistently.

## Repeated readings

The same 60 round-2 plans, read three times with the final configuration on main (two readings at ultra-high resolution, one at high): 463, 459 and 460 correct. The median of the three readings scored 462, so repeating does not raise accuracy.

As a flag it is informative. Where all three readings returned a count (518 questions), they agreed on 498, and 452 of those answers were right (90.8%); on the 20 where they differed, the median was right 8 times. With the first two readings only, which are identical requests, both returned a count on 519 questions: they agreed on 504 with 455 right (90.3%) and differed on 15, where the first reading was right 6 times. The remaining questions had a reading that failed with a network error. Trace therefore makes two readings per page, answers with the first that succeeds and flags a different count for review.

## Printed window and door codes

The same 60 plans, with one extra call that transcribed every window size code and door code and named the drawing style. Window codes were found on 11 of the 38 architectural plans, and the code count matched the answer on 2 of 60 plans. Using the codes on architectural plans where they were found gave 30 correct window answers, the same as the inventory. For doors the code count matched on 6 of 46 plans, and rules using it gave 30 to 32 correct against 33 for the inventory. Code reading was not adopted.

## Usage

The held-out run made 54 calls with 718,344 input and 472,099 output tokens (output includes reasoning), about 13,300 and 8,700 per plan. Dollar costs are not stated here because the gemini-4-argon rates were not configured or checked.

## Limits

- The development plans were also seen during the earlier dataset analysis. Only the held-out numbers come from plans no decision used.
- Run-to-run noise is about two to four questions in 524, so differences of that size are not evidence.
- Counts follow the CubiCasa5K annotation conventions on purpose; uploads and other collections use the generic prompt.

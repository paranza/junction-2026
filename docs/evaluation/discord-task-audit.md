# Audit of the actual Stoa Discord drawing tasks

15 November 2026. This study uses the four original large PNG attachments from
Stoa's 14 November message, not substitute school or service plans. The message
lists task categories: floor areas, baseboard lengths, door/window counts, slab
area by thickness/reinforcement and understanding piping. It does not publish a
fixed hidden question/answer list. Nine operational questions were prepared
from those categories and the user's request to count all school chairs and
measure pipe length. Their source hashes, raw requests and responses are held
privately; reference values never entered inference. Neither reserved evaluation
was used.

## Observed results

| Task on the original attachment | Observed app result | Assessment |
| --- | --- | --- |
| School Multi-Purpose Hall internal area | 245.63 m² | Source-only wall/scale trace gives 245.25 m²; passes the predeclared 7.5 m² tolerance. Both sides of the movable partition included. |
| Dormitory total second-floor area | 2467.69054848 m² | Correct conversion of the printed 26,562 SF, including stair allowance. |
| Whole-school chairs | 306 in the released reader; 323 in the tile experiment | Hall improved from 120 to the independently counted 136, but the experiment still misses an office task chair. No exact-count success. |
| Whole-school passage openings, excluding cabinetry | 110 released; 116 experimental | Exterior plant/stair symbols and sliding assembly interpretation remain unresolved. No exact reference score claimed. |
| Whole-school exterior window openings | 67 released; 68 experimental | Source audit found a candidate on a solid corridor pier. The experiment also adds candidates. No exact-count success. |
| Baseboard in the northernmost west classroom | Initially refused; 29.83 m after intent fix | Initial independent wall/opening trace gives 29.19 m. The result misses the original 0.6 m tolerance; detailed trace audit remains necessary. |
| Gross 150 mm / D13 slab area | Initially refused; 61.69 m² after explicitly declaring drawing dimensions in mm | Correct 6200 by 9950 calculation with supplied units. This is a changed-input control, not a pass of the original unsupplemented question. |
| Gross 300 mm / D16 slab area | Initially refused; 218.73 m² with explicit mm declaration | A nonrectangular decomposition is returned, but exact alcove/foundation boundary interpretation remains ungraded. |
| All shown pipe centrelines on M-101A | No numeric total | Calibration/trace completeness failed. No independently digitized full-network reference exists; do not claim a pipe takeoff success. |

The initial real application API run answered five of nine questions, with
zero technical HTTP failures and 29 actual provider attempts. Answer coverage
is not accuracy: the three counts above are not verified correct. Every response
exported successfully. Separate development follow-ups used 48 attempts for the
three tile inventories, five for the intent-fixed baseboard and five for the
two explicit-unit controls: 87 isolated attempts in total. No existing local or
production attempt counter was reset or consumed by these studies.

The previous 17 correct numeric checks consisted of seven already used and ten
new public-drawing checks. They did not test these nine harder tasks. The 106
classroom-chair and roughly 20 m service-route successes were on other drawings
and cannot stand in for these results.

## Changes and promotion decision

- Fixed measurement intent for phrases such as "how many linear metres" and
  "how many lineal feet" without treating a door-width filter as a length query.
- Calibration can retain a unit suffix from the same positioned OCR token, for
  example a requested substring `8` inside the actual printed token `8'`. It
  cannot borrow a unit from another token or invent missing source units.
- Preserve source polyline geometry in exported measurement evidence.
- Fixed evidence-detail/dialog clicks clearing the selection before a real
  Cloudinary close-up could open. The isolated browser displayed an actual
  transformed crop with original answer rows and model counter unchanged.
- Added a bounded tile inventory prototype: disjoint ownership cores,
  overlapping source context, compact per-object responses and usage-accounted
  parallel requests. **`STOA_PARTITIONED_COUNTS=off` remains the default.** The
  experiment recovers hall rows but does not establish exact-count improvement
  across the tested categories, so it is not promoted into the default policy.

461 backend tests and 59 frontend tests pass, and the frontend production build
passes. Native solver files and the native app flow are unchanged; the large
7,066-case benchmark was not repeated at the user's direction. This is a tested
compatibility/behavior release, not a claim that every sponsor question works.

Raw original studies, failed references and changed-input controls remain
separate. Approximate geometry, source classification, units and complete
network reconstruction remain distinct limitations. The app still needs review
on these difficult drawings; these results do not establish readiness to answer
all final judging questions correctly.

[Machine-readable studies and audit](../../stoa-trace/ops/reports/discord-task-audit/development-results.json),
[partner contribution and submission evidence](../delivery/technical-challenge-evidence.md).

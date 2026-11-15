# Complex source recovery

15 November 2026. This work continues the
[original Discord task audit](discord-task-audit.md), using the same operational
questions and original attachments. No hidden judge questions, reserved preview
questions or supplied answer lookups are used in inference.

## Implemented

- Preserve foot/inch primes during positional OCR deduplication. Calibration can
  recover a clipped scalar annotation from surrounding source context, but the
  qualifying scalar must remain inside the original located annotation box.
- Measure closed perimeters and disconnected paths. Gaps are excluded and exactly
  overlapping shared geometry contributes once. Analytic measurements retain the
  original source aspect rather than the rounded preview aspect.
- Show actual perimeter and route polylines in the drawing. Small disjoint opening
  deductions receive focused source overlays, with a bounded extra correction
  round to inspect the clear wall gap instead of only a door leaf.
- Audit large source-tile object proposals against unmarked source and numbered
  overlays. Completed audited tiles persist privately so an interrupted attempt
  can resume; source, question, coordinates, model, policy or code changes prevent
  inappropriate reuse.
- Add experimental spatial route planning, calibration, local tracing, source
  review, disjoint tile clipping and host length arithmetic. This is visible 2D
  geometry, not a claim about hidden installed routes.
- Restore saved answers linked into a chat. The server's `saved:` message alias
  was rejected by the client and could then duplicate the active answer. Both
  restoration and alias normalization were verified in a real browser refresh.

## Actual results so far

| Check | Observation | Interpretation |
| --- | --- | --- |
| Argon source-audited school windows | 68 marked openings; 38 west block and 30 east block verified against source | A post-inference source audit, not a blind score. The earlier manual reference was wrong and is retained as historical provenance. |
| Carbon source-audited school chairs | 320; the earlier one-pass tiled reader returned 323, against an initial 324 clear-symbol reference | The new audit is not promoted. A later replay found an empty locator in the earlier 323 result. Some initially presumed office chairs have drawer-handle-like outlines and remain semantically ambiguous; no objects are added to match 324. |
| School baseboard with perimeter and explicit deductions | 29.7684 m, within the initial 0.6 m tolerance of the 29.189647 m source reference | Further source interpretation is unresolved: the initial wider doorway deduction may include fixed glazing. The instruction to include wall below windows makes that distinction material. Keep the initial reference and do not silently rescore it. |
| Original piping scale | Both model-proposed annotation boxes now reproduce the printed 8-foot reference through actual source OCR | A real calibration fix with zero model requests in the reproduction, not proof of the whole-network total. |
| Whole visible piping network | Calibration now succeeds, but subsequent tracing attempts still encounter output-budget/provider failures | No independently verified full-network accuracy is claimed. |

The first Argon audit study made 41 attempts: windows returned a number, while
chairs and doors had service errors. These failures remain recorded. Separate
Carbon count and corrected geometry studies have frozen code/configuration and
private raw artifacts; their completed rows are retained even while later rows
run. The [machine-readable record](../../stoa-trace/ops/reports/source-recovery/development-studies.json)
distinguishes completed studies from work in progress. A timeout or nonanswer is
not silently excluded from a success rate.

Large source-audited counts and the dedicated route reader remain off by default
until accuracy and latency justify enabling them. The optional `STOA_COUNT_REFINEMENT=on` candidate proposes unclaimed source forms, audits every ID and flags unsupported old locators. It never accepts image-processing proposals as objects without semantic source review. Completed first-pass inventories and valid batch reviews resume privately; source/policy/code changes invalidate reuse. This remains off by default. The existing Gemini provider
and model policy is preserved. No fine-tuned detector or filename-specific
answer profile was enabled.

## Verification

472 backend tests passed on frozen backend source. The frontend-only chat follow-up
passed 60 tests and a fresh production build. A browser loaded the real saved
measurement from a copied development runtime, restored it once after refresh
and rendered its closed perimeter plus three separate opening polylines. No
model requests were allowed in that browser test. The original study runtime was
not modified.

Native solver files and the native-reachable analysis function are unchanged.
The full easy/native benchmark and both reserved evaluations were not rerun.
[Build hashes and checks](../../stoa-trace/ops/reports/source-recovery/build-checks.json)
and the [release compatibility gate](../../stoa-trace/ops/reports/source-recovery/release-validation.json)
do not certify general complex-drawing accuracy. Public
[research follow-up](../research/source-inspection-follow-up-2026-11-15.md)
records methods and the changed competitor implementation without copying code.

## Subsequent source-only count replay

Candidate `8043034` passed 481 backend tests. A retained earlier model inventory (323 located observations, no reference answer) was reexamined using the whole original school image. CPU discovery produced 80 locations, including one flagged empty old locator; four Carbon requests classified all IDs. The model rejected the empty locator and all proposed new forms, returning 322 candidates in 17.6 seconds. This is an object-location precision correction, **not** proof that 322 is the true total. Ambiguous desk/pedestal symbols are not forced into chair counts. The original 324 manual reference remains recorded and requires source adjudication. Cold API tests use fresh uploads and also include an already exposed external school control.

## Subsequent physical-role review and route controls

The staged source audit now checks every initial location before searching for
omissions. Original source legend crops provide class definitions and exclusions.
Named, bounded legend coordinates prevent Gemini's 0–1000 convention from being
mistaken for normalized page coordinates. Each retained or added object needs a
short physical qualification; a label such as Store does not establish a walk-in
room. Lift entrances can qualify without a swing arc, while shallow wall
cupboards remain excluded.

A frozen source-only replay (`e2e1cd6`) returned 322 school chairs, 113 passage
openings (including the lift), 68 exterior windows and 106 chairs on the external
Kelsey control. Four questions returned candidates with zero technical errors,
using 63 requests. These reuse retained, fallible first-pass model observations;
they are **not** four fresh end-to-end accuracy passes. The window reference and
Kelsey chair control agree; the school chair and full door totals still require
independent full-source adjudication. The five shallow cupboards falsely added
by the previous 119-door variant were inspected on source and are no longer
added. Earlier failures and false-positive variants remain recorded.

A separate cold route run completed all nine original piping zones in 229 seconds
with 19 Argon requests at low reasoning, returning 414.597 m. This establishes
response coverage and traced geometry, not exact full-network accuracy. A CPU
replay identified a 608.94-pixel estimated scale span versus the checkered bar's
actual 600-pixel edge-to-edge span; aligning the same paths produces 420.7745 m.
No reference length, expected total or model request participates in that
correction. Plain lines, text and multiple matching bars are deliberately not
snapped. Equipment-internal exclusions and completeness still require source
review; no full-network reference has been independently digitized.

On a separate, already exposed incoming-water-service drawing, the same cold
route policy returned 20.0780 m in 109.6 seconds (five model requests), within the
existing 20.0187 m ±0.6 m source reference. This is one visible route, not a whole
installed network or a hidden generalization benchmark. The refined 106-chair
external control also passes after reading its actual legend; the earlier
116-candidate regression remains recorded.

The frontend now offers Continue analysis for retained, recoverable inspections.
It resubmits the original question/page/selection without using the previous
answer as an operand. A real browser verified that payload against a copied
partial runtime with model requests disabled; the original and copied cumulative
counters both stayed at 18. Progress text uses actual completed source areas and
avoids repeating the same transport failure. No production study data was
modified by this UI check.

## Cold dedicated count profile

The frozen `5f61113` cold upload/API run returned 322 school chairs, 68 school windows and 106 external-control chairs. The door question returned no number because one of 16 tiles marked its owned scope incomplete despite describing out-of-core exclusions. This is three of four numerical responses, zero technical HTTP failures and 136 requests in the original summary, not a new general accuracy estimate. The source-only four-answer replay above did not predict this end-to-end failure. Local recovery and resumable incomplete-count handling are being implemented as a separate candidate; the failure is retained rather than overwritten.

Reviewed source `5f61113` is on main, deployed and loaded locally with the experimental modes still off by default. Verification preserved the production counter at 17/1,000 and local counters at 4/1,000 and 140/200, using zero model requests.


## Native-detail pipe coverage and local count recovery — 15 November

The follow-up adds bounded local recovery for incomplete count cores, with named
source coordinates and retained completed inspections. The cold original door
question now returns 111, but source comparison found a genuine storage-room
entrance wrongly excluded by the refinement pass. This is not a validated correct
count and does not justify promoting that experimental policy.

The opt-in route reader now reviews dense regions in four closer, overlapping
source details with disjoint measurement ownership. Each detail returns a full
replacement trace, including previously unmarked areas. Explicit equipment-body
polygons are subtracted by host geometry; adjacent bypasses are retained. Failed
closer reads preserve partial evidence, withhold the whole-network total and
resume only unfinished inspections. Method planning uses the meaning of a length
question rather than requiring the word “pipe”; unrelated length questions and
printed quantities delegate to the general source reader.

Backend validation passed 500 tests; frontend validation passed 64 tests and the
production build. Controls cover a previously missing branch, equipment cutouts,
shared boundaries and resumption after an interrupted closer inspection. The
external incoming-service development control returned 20.2429682746 m against
an already exposed manual reference of 20.018686381 m (about 1.12% difference).
The same question through the earlier generic source agent returned
20.0381763196 m in a separate run; retain both observations. Neither is evidence
that every pipe in the Discord network is recognized.

The whole-network study is recorded separately in
[the development record](../../stoa-trace/ops/reports/source-pipe-coverage/development-study.json),
including its completion status, failures and cumulative request count. No
reserved evaluation was opened or rerun. The deployed feature flags and provider
policies were not changed by this source update.

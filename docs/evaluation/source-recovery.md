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
| Carbon source-audited school chairs | 320; the earlier one-pass tiled reader returned 323, against an initial 324 clear-symbol reference | The new audit did not fix all misses and is not promoted. Eight ambiguous desk-pedestal shapes were not added to reach a target. |
| School baseboard with perimeter and explicit deductions | 29.7684 m, within the initial 0.6 m tolerance of the 29.189647 m source reference | A doorway deduction still follows a leaf rather than its full clear wall gap. Focused correction was added; exact geometry is not established by this result. |
| Original piping scale | Both model-proposed annotation boxes now reproduce the printed 8-foot reference through actual source OCR | A real calibration fix with zero model requests in the reproduction, not proof of the whole-network total. |
| Whole visible piping network | Earlier agent attempts failed source calibration; the corrected end-to-end run continues | No independently verified full-network accuracy is claimed. |

The first Argon audit study made 41 attempts: windows returned a number, while
chairs and doors had service errors. These failures remain recorded. Separate
Carbon count and corrected geometry studies have frozen code/configuration and
private raw artifacts; their completed rows are retained even while later rows
run. The [machine-readable record](../../stoa-trace/ops/reports/source-recovery/development-studies.json)
distinguishes completed studies from work in progress. A timeout or nonanswer is
not silently excluded from a success rate.

Large source-audited counts and the dedicated route reader remain off by default
until accuracy and latency justify enabling them. The existing Gemini provider
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

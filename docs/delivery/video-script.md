# Trace submission video

**Status:** storyboard and narration draft. No encoded video, measured duration, public viewing check or submission is established by this file. Target **1:55**, leaving five seconds below the recorded 2:00 maximum. The shot durations are estimates; time the actual take.

Record the verified Trace deployment or a clearly identified local build. Pin its revision and rehearsal result in [deployment verification](deployment-verification.md). Use only development drawings; check the reserved-group membership before filming. The examples below were already used in development and are not demonstrations on unseen test data.

## Storyboard and spoken script

| Time | Screen action | Narration |
| --- | --- | --- |
| 0:00-0:14 | Open directly on the real floor plan, with the room label visible. Brief title: Trace, MUSTA HELMI, Stoa. | "An engineer needs a quantity from a drawing, and needs to check where it came from. Trace connects the question, the calculation and the exact source evidence in one workspace." |
| 0:14-0:33 | On `site1102_bldg2242_floor10281.pdf`, ask the room 5.11 net-area question. Show 13.62 m² and click its evidence. | "Ask for the net floor area of room 5.11. Trace reads the source annotation and returns 13.62 square metres. Selecting the evidence brings us directly to the room and its printed value." |
| 0:33-0:53 | Enable comparison and ask the same question. Show printed annotation, calculated outline area and the scoped comparison. | "Here, a second calculation uses the registered CAD outline. Both values remain visible, with their methods and tolerance. The engineer can save a working quantity and the reason for choosing it. Agreement is a check, not a guarantee." |
| 0:53-1:13 | Show an existing verified saved count review, its original value and revision. If no genuine review is available, use the clearly labelled rehearsal procedure below. | "For counts, every included candidate is inspectable. A reviewer can exclude an extra object or mark a missed one, then save the revision. Trace preserves the original result, the change and the note, including after a reload." |
| 1:13-1:31 | Open usage details; repeat a question only if already rehearsed. Briefly show IFC GUID evidence or a schedule row. | "Supported native questions need no model call. Visual analysis can prepare a cached inventory for follow-up questions. Usage separates the current question from initial extraction, and unknown dollar cost stays unknown. BIM records keep their source identifiers too." |
| 1:31-1:46 | Show the compact full-preview metrics card below, including numeric denominator and native-only mode. Avoid scrolling through raw benchmark output. | "On the full preview, native answering covered 21 percent of questions with no model calls. The numeric result is shown here, including unanswered cases. This development score does not establish unseen-image accuracy." |
| 1:46-1:55 | Return to the selected source and reviewed value. Close on team/product name. | "Trace keeps the quantity, its source and the engineer's review connected as models improve." |

This narration is approximately 222 words, about 1:43 at 130 words per minute, leaving roughly twelve seconds for pauses within the 1:55 target. Screen actions run alongside narration. Shorten after rehearsal if needed; the final encoded file, not this estimate, determines compliance.

## Honest correction shot

Prefer a genuine detected mistake from a development drawing that a human has verified. Keep a short record of the original source, the observed error and why the correction is justified.

If no such case is available, use `site1102_bldg2242_floor10281.pdf` and its known native 13-window answer only as a **workflow rehearsal**. Label the temporary mark "Rehearsal mark, not a real missed window", explain that it demonstrates editing, and restore the original afterwards. Do not film an invented mark as a detection success or a real missed object. Show the explicit rehearsal label in the video, or omit this editing shot and show an existing saved review history.

## Measured metrics card

Use only results pinned to the code actually being presented. The card needs these fields:

| Field | Measured value |
| --- | --- |
| Code revision and evaluation mode | `d6f5b0c`, native mode |
| Population | All 7,990 preview questions, already exposed during development; not an unseen-file test |
| Answered / all questions | 1,682 / 7,990 (21.1%) |
| Correct numeric / all numeric questions | 1,598 / 7,725 (20.7%); unanswered cases count as incorrect |
| Correct numeric / answered numeric | 1,598 / 1,679 (95.2%); show coverage beside this figure |
| Text questions | 265 unscored text questions; three answered, requiring manual review |
| Model calls | Zero; this run does not exercise hosted vision or measure its accuracy |
| Model cost | No model inference in this run; hosting/storage and earlier extraction costs are separate |

Source: [full baseline summary](../../stoa-trace/ops/reports/riccardo-delivery/native-full-baseline-summary.md). If the filmed code revision changes, rerun the agreed evaluation and update the card before recording. Keep the native-only and development-data labels visible. The 48-group reserve was frozen prospectively after baseline exposure; do not call this result held-out accuracy.

The previous paired native diagnostic was **55/97 correct numeric questions**, from **58/100 answered**, with three numeric errors. Its earlier version had 41/97 correct. That is a small source-stratified diagnostic, not a full-corpus or general visual-accuracy claim. Do not show only the 94.8% answered precision while hiding coverage.

## Recording acceptance checklist

- [ ] Actual filmed revision and environment recorded.
- [ ] Every shown question rehearsed on that environment; scope and source match.
- [ ] No reserved test drawing opened before its permitted evaluation.
- [ ] A replay, cached result or rehearsal mark is identified accurately.
- [ ] Metrics and model usage copied from the same pinned report.
- [ ] No key, password, private file path, contact detail or provider dashboard shown.
- [ ] Final encoded duration measured at 120 seconds or less; target at most 115 seconds.
- [ ] Full video watched with audible speech and legible evidence.
- [ ] Authorized public viewing tested signed out, then its actual link entered in the submission.

Example duration check after a real file exists:

```sh
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 trace-submission.mp4
```

Keep a local copy of the final video and the source recording. A fallback recording is useful during the live demo, but call it a recording when used.

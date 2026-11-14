# Trace submission video

**Status:** storyboard and narration draft. No encoded video, measured duration, public viewing check or submission is established by this file. Target **1:55**, leaving five seconds below the recorded 2:00 maximum. The shot durations are estimates; time the actual take.

Record the verified Trace deployment or a clearly identified local build. Pin its revision and rehearsal result in [deployment verification](deployment-verification.md). Use only development drawings; check the reserved-group membership before filming. The examples below were already used in development and are not demonstrations on unseen test data.

## Storyboard and spoken script

| Time | Screen action | Narration |
| --- | --- | --- |
| 0:00-0:14 | Open directly on the real floor plan, with the room label visible. Brief title: Trace, MUSTA HELMI, Stoa. | "An engineer needs a quantity from a drawing, and needs to check where it came from. Trace connects the question, the calculation and the exact source evidence in one workspace." |
| 0:14-0:33 | On `site1102_bldg2242_floor10281.pdf`, ask the room 5.11 net-area question. Show 13.62 m² and click its evidence. | "Ask for the net floor area of room 5.11. Trace reads the source annotation and returns 13.62 square metres. Selecting the evidence brings us directly to the room and its printed value." |
| 0:33-0:55 | Open one rehearsed procedural development upload. Show its saved Gemini door answer and numbered evidence. Identify a cached replay visibly. | "For a supported image question, Gemini creates a reusable inventory of located objects. Trace counts those objects and puts each candidate back on the drawing. An optional Gemma review searches for missed or incorrect objects. That second pass remains a proposal an engineer can inspect." |
| 0:55-1:14 | Show an existing verified saved count review, its original value and revision. If no genuine review is available, use the clearly labelled rehearsal procedure below. | "A reviewer can exclude an extra object or mark a missed one, then save the revision. Trace preserves the original result, the change and the note, including after a reload." |
| 1:14-1:33 | Keep the session inference section and the selected answer's cost visible. Repeat a rehearsed identical question and show its cached cost. Briefly show source IDs if time permits. | "The workspace shows inference spending for this session and for every message. A cached repeat makes no new model call. Costs use model-specific token estimates, and missing usage stays unknown. Supported native answers need no model inference." |
| 1:33-1:46 | Show the compact development metrics card below, including numeric denominator and native-only mode. Avoid scrolling through raw benchmark output. | "Native mode answered 43 percent of development questions with no model calls. Six generated drawings also passed a small visual door-count check across six file formats. Neither result proves general accuracy on unseen plans." |
| 1:46-1:55 | Return to the selected source and reviewed value. Close on team/product name. | "Trace keeps the quantity, its source and the engineer's review connected as models improve." |

Time the narration with the actual screen recording and shorten after rehearsal. Screen actions run alongside narration. Avoid waiting for a new long-running model request in the two-minute video: identify a saved answer as a replay, or record the request and edit the waiting interval transparently. The final encoded file, not the storyboard timings, determines compliance.

The local six-format answer check used backend `b01af99`; the frontend quantity-label and icon update is `89cd4b8`. Neither reference proves that the existing remote deployment has been updated. Confirm the actual provider, Gemma setting and deployed revision before filming. Hosted Gemma must not be described as local, private or offline inference. Omit its narration if the final policy disables that optional review after evaluation.

## Honest correction shot

Prefer a genuine detected mistake from a development drawing that a human has verified. Keep a short record of the original source, the observed error and why the correction is justified.

If no such case is available, use `site1102_bldg2242_floor10281.pdf` and its known native 13-window answer only as a **workflow rehearsal**. Label the temporary mark "Rehearsal mark, not a real missed window", explain that it demonstrates editing, and restore the original afterwards. Do not film an invented mark as a detection success or a real missed object. Show the explicit rehearsal label in the video, or omit this editing shot and show an existing saved review history.

## Measured metrics card

Use only results pinned to the code actually being presented. The card needs these fields:

| Field | Measured value |
| --- | --- |
| Code revision and evaluation mode | Backend `b01af99`, native mode; frontend-only quantity/icon changes at `89cd4b8` |
| Population | 7,066 preview development questions; not an unseen-file test |
| Answered / all questions | 3,026 / 7,066 (42.8%) |
| Correct numeric / all numeric questions | 2,929 / 6,801 (43.1%); unanswered cases count as incorrect |
| Correct numeric / answered numeric | 2,929 / 3,023 (96.9%); show coverage beside this figure |
| Text questions | 265 unscored text questions; three answered, requiring manual review |
| Model calls | Zero; this run does not exercise hosted vision or measure its accuracy |
| Model cost | No model inference in this run; hosting/storage and earlier extraction costs are separate |

The local evaluator report was generated on 14 November at 09:51 UTC and uses development manifest SHA-256 `f5b772de621f06dc8c7dc8d9d83f0e99ab56a6488d2867f0a377eb6f42accb07`. It recorded zero request errors, 94 wrong numeric answers and 3,778 unanswered numeric questions. Retain that report and attach its sanitized aggregate to the release. The older [full baseline summary](../../stoa-trace/ops/reports/riccardo-delivery/native-full-baseline-summary.md) uses an earlier revision and a different denominator; do not present the two as a paired score. If inference code or policy changes, rerun the agreed evaluation and update the card before recording. Keep native-only and development-data labels visible. The 48-group reserve was frozen prospectively after baseline exposure; do not call this result held-out accuracy.

An optional second card can identify the small visual format check separately: **six generated development drawings, six door questions, 6/6 exact counts, zero request errors**, across PNG, JPEG, PDF, SVG, TIFF and WebP. The Gemini Carbon plus Gemma pipeline at `b01af99` matched reference objects with precision and recall 1.0 at one-to-one IoU 0.3. Twelve other questions in that procedural development corpus were unrun in this check. This measures a narrow format and evidence path, not general visual accuracy or a causal benefit from Gemma. The larger CubiCasa run and predeclared Gemma comparison were still in progress at this documentation update; insert only their completed, pinned and reviewed results later.

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

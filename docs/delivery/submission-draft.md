# Trace submission text

**Status:** copy draft, not a saved form, FINAL submission or confirmed acceptance. A read-only inspection on 14 November showed the platform project named **MUSTAHELMI**, in **Draft**, with punchline, description, challenge, demo, source and video fields blank. The page displayed **Closed** with a negative countdown, while the authenticated Guide still gives Sunday 15 November, 10:00 Helsinki as the final deadline. Resolve this discrepancy with current platform or organizer information. This document did not edit the form. Keep phone numbers and Discord details in the private form.

## Project name

Trace

## Punchline

Construction quantities you can trace back to the drawing, inspect and correct.

## Short description

Trace helps construction engineers answer questions about drawings and BIM models with inspectable source evidence. Native CAD, PDF and IFC tools calculate supported quantities from source records; visual analysis proposes located candidates when a supported native route is unavailable. Engineers can inspect the evidence, correct a count and retain the original answer and review history.

## Full description

Finding a number is only part of the job. An engineer also needs to know which room, object, schedule row or model property supports it. Trace brings the question, source and calculation into one workspace.

The application reads supported PDF text and schedules, semantic DXF geometry, IFC records and linked drawing views. It attempts constrained native calculations first. For other supported inputs, Gemini 4 Carbon can extract a reusable inventory of located visual candidates from the rendered drawing. Follow-up supported count questions operate on that inventory. An optional hosted Gemma 4 31B review searches again for missed or incorrect candidates; its effect is being evaluated. Counts derive from evidence objects. Unresolved filters, incompatible units, missing source values or different model/floor scopes should produce a limitation or an unanswered result rather than a silently broader total.

Selecting evidence opens the relevant source and focuses its region when registration exists. Engineers can add missed count candidates, exclude extras, undo draft edits and save a review note. Original machine results and saved revisions remain available after reload and export. Compatible independent quantities can be compared, with a reviewed working quantity recorded alongside both sources.

Immutable answer caches and reusable visual inventories reduce repeated model requests while preserving review isolation. The drawing workspace shows the current session's inference total and the cost of each message, including cached answers and known failed-call usage. Estimates use dated model-specific published rates or explicit configured rates. Missing usage or unsupported pricing stays unknown; hosting, storage and credits are separate. The interface uses free MIT-licensed BoardUI primitives with their attribution preserved.

Trace is designed to retain useful source extraction, geometry, scope controls and human review as frontier models improve. The current product does not promise reliable answers for every uploaded plan. Raster symbols, unfamiliar layouts, missing scale, comprehensive takeoffs and ambiguous source scopes remain limitations. Review is part of the workflow, not proof that every object was detected.

## Measured validation text

The latest local native-only development run, generated on 14 November at 09:51 UTC against the backend at `b01af99`, has the following results:

> Native mode answered 3,026 of 7,066 development questions (42.8% coverage), with zero model calls and zero request errors. It matched the supplied answers for 2,929 of 6,801 numeric questions (43.1%, including unanswered cases as failures), or 2,929 of 3,023 answered numeric questions (96.9%). There were 94 incorrect numeric answers and 3,778 unanswered numeric questions. The 265 text questions were not automatically scored; three were answered and require manual review. This preview has informed development. The result does not establish accuracy on unseen uploads or hosted visual analysis.

The local evaluator report uses development manifest SHA-256 `f5b772de621f06dc8c7dc8d9d83f0e99ab56a6488d2867f0a377eb6f42accb07`. The backend remained at `b01af99` during this run; `89cd4b8` subsequently changed frontend quantity labels and file icons. Retain the original report and publish its sanitized aggregate with the final release. The earlier [full native baseline](../../stoa-trace/ops/reports/riccardo-delivery/native-full-baseline-summary.md) covered all 7,990 preview questions at an older revision; its denominator and code differ, so it is not a paired improvement estimate.

The Gemini Carbon plus Gemma review pipeline also completed a small six-drawing procedural development check at backend `b01af99`: **6/6 exact door counts, zero request errors**, across PNG, JPEG, PDF, SVG, TIFF and WebP. Reference object matching had precision and recall of 1.0 at one-to-one IoU 0.3. This is a narrow format and evidence check on generated development drawings; it does not establish general door-detection accuracy, appliance recognition or arbitrary-file reliability. The other 12 questions in that development corpus were not part of this six-question check. The larger CubiCasa Gemini development evaluation and the predeclared Gemma door/window comparison were still running at this documentation update; no final score or measured Gemma benefit is asserted here.

The newly reserved 48 drawing groups contain 924 questions; the development portion contains 269 groups and 7,066 questions. No new reserved-subset score is asserted here. This reserve is a prospective quarantine, not an untouched historical test. Any genuinely unseen external-file test must be reported separately, with its scale assumptions, question count and manually checked evidence. SVG-annotation ceilings and calibrated development scores are not raster prediction accuracy.

## Challenge

Stoa: Make Blueprints Talk remains the main challenge. The checked briefs support prioritizing **Best Use of Gemini API** alongside it, with **Best Use of Gemma** conditional on a useful measured contribution. The same focused product can compete for the EUR 10,000 overall main prize, subject to all-member peer-review and submission requirements. See the [dated prize strategy](../research/stoa-prize-strategy.md) for official links, reward types and unresolved award-combination rules. These are recommendations, not saved challenge selections or guaranteed eligibility. Codex and Verda awards are credits rather than cash; avoid adding services solely to collect sponsor names.

## Technologies

Python, FastAPI, React, Vite, SQLite, PyMuPDF, ezdxf, Shapely, IfcOpenShell, Pillow, Gemini Interactions API with Gemini 4 Carbon, optional hosted Gemma 4 31B review, and free BoardUI primitives. The selectable OpenAI adapter remains available. Hosted Gemma is not local or offline inference. Verify which provider and policy are running in the actual filmed deployment before naming them as deployed. The separate historical model prototype is not part of the demonstrated Trace product.

## Links and artifacts

| Form field | Prepared value or remaining action |
| --- | --- |
| Demo | `https://stoa-86-38-182-146.sslip.io`; existing protected workspace. Verify current revision and agree organizer access securely. Do not place credentials in this document or a URL. |
| Source | `https://github.com/paranza/junction-2026`; confirm organizer access and the intended publicity setting. A private link alone is not proof of access. |
| Video | Pending a real encoded video, duration at most 2:00 and signed-out public viewing check. [Storyboard](video-script.md) is prepared. |
| Pitch deck PDF | Pending final artifact and render/readability check. |
| Team | MUSTA HELMI; verify all four members in the platform. |
| Licence | Team code has MIT licensing; preserve third-party terms. Organizer answer on PyMuPDF integration is pending in the question checklist. Do not state that every component is MIT. |
| Contacts and attribution | Complete privately in the platform. |
| Submission state | Draft named MUSTAHELMI observed read-only on 14 November; required fields above were blank. Closed status conflicts with the Guide and needs clarification. No FINAL confirmation. |

## Final release check

- [ ] Current source and demo revisions agree with the video and evaluation claims.
- [ ] Public video is actually viewable signed out and no longer than 2:00.
- [ ] Intended demo access works without exposing credentials.
- [ ] Organizers can access the source and the source-publicity field is deliberate.
- [ ] Pitch PDF opens and shows the final story and measured results.
- [ ] Team membership, licence entry, attribution and private contacts are complete.
- [ ] A human checks the actual platform form and any organizer updates.
- [ ] The observed Closed status versus Sunday deadline discrepancy is resolved, and all required fields and challenge selections are saved.
- [ ] Submission is set to FINAL and confirmation retained before **Sunday 15 November, 10:00 Europe/Helsinki**. Internal target: **09:00**.
- [ ] All teammates are available for peer review from 10:30 and through 14:00 while the end-time conflict remains unresolved.

This checklist is not permission to submit or publish. Confirm the external action in the active task before performing it and verify its result afterwards.

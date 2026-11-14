# Trace submission text

**Status:** copy draft, not a saved form, FINAL submission or confirmed acceptance. Check the current Junction Platform form before use; the recorded guide may have changed. Keep phone numbers and Discord details in the private form.

## Project name

Trace

## Punchline

Construction quantities you can trace back to the drawing, inspect and correct.

## Short description

Trace helps construction engineers answer questions about drawings and BIM models with inspectable source evidence. Native CAD, PDF and IFC tools calculate supported quantities from source records; visual analysis proposes located candidates when a supported native route is unavailable. Engineers can inspect the evidence, correct a count and retain the original answer and review history.

## Full description

Finding a number is only part of the job. An engineer also needs to know which room, object, schedule row or model property supports it. Trace brings the question, source and calculation into one workspace.

The application reads supported PDF text and schedules, semantic DXF geometry, IFC records and linked drawing views. It attempts constrained native calculations first and uses hosted visual analysis for other supported inputs. Counts derive from evidence objects. Unresolved filters, incompatible units, missing source values or different model/floor scopes should produce a limitation or an unanswered result rather than a silently broader total.

Selecting evidence opens the relevant source and focuses its region when registration exists. Engineers can add missed count candidates, exclude extras, undo draft edits and save a review note. Original machine results and saved revisions remain available after reload and export. Compatible independent quantities can be compared, with a reviewed working quantity recorded alongside both sources.

Immutable answer caches and reusable visual inventories reduce repeated model requests while preserving review isolation. Usage distinguishes current-question inference from initial visual extraction. Dollar cost is reported only when a supported cost basis is configured; hosting and storage are separate.

Trace is designed to retain useful source extraction, geometry, scope controls and human review as frontier models improve. The current product does not promise reliable answers for every uploaded plan. Raster symbols, unfamiliar layouts, missing scale, comprehensive takeoffs and ambiguous source scopes remain limitations. Review is part of the workflow, not proof that every object was detected.

## Measured validation text

Use the measured full-preview paragraph, with its scope and limitations intact:

> At code revision d6f5b0c, native mode answered 1,682 of all 7,990 preview questions (21.1% coverage) with zero model calls. It got 1,598 of 7,725 numeric questions correct (20.7% including unanswered cases), or 1,598 of 1,679 answered numeric questions (95.2%). The 265 text questions were not automatically scored; three were answered and require manual review. This preview has informed development. The result does not establish accuracy on unseen uploads or hosted visual analysis.

Source: [full native baseline summary](../../stoa-trace/ops/reports/riccardo-delivery/native-full-baseline-summary.md). It records per-source and per-language results; 4,270 CubiCasa raster questions received no native answers. Native coverage, rather than answered precision, is therefore the central measured gap.

An earlier paired 100-question source-stratified native diagnostic improved from 41/97 to 55/97 correct numeric answers, with 58/100 answered. It is a separate smaller sample and should not replace the full-preview denominator. No combined accuracy figure is appropriate.

The newly reserved 48 drawing groups contain 924 questions; the development portion contains 269 groups and 7,066 questions. No new reserved-subset score is asserted here. This reserve is a prospective quarantine, not an untouched historical test. Any genuinely unseen external-file test must be reported separately, with its scale assumptions, question count and manually checked evidence. SVG-annotation ceilings and calibrated development scores are not raster prediction accuracy.

## Challenge

Stoa: Make Blueprints Talk. Do not select an additional challenge unless its actual requirements have been checked.

## Technologies

Python, FastAPI, React, Vite, SQLite, PyMuPDF, ezdxf, Shapely, IfcOpenShell, Pillow and hosted OpenAI Responses vision. Name any additional model/checkpoint only if it is integrated into the submitted Trace revision and its role is clear. The separate model prototype is not automatically part of the demonstrated product.

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
| Submission state | Unverified. Prepared text does not establish DRAFT or FINAL. |

## Final release check

- [ ] Current source and demo revisions agree with the video and evaluation claims.
- [ ] Public video is actually viewable signed out and no longer than 2:00.
- [ ] Intended demo access works without exposing credentials.
- [ ] Organizers can access the source and the source-publicity field is deliberate.
- [ ] Pitch PDF opens and shows the final story and measured results.
- [ ] Team membership, licence entry, attribution and private contacts are complete.
- [ ] A human checks the actual platform form and any organizer updates.
- [ ] Submission is set to FINAL and confirmation retained before **Sunday 15 November, 10:00 Europe/Helsinki**. Internal target: **09:00**.
- [ ] All teammates are available for peer review from 10:30 and through 14:00 while the end-time conflict remains unresolved.

This checklist is not permission to submit or publish. Confirm the external action in the active task before performing it and verify its result afterwards.

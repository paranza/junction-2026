# Trace live demo and rehearsal

Owner: Riccardo. Intended product: `stoa-trace/`. Target a three-minute live flow, with the separate [submission video](video-script.md) kept below two minutes. This is a runbook, not evidence that the current deployment passed it.

## Before the room opens

1. Read [deployment verification](deployment-verification.md) and confirm the exact revision, protected URL and latest check. The existing VM must be reused; do not reset runtime or model-call counters.
2. Establish organizer access through the agreed secure channel. Never put the Basic password or provider key in a URL, screen recording, source, slide or chat. Verify intended access from a signed-out browser before submission.
3. Confirm the real dataset directory is present and available offline. Original files and extraction caches stay outside Git. Check the reserved-group policy before opening or querying any drawing; the familiar examples below belong to development.
4. Confirm the model-attempt allowance before any visual question. Native rehearsal uses zero model calls. An uncached visual question can spend credit even if the UI stops waiting. Use a known cached visual result if the budget cannot support another call; identify it as cached.
5. Open a clean workspace and a local fallback copy or recording. Check the display and browser zoom. Record actual rehearsal results and remaining issues; do not mark them passed from this checklist alone.

For the existing protected deployment, a non-model API exercise is available from `stoa-trace/`:

```sh
.venv/bin/python ops/verify_remote.py --exercise
```

This check does not establish that arbitrary uploaded raster drawings are accurate. Use the separate [generalization report](generalization-report.md) for that question. Do not add a restart during the presentation; coordinate the existing sync/start procedure before the rehearsal.

## Three-minute stage flow

| Time | Action | Observable result and explanation |
| --- | --- | --- |
| 0:00-0:20 | State the user problem and open the plan. | Engineers need a quantity and a quick way to verify it. No unsupported time-saving or accuracy percentage. |
| 0:20-1:00 | Search `site1102_bldg2242_floor10281.pdf`; ask "What is the net floor area of room 5.11 ('Stanza') in m²?" Click the evidence. | Source annotation 13.62 m², room focus and calculation. It is a familiar development example with a paired CAD source. |
| 1:00-1:30 | Enable comparison for the same question, inspect the outline and save a working quantity with a reason if rehearsed. | Both quantities/methods remain available; the engineer's choice does not rewrite the machine result. |
| 1:30-2:05 | Show a verified development count review and reload it. | Included/excluded/added evidence and revision history persist. If a synthetic rehearsal mark is used, label it as such and restore it. |
| 2:05-2:30 | Show native usage, saved answer reuse and one IFC source record. | Native inference used zero model calls; hosting is separate. GUID evidence does not imply a located 2D highlight where no registration exists. |
| 2:30-3:00 | Show the measured report card, state limitations and close. | Name the evaluation population and coverage. Explain that unknown images can fail and area needs reliable source quantities or scale. |

Keep the source visible while speaking. If interaction takes longer than planned, omit the IFC switch rather than rushing past the core evidence and correction flow.

## Development question bank

| Input | Question | Established rehearsal expectation | What it does not prove |
| --- | --- | --- | --- |
| `site1102_bldg2242_floor10281.pdf` | What is the net floor area of room 5.11 ('Stanza') in m²? | 13.62 m², native annotation and registered room evidence | General area measurement on an arbitrary screenshot |
| Same PDF | How many windows are drawn on this floor plan? | 13 native candidates; inspect rather than invent corrections | Detection recall on a new raster style |
| Xcel `A-801` schedule | On sheet A-801 of the Xcel Sports Complex drawings, what is the area of room 128 (Fieldhouse) in the finish room schedule? | 29,690 ft² and the source row | Every schedule layout or revision is supported |
| `ac20_arc.ifc` | How many doors are in the model? | 77 model objects, inspectable GUIDs | 77 visible doors on one floor or an as-built survey |
| `high_quality_architectural-10370.png` | How many windows are shown on this floor plan? | Previously a wrong visual count; use only as an explicit limitation/review example | A correct autonomous raster result |

The expectations above come from earlier verified development runs. Recheck them after current merges before recording. Do not train or tune on a reserved drawing just to keep this bank working.

## Count review restoration

1. Start from the original machine answer and note its answer ID.
2. Inspect each relevant candidate and the source scope.
3. For a genuine error, save the addition/exclusion and the evidence-based reason. For a rehearsal, use an unmistakable test label and do not call it a real source error.
4. Show original and reviewed counts, then reload and reopen the saved question.
5. Restore the original after any temporary rehearsal edit and save that revision. Export JSON to confirm the original and review history remain available.

## Failure handling

| Observed problem | Response |
| --- | --- |
| Model quota, timeout or unavailable key | Show the native flow or an identified cached answer. State that uncached visual analysis is unavailable; do not imply a live result. |
| Source changed warning | Recompute on the updated source before reviewing. Do not show stale highlights as current evidence. |
| Missing preview/registration | Open the original or inspect BIM properties. Explain the missing location instead of fabricating an overlay. |
| Wrong visual count | Inspect and correct it transparently. Preserve the machine result and explain that review is needed. |
| Missing dimensions/scale | Do not present m² from pixels as measured floor area. Ask for reliable scale or dimensions, or leave the quantity unanswered. |
| Network failure | Use the local build or a labelled recording. Identify the fallback. |

## Questions to prepare for

- **Is it hardcoded?** Native parsers use explicit source conventions, known layouts and question rules. They compute from source records; that differs from looking up supplied answer labels. The exact boundary and unknown-file checks are in the generalization report.
- **Can it read any Google floor plan?** It can accept supported uploads and attempt native/model analysis, but arbitrary symbol styles, resolution, language and missing scale can prevent a reliable answer. We do not claim universal plan understanding.
- **What did you train?** Separate the `Michele-testing/` model work from the demonstrated Trace path. Quote only model results with the input split, checkpoint and integration actually verified.
- **Why not a generic vision chat?** The persistent source inventory, constrained calculations, scope checks, evidence interaction, cached reuse and auditable review survive model changes. Other teams also use hybrid methods; do not claim exclusivity.
- **How much does it cost?** Give measured ingestion and follow-up usage separately. Unknown token pricing stays unknown; compute/storage are separate. Cached zero-call answering is not free initial extraction.
- **How good is it?** Report correct/all, answered/all and the evaluation population, with free text separate. Do not compare incompatible competitor headline percentages.

After rehearsal, record date, code revision, environment, questions exercised, actual outcomes, model calls, cost basis, restoration/export outcome and failures in the delivery status file.

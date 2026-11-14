# Stoa, organizer and access checklist

Prepared for Riccardo on **14 November 2026** from the Saturday plan. These questions have not been sent, answered or approved by virtue of being written here. No external contact was made to prepare this file. Record each human answer with its source, date, exact scope and resulting action in `docs/decisions.md`.

## Stoa booth: seven questions in priority order

| # | Question to ask | Status | Why it affects delivery |
| --- | --- | --- | --- |
| 1 | How is accuracy judged: a hidden question set run through our system, by URL or a batch file, the demo only, or both? At test time, do we get only `path` and `question`, or also `type`, `unit` and sibling files such as DXF, SVG or parent IFC? | Pending human answer | Determines the submission contract, batch-runner requirement and available source context. |
| 2 | How is inference cost judged: per question, per drawing or in total? Do cached calls count? | Pending human answer | Determines the reported denominator and whether to include initial ingestion in the judged cost. Keep both costs available regardless. |
| 3 | How are free-text answers graded, especially IFC-Bench and Opening Design text? | Pending human answer | Determines whether model-written text needs an automated judge, manual review or a different output contract. |
| 4 | The CubiCasa questions closely match the public CubiCasa5K annotations. May we train on CubiCasa5K, and are hidden test images part of that public corpus? | Pending human answer | Prevents training on hidden-test images or misrepresenting a model's generalization. The previously reported 98.6% annotation match is an annotation ceiling, not predicted raster accuracy. |
| 5 | For windows, do you count openings or panes? On sheets with several apartments, should the answer cover only a target apartment? | Pending human answer | Fixes the object definition and scope used for exact counting and visible evidence. |
| 6 | Are duplicate door and window records in Swiss Dwellings intentional for scoring? | Pending human answer | Determines whether geometrically duplicate source records should be counted or deduplicated. Do not silently rewrite the source. |
| 7 | Will the scans have questions? | Pending human answer | Determines whether to prioritize scanned drawings or focus on the currently labelled formats. |

Already recorded from Friday's partner discussion: keep the interface simple, visually show why an answer is correct and focus on a specific engineering quantity task. Do not treat that discussion as an answer to the seven questions above.

## Organizer licence question

**Pending human answer.** Ask: "Our team-authored code is MIT. The Trace application uses PyMuPDF, which is available under GNU AGPL v3 or an Artifex commercial licence. Is that dependency arrangement acceptable for this challenge's MIT/source-access submission rules, and what distribution/source obligations do you require us to meet for the submitted application and demo container?"

Take the current [third-party notices](../../stoa-trace/THIRD_PARTY_NOTICES.md) and the dependency list to the organizer. Record which option or requirement they actually confirm. This file does not resolve licence compatibility or establish a commercial licence. Do not remove required notices, call all dependencies MIT or change a core library solely on an assumed organizer requirement.

## Model access with Matteo

- [ ] Verify Matteo can use an authorized development key through private local configuration; never copy a key into chat, Git, screenshots or this document.
- [ ] Confirm the owner, spending allowance, provider limit and existing recorded-attempt cap before uncached visual testing. A runtime attempt limit is not a dollar budget.
- [ ] Verify the intended endpoint/model and a minimal authorized request, or record that access remains unavailable. A populated environment variable alone is not a successful model test.
- [ ] Preserve current runtime model counters; do not obtain another allowance by creating a fresh runtime.
- [ ] Agree who may run the CubiCasa bake-off and how cached results, first-ingest usage and token prices are recorded. Gemini credits are for the authorized bake-off in the plan, not a blanket new provider budget.
- [ ] Record readiness and limits without the credential value in the delivery status.

## Answer record template

```text
Question number / licence / model access:
Asked at (Europe/Helsinki):
Source or organizer role:
Answer, including limitations:
Evidence location (private if necessary):
Decision or required change:
Owner and due time:
Recorded in docs/decisions.md:
```

No answer is currently asserted in this checklist. If the response is ambiguous, retain the uncertainty and keep the dependent task conditional. In particular, implementing a useful batch interface does not establish that Stoa requested that format or that a submission was accepted.

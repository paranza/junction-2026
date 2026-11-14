# Stoa and technical challenge prize strategy

Evidence checked on **14 November 2026, approximately 11:30 Europe/Helsinki**. The authenticated Junction challenge pages were read in the participant's Chrome session. Public organizer and Google documentation were checked separately. This is an entry and implementation strategy, not a prediction of winning or a claim that prizes can be combined without restriction.

The existing project is Trace, entered for Stoa's **Make Blueprints Talk**. At the observation time, about 22.5 hours remained until the recorded Sunday 15 November, 10:00 Helsinki final deadline. Check the live submission form and organizer notices before submitting.

## Overall main prize and eligibility

The authenticated [Junction Guide](https://hackjunction.app/participate/45/guide), under Junction Rules, confirms a **EUR 10,000 overall main prize**. It permits submitting one project to multiple challenges and describes challenge prizes alongside the overall main prize. This supports entering Stoa and relevant technical challenges with the same project, while the detailed conditions for receiving several technical awards remain unresolved.

The overall winner is selected through live peer review to choose five finalists, followed by a stage pitch and grand-jury decision. All teammates must participate in the required live peer review for overall-prize eligibility. This makes a clear, reliable and visibly useful core product more important than collecting additional service integrations.

The Guide requires event-written project code, apart from open-source libraries, a team of one to four, at least one selected challenge and organizer access to source under the stated MIT requirement. Source history and dependency notices must support those conditions. This document does not infer a violation from a pre-event documentation or configuration commit.

## Main challenge criteria

The [authenticated Stoa brief](https://hackjunction.app/participate/45/challenges/335) assigns **25% each** to:

1. Accuracy.
2. Visualization of reasoning so a human can verify the answer.
3. Creativity.
4. Low inference cost.

The brief lists Stoa founding technical engineers and a construction engineer as judges. The supplied preview is approximately 0.5 GB, with a separate approximately 10 GB full dataset. Loading the preview does not establish that the full dataset has been tested.

The team's sponsor discussion also emphasized a simple interface and a specific construction-engineering task, especially metric or material measurements. That discussion is recorded in [challenge research](../challenges.md); it is separate from the four published scoring criteria.

Developer credits help run experiments. Production token consumption, model calls, latency and cost per answer still need measurement because low inference cost carries a quarter of the Stoa score. A provider credit balance is not a production unit-cost estimate.

## Cash prizes observed in the authenticated briefs

Amounts below preserve the original currency. Cash, credits, vouchers, hardware and work opportunities are different reward types.

| Challenge | Cash awards | Additional reward or qualification | Fit for Trace |
| --- | --- | --- | --- |
| [Overall Junction main prize](https://hackjunction.app/participate/45/guide) | EUR 10,000 | Peer-review finalist selection followed by grand-jury judging; required team participation. | Highest cash stake. A strong Stoa product can also compete here. |
| [Stoa: Make Blueprints Talk](https://hackjunction.app/participate/45/challenges/335) | First EUR 1,000; second EUR 750; third EUR 250 | First also lists a work-trial opportunity, which is not counted as cash. | Main entry. Focus on measured quantities and visible evidence. |
| [Best Use of Gemini API](https://hackjunction.app/participate/45/tech-challenges/48) | First EUR 4,000; second EUR 2,000; third EUR 1,000 | First also lists USD 1,000 Google Cloud credits per member. Meaningful, innovative and technically impressive Gemini use; open to any industry. | Highest immediate cash priority. Real visual blueprint recognition and source-grounded answers can serve both this and Stoa. |
| [Best Use of Gemma](https://hackjunction.app/participate/45/tech-challenges/47) | Three selected teams receive EUR 1,000 each, without ranked placements | Innovative and impactful use of Google's Gemma open models. | Strong conditional add-on if a genuine Gemma component improves extraction, audit or operating cost. |
| [Modal technical challenge](https://hackjunction.app/participate/45/tech-challenges/40) | First USD 2,000 | First also lists USD 3,000 credits. Modal must perform meaningful AI work such as GPU inference, sandboxing, fan-out computation or fine-tuning. | A substantive Gemma inference or document-processing component could fit if access and implementation time permit. |
| [Aiven technical challenge](https://hackjunction.app/participate/45/tech-challenges/43) | First EUR 1,000; second EUR 750; third EUR 500 | At least one Aiven service must be a core part of the project, alongside the main challenge. | A useful source-object search index or durable evidence/revision service could fit. Current local SQLite use alone does not qualify. |
| [Context.dev technical challenge](https://hackjunction.app/participate/45/tech-challenges/44) | First EUR 750; second EUR 250 | Live endpoint data must visibly drive the demo; identify the endpoints used. | A sourced material or product-datasheet lookup linked to measured quantities could fit. An unrelated search panel would be weak. |

The table describes prize terms observed at that time. It does not establish that the team is registered for each challenge, meets every condition, or can receive all awards cumulatively.

## Other observed rewards

| Challenge | Reward type | Implication |
| --- | --- | --- |
| [Codex development challenge](https://hackjunction.app/participate/45/tech-challenges/49) | First USD 10,000 API credits; second USD 5,000; third USD 2,500 | Meaningful Codex use in the development process can accompany any main challenge. Existing implementation, evaluation and review work may provide evidence. These are API credits, not cash. |
| [Verda technical challenge](https://hackjunction.app/participate/45/tech-challenges/56) | First USD 10,000 compute credits and hoodies; second and third USD 2,500 credits | Calls for ambitious computation that could not be built on a laptop and a process summary in Discord. The existing CPU-hosted app is useful infrastructure but does not by itself demonstrate the requested ambitious computation. No Discord message has been sent. |
| [Cloudinary technical challenge](https://hackjunction.app/participate/45/tech-challenges/41) | USD 500 Amazon gift card per team member | Requires use of at least one of the four listed tools and a separate form. These are restricted gift cards, not cash. |
| [Oxylabs technical challenge](https://hackjunction.app/participate/45/tech-challenges/32) | EUR 1,000 Apple gift voucher per team, plus USD 500 credits per member | Requires substantive runtime search or scraping with cited source data. Do not count the voucher as cash or as EUR 1,000 per member. |
| [NVIDIA technical challenge](https://hackjunction.app/participate/45/tech-challenges/46) | One RTX 5080 for each of two selected teams | Requires a core contribution from Nemotron 3.5 Super VL. Hardware is separate from cash. |

Workshop attendance, an available API key or a partner logo does not establish challenge eligibility. A working integration and the brief's required evidence are necessary.

## Recommended implementation order

### 1. Protect the overall main prize with a strong Stoa plus Gemini core entry

Finish real Gemini access verification and the raster evaluation before choosing a release model. Run development comparisons without reference answers entering inference. Record exact-count accuracy, measurement accuracy with the stated tolerance, unanswered answerable questions, object localization, latency, tokens and model calls separately. Freeze the chosen model and settings before releasing the reserved external evaluation.

Use one focused demo flow: upload a construction drawing, ask a door or room quantity question, inspect numbered source evidence and calculation, correct a candidate when necessary, and retain the original result and review history. A second quantity question can reuse the drawing inventory and show the saved inference cost. Every displayed success claim should correspond to an observed result.

This directly addresses all four Stoa criteria while showing substantive Gemini use. For the overall main prize, make the construction engineer's problem, saved work and visible result understandable to a general judge in one short demonstration. The EUR 10,000 overall prize is the highest single cash stake verified here, and Gemini is the largest listed add-on cash prize. Additional integrations should improve that same product and preserve the time needed for a reliable demo and pitch.

### 2. Add Gemma only in a useful, measured role

Google's current [hosted Gemma documentation](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api) lists `gemma-4-31b-it` and `gemma-4-26b-a4b-it` through the Gemini API, including image input. The [Interactions API reference](https://aistudio.google.com/api-reference/interactions-api) also lists both model IDs. A separate GPU account is therefore not necessarily required for a Gemma experiment, subject to actual model access and a successful image request with this account.

Possible useful roles are a cheaper first pass for categories where development results support it, or a diverse-model review of uncertain regions. Measure whether the role improves correct answers or lowers cost. Two models agreeing does not establish ground truth, and disagreement must not silently select whichever answer looks preferable. Hosted Gemma must not be described as local or offline inference.

Gemma's documented thinking settings are `high` and `minimal`; provider settings must match the selected model rather than assuming every Gemini setting is valid for Gemma. Hosted documentation is not proof of successful account access.

### 3. Consider one substantive infrastructure or data extension

If suitable credentials and time are already available, Modal could host actual Gemma GPU inference or a meaningful document-processing workload. That would combine a real open-model component with a compute component. A cosmetic remote wrapper around Gemini API calls is poor evidence of AI heavy lifting.

Aiven is useful if project-wide source/evidence retrieval or durable revision history is needed and implemented as a core feature. Preserve the working runtime and review history during any migration. Do not migrate the whole app solely to add a sponsor name.

Context.dev is useful when live, cited material or manufacturer data changes the engineer's result. Keep quantity computation grounded in the drawing and distinguish external specifications from observed drawing values. The demo must show which endpoint supplied the external information and how it affected the workflow.

Choose the extension that improves the same product most with the lowest implementation risk. Attempting all three creates several new service, access and failure dependencies before the deadline.

### 4. Record existing Codex work with minimal product scope

Prepare a concise, reproducible development account: meaningful implementation changes, independent fixture checks, development regressions, mistakes found and fixed, and the separation of reference labels from inference. Use actual commits and reports. Preserve credentials and private data. This supports the development-process challenge without adding another customer-facing feature.

## Entry permission and prize stacking

The [official Junction 2026 website](https://2026.hackjunction.com/) explicitly says tech challenges run across tracks and teams can take them alongside their track. It describes partner judging separately from the peer-review top five and grand-jury overall winner.

Permission to enter multiple categories does **not** establish all of the following:

- Whether there is a maximum number of tech selections in the final form.
- Whether a team can receive multiple cash awards for the same submitted project.
- Whether a particular sponsor excludes another sponsor's entry or requires a separate submission artifact.
- Whether the observed closed selection status concerns preliminary main-challenge choice or final technical entries.
- Any restrictions on receiving several technical awards together with a main-challenge or overall prize.

The public website advertises EUR 100,000 across the weekend and still states that a full prize breakdown is forthcoming. That aggregate is not a team-level cash award. The authenticated Guide separately confirms the EUR 10,000 main prize. The final form, individual award terms, current written rules or an organizer response must resolve the remaining selection and award-combination questions. No organizer message, additional challenge selection or separate form submission has been made as part of this research.

Purely as arithmetic, the first awards for Stoa, Gemini, Gemma, Aiven and Context total **EUR 7,750**, with Modal adding **USD 2,000**. Stoa plus Gemini alone totals EUR 5,000; adding Gemma makes EUR 6,000. Including the EUR 10,000 overall main prize would make the full arithmetic EUR 17,750 plus USD 2,000. The overall main prize plus Stoa and Gemini totals EUR 15,000 arithmetically; adding Gemma makes EUR 16,000. These are conditional combinations of listed awards, **not confirmed unrestricted stackable totals, winning probabilities or expected payouts**. Keep Google Cloud, Codex, Modal and Verda credits, gift cards, hardware and work opportunities outside those cash sums.

## Submission status requiring clarification

A read-only inspection of the actual project submission form on 14 November showed a **Closed** status with a negative countdown, while the project remained **Draft** and only its name was populated. The punchline, description, challenge, demo, source and video fields were blank. The Guide still states a Sunday 15 November, 10:00 submission deadline and requires FINAL status; it also permits edits before that deadline.

These observations are inconsistent enough to require current platform or organizer clarification. They do not by themselves prove that the team is disqualified or that the official deadline has passed. Confirm that the team can edit and finalize the intended submission before relying on the countdown or leaving the access question until Sunday. This research did not edit or submit the form.

## Submission and judging work that protects eligibility

The authenticated [Junction Guide](https://hackjunction.app/participate/45/guide), together with the supplied guide summaries in [event notes](../event.md) and the [submission checklist](../submission.md), requires the following to be verified against the live form:

- All four teammates joined the correct team and required challenge selections are saved.
- A working demo and source link are accessible to organizers. The currently protected deployment needs an actual organizer-access plan.
- A publicly viewable video is at most two minutes; measure the encoded file, not the script estimate.
- The pitch deck PDF opens and the project description identifies working features and measured limits.
- Private phone and contact fields are completed in the platform, and the project is set to FINAL before Sunday 10:00 Helsinki.
- Every teammate attends the assigned live peer review, which the supplied guide ties to overall-prize eligibility.

Prepared scripts and drafts are not uploaded artifacts or submitted entries. These delivery and access requirements can invalidate an otherwise strong product, so reserve time for them before adding optional integrations.

## Evidence scope

- Authenticated primary sources: the individual Junction links in the tables, the Stoa criteria link and [Junction Guide](https://hackjunction.app/participate/45/guide), observed in Chrome on 14 November 2026. The actual draft submission form was inspected read-only for status and field completion.
- Public primary source: [Junction 2026 event website](https://2026.hackjunction.com/) for co-entry context, schedule and judging structure.
- Public organizer announcement: [Junction's LinkedIn feed](https://uk.linkedin.com/company/hackjunction) confirms the Aiven best-use-platform challenge and Context.dev's open technical challenge. Its changing feed is supporting evidence, not a replacement for the individual briefs.
- Public technical primary sources: Google's hosted Gemma guide and Interactions API reference linked above. Actual service success still requires testing.
- Local supplied guide summaries are dated working notes and remain subordinate to current organizer instructions.

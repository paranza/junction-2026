# Public Stoa competitor refresh, Saturday evening

Research window: **14 November 2026, approximately 18:15-18:27 Europe/Helsinki (16:15-16:27 UTC)**. This assessment compares pinned public source with Metria main `1913388`. The [snapshot](stoa-competitor-snapshot.json) records HEADs, queries, classifications and observed live pages. The [morning snapshot](stoa-competitor-snapshot-2026-11-14-morning.json) and earlier assessments remain historical records.

## Assessment

Metria has competitive published numeric results, but chat, native geometry, evidence highlights and correction controls are now common. They are useful capabilities, not a distinctive pitch by themselves. Countersign has the strongest combination of measured raster work, confidence/review policy and source-conflict workflow in this review. OQVAR, Take-off check and PINPOINT have substantially stronger implementations than their earlier snapshots. Hologram has the broadest connected-device presentation among the inspected projects.

The morning advice that nobody scores IFC-Bench text, few teams handle schedules, and archive reading is untouched is obsolete. Several teams now implement or report these tasks. Likewise, Léargas and Blueprints Talk are no longer design-only or unconfirmed watchlist entries. OQVAR is the current name in lorikjashari/stoa, previously Plumbline.

We qualified **21 challenge-related, non-fork repositories**: 16 implemented source trees, two experimental repositories under one owner, one mock, one design and one starter. Two additional Stoa Takeoff forks are related work, not extra confirmed teams. A renamed repository has pivoted and one prior watchlist is unavailable. None of these counts establishes the number of registered Stoa teams.

## What we can actually open online

| Product | Public URL | Observed in this pass | Still unverified |
| --- | --- | --- | --- |
| Hologram / Stoa Pro | [Open](https://hologram-khaki.vercel.app/) | Chat shell, populated drawing choices and loaded Library skills. Public UI says Stoa Pro; repository says Hologram. | Fresh-upload extraction, paid/model Q&A, cross-device sync and physical AR. No question was submitted. |
| SpaceLens | [Open](https://junction26.github.io/SpaceLens/) | Landing page and built-in sample with 2D plan and loaded 3D controls. | Blueprint Q&A and arbitrary-upload performance. |
| Measure | [Open](https://stoa-eta.vercel.app/) | Real Swiss sample loaded, 21 numbered room boundaries, room 5.11 at 13.62 m² with units and coordinate formula. | Automatic understanding beyond its documented semantic DXF scope. |

These are browser observations, not just HTTP success codes. The text web reader could not fetch these sites, but the browser loaded them. No credentials, private file or question was sent to a competitor. Public demo links were not found for the other qualified projects after README/source/deployment-link research. That means **URL not located**, not **no deployment exists**. Fourteen GitHub deployment collections returned empty, including Hologram despite its known working public site, so that API is not a complete deployment inventory.

## Most relevant competitors and ideas

### Countersign: strongest measured verification workflow

[Current README](https://github.com/Hour49/Junction26/blob/c53eeaf6cd304172b47f29ad9f40113774e99aea/README.md) describes native and raster routes, located issues, a human double-check/sign-off flow and a limited building-code pre-check. Its current published raster result is **5,846/6,718 exact (87.0%) on 376 test pages through the API**. The CLI is slightly higher because it can use a kitchen prior; the README says uploaded files through the API do not. The separately defined golden set reports 2,717/2,948 correct (92.2%).

Their double-check policy reports 98.98% exact among unflagged answers while requesting review on 62.1% of answers. That illustrates a trade-off between precision and human workload, not 99% automatic coverage. Their [known issues](https://github.com/Hour49/Junction26/blob/c53eeaf6cd304172b47f29ad9f40113774e99aea/docs/KNOWN.md) explicitly describe raster area errors and poor hand-drawn door counting.

**Useful idea:** validate when to ask for review, and make the disputed object easy to inspect. For us, measure reviewer effort alongside correctness. Two matching Gemini readings are not independently verified evidence.

### OQVAR and Take-off check: specialist detectors and language planning

[OQVAR](https://github.com/lorikjashari/stoa/blob/b531ee3b3c5d3eb195f3f94632f862312017737e/README.md) reports **84.2% on 3,398 held-out raster questions**, native Swiss 99.49% and IFC 99.90%. Its fused YOLO readers use category-specific thresholds. Its new [live detection module](https://github.com/lorikjashari/stoa/blob/b531ee3b3c5d3eb195f3f94632f862312017737e/stoa_qa/cubicasa_live.py) runs on images without offline boxes, provided the weights and detection dependencies are installed. A deployment script does not establish that those dependencies are installed on a public service.

[Take-off check](https://github.com/NiceK1/stoa-spike/blob/77a9b3f7896a22cee640e4c8fef4fdb8d8edb285/app/README.md) combines detector counts with Sonnet inventories and a constrained planner. It reports **1,569/1,781 (88.1%)** across two raster samples, but voting was selected on sample A. The less selection-informed sample B is **760/865 (87.9%)**. Its paraphrase gains are development results. Windows remain weak.

**Useful idea:** use a small, domain-trained reader for repeated symbol counting, then a vision model for labels or unresolved regions. Compare each category on development data, including count-to-mark consistency, latency and model usage. Merely adding another model is not an accuracy improvement.

### PINPOINT, ProofPlan and Blueprints Talk: source reconciliation

[PINPOINT](https://github.com/tusbuh/junction-hackathon-2/blob/456b6ab95b55449bfe69de88ea2efadba82a8e1e/README.md) now has native quantity answers, schedule rows, drawing audits, BoQ exports and a raster ensemble. Its 3,124/4,270 raster preview score (73.2%) includes disclosed preview tuning and priors; native near-100% figures depend on semantic sources. Its cost estimates include a stated CPU-rate convention and should not be compared directly with hosted-token charges.

[ProofPlan](https://github.com/nia-soogm/proofplan/blob/53c375127a722124c976a7bb576f61885915c574/README.md) distinguishes a second-source check from a single-source answer. It has useful rotated schedule-cell extraction and CPU OCR, but refuses all its unsupported raster door/window/sink/shower classes. Its current near-100% native results include test-informed fixes, disclosed in its README. IFC-Bench text is measured and remains difficult.

[Blueprints Talk](https://github.com/Yue-fy/Junction_Hannah_family/blob/8a895c4e4a3c9679b5d75370d0eda7345d07c015/web/README.md) has a source graph, linked model/sheet highlights and an interface exposing drawing-versus-IFC discrepancies. Its [demo check](https://github.com/Yue-fy/Junction_Hannah_family/blob/8a895c4e4a3c9679b5d75370d0eda7345d07c015/demo/LIVE-CHECK.md) records 16/17 scored demo answers correct. A scripted tour is not an independent random benchmark.

**Useful idea:** expose exactly which source and scope contributed to an answer, and preserve conflicts. This is now shared competitive territory, so it needs better execution to distinguish Metria.

### Stoa Takeoff: quantity to purchase

[Stoa Takeoff](https://github.com/easyiowa/stoa-takeoff/blob/00e8e63ce44a0fef7262e339b58645bc42dc5281/README.md) extends quantities into supplier catalogue import, waste allowances, sale-unit conversion and an order PDF. Reviewer labels can create reusable signature rules. It reports native Swiss 99.3%, IFC 99.5% and raster 78.7% on official test plans. The [hosted bundle builder](https://github.com/easyiowa/stoa-takeoff/blob/00e8e63ce44a0fef7262e339b58645bc42dc5281/deploy/build_demo.py) ships pre-extracted drawings because full ingestion does not fit the serverless runtime. Its README says hosted reviews/rules reset with an instance restart.

**Useful idea:** a quantity should help complete a real construction task. A source-backed material summary or export is valuable. A new catalogue/purchasing feature is a larger scope choice and should not displace the current counting and reliability work.

### Hologram and SpaceLens: presentation breadth

[Hologram](https://github.com/Akshaz7/junction/blob/62f8a85f170ca5ab086e737f6f17c45a16563612/README.md) connects 2D/3D, phone/AR source, voice and reusable skills. Its public app loaded successfully. The pinned [accuracy report](https://github.com/Akshaz7/junction/blob/62f8a85f170ca5ab086e737f6f17c45a16563612/docs/ACCURACY.md) reports 124/187 numeric questions correct (66.3%) in its 200-question sample, with text separate. That result neither proves nor disproves arbitrary live-upload performance.

[SpaceLens](https://github.com/JUNCTION26/SpaceLens/blob/8d8ea00f2133c0ecd5a8683eef7710009934ac53/README.md) focuses on room design, layout constraints, routes, furniture and 3D experience. It is a different product emphasis. Metria should not expand into AR or room design simply because these make attractive demos; a visibly correct engineering quantity is closer to our current product and the partner discussion.

## Where Metria stands

Our [published end-to-end report](../evaluation/end-to-end.md) at `d0c9fcd` records **7,218/7,725 numeric preview answers correct (93.4%)**: Swiss 2,358/2,358, IFC 1,029/1,049, schedules 35/48 and raster 3,796/4,270 (88.9%). It excludes 265 free-text questions and includes development-exposed data. The 54 raster plans separated during prompt development scored **425/482 (88.2%)** through our application API. That subset had already been evaluated previously, so the application run is a replication, not a new independent reserve. English/Finnish twins share inventories and are correlated.

Those numbers are more relevant than our older 78.1% visual-development run. They also cannot be ranked against another team's golden set, full native set or different raster split. We have not shown 99.9% general accuracy or that we lead the challenge.

Main `1913388` subsequently adds the chat, UI and registered-region recovery. Its [verification](../delivery/chat-and-region-recovery.md) records 338 Python tests, 54 frontend tests, a build and **zero previously correct regressions across 7,066 native-mode development cases**, without model calls. That guard is not a fresh end-to-end visual accuracy measurement. The separate 924-question prospective reserve was not scored or inspected in this pass. Neither was the consumed independent upload corpus rerun.

Metria already has persistent plan chats, generic Gemini-backed native query planning with Python arithmetic, registered DXF region queries, native/source evidence, manual add/exclude review, revision history, export, Cloudinary close-ups and a real Spending view. Many of these capabilities have competitors. Our largest practical risks are:

- **Raster windows and doors.** In the published preview run, windows are 246/482 (51.0%) and doors 262/352 (74.4%). Together their 326 misses are **64.3% of all 507 numeric misses**. These figures include translation pairs.
- **General questions and text.** The typed planner supports count/value/sum/min/max/mean and source-field filters. Grouping, ratios, cross-table joins and arbitrary spatial reasoning are not generally established. Free text has no full scored result.
- **Cost and time.** The end-to-end run attempted 482 model readings for 241 raster plans. Repeated same-model readings flagged disagreement but did not improve the count rule in development. Argon dollar prices were not established in the report. One drawing failed both readings; model wait time and recovery matter to judges.
- **Runtime reliability.** We fixed an actual frontend/backend version mismatch, stale chat state, image-load races and region registration. The final demonstration must exercise the exact deployed URL and backend revision. A local fix does not prove production is updated.
- **Evidence correctness.** Valid boxes and a correct total do not prove every marked object is the requested class or in scope. Source IDs, geometric registration and semantic truth require separate checks.

## Improvements ranked for the remaining time

These are recommendations, not changes implemented by this research pass. The recorded final deadline is Sunday 10:00 Helsinki; at this research point roughly 15.5 hours remain. The team workflow [challenge-fit](../../.agents/skills/challenge-fit/SKILL.md) and [earlier checked Stoa brief](stoa-prize-strategy.md#main-challenge-criteria) support focusing on accuracy, visible reasoning, creativity and inference cost rather than adding unrelated screens.

| Priority | Improvement | Reusable competitor idea | Reviewable completion criterion |
| --- | --- | --- | --- |
| 1 | Improve missed windows and doors on new images | OQVAR/Take-off check specialist detector plus category-specific selection | Frozen development comparison: exact count, one-to-one evidence, unchanged previously correct cases, latency and request usage. No filename/gold lookup. New independent test only after policy freeze. |
| 2 | Make question and region interpretation inspectable in the existing chat artifact | Constrained planners across OQVAR, Take-off check and Blueprints Talk | Show a short interpretation when it changes scope. Test novel wording, exclusions, units, page/region boundaries and follow-ups. Extend typed operations only where source records support them; ask a focused clarification for unresolved intent. |
| 3 | Complete a correction in seconds | Countersign review policy and our existing review trail | Click a disputed door, correct inclusion, recompute the answer, export the same revision, reload and retain it. No duplicate panels or new navigation. Record median human verification/correction time on development drawings. |
| 4 | Strengthen real schedule and material questions | Drawing Desk cross-sheet tools, PINPOINT/ProofPlan schedule cells | Parse columns and units into typed rows, distinguish sum of Qty from row count, link every operand to its page/cell, abstain on unsupported joins. Test on development files beyond one demo sheet. |
| 5 | Reduce repeated inference where it adds no value | Cached detector inventories and cheap native arithmetic | A development ablation must show the effect on errors, flags, cold/warm latency and attempts per drawing. Keep the configured production policy until a measured replacement is reviewed. Do not call credits zero operating cost. |
| 6 | Freeze and rehearse the exact deployed flow | Competitor deployment checks and our recovery experience | New browser session, genuinely new supported upload, paraphrased/region question, readable highlights, correction/export and reload. Confirm real backend revision and persistence. Native-source, image-only and unavailable-data paths must all be clear. |

The best positioning to pursue is **a construction quantity that the engineer can check and correct immediately, even on a fresh upload and a selected part of the plan**. The combination exists in parts elsewhere. Our differentiator has to be the demonstrated quality, scope correctness, speed and durable result, rather than claiming that chat or highlights are unique.

A compact demonstration can show: fresh upload, natural question, selected-region follow-up, evidence, one correction and a retained/exported result. Use an image-only drawing for the visual part so a matching CAD twin cannot silently make it look like image understanding. If an answer uses a native twin, disclose that in the evidence.

## Complete qualified repository map

“Implemented” means relevant implementation is present in inspected public source. It does not mean we ran it or verified a working deployment. Source links are pinned; more commits may arrive after the research window.

| Project and public source | Classification | What it does differently | Website status |
| --- | --- | --- | --- |
| [Countersign](https://github.com/Hour49/Junction26/blob/c53eeaf6cd304172b47f29ad9f40113774e99aea/README.md)<br>`Hour49/Junction26` | implemented | YOLO detectors and room reader, source conflicts, review/sign-off, located issue export and limited code pre-checks. Broadest measured workflow in this review. | No public app URL found. |
| [OQVAR (formerly Plumbline)](https://github.com/lorikjashari/stoa/blob/b531ee3b3c5d3eb195f3f94632f862312017737e/README.md)<br>`lorikjashari/stoa` | implemented | Native geometry plus a constrained query planner, fused YOLO detectors with per-category validation thresholds, linked 2D/3D and live detection on new uploads. | Modal deployment script; no published app URL found. |
| [Hologram / Stoa Pro](https://github.com/Akshaz7/junction/blob/62f8a85f170ca5ab086e737f6f17c45a16563612/README.md)<br>`Akshaz7/junction` | implemented | Linked plan maps, browser 2D/3D, phone/AR source, voice and reusable skills. Public frontend is branded Stoa Pro; repository calls it Hologram. | [Live UI](https://hologram-khaki.vercel.app/). Library data loaded; Q&A not exercised. |
| [Take-off check](https://github.com/NiceK1/stoa-spike/blob/77a9b3f7896a22cee640e4c8fef4fdb8d8edb285/README.md)<br>`NiceK1/stoa-spike` | implemented | TypeScript app now combines native solvers, detector/vision voting, PDF text tools and a planner for paraphrases. It is no longer just a Python spike. | No public app URL found. |
| [Stoa Takeoff](https://github.com/easyiowa/stoa-takeoff/blob/00e8e63ce44a0fef7262e339b58645bc42dc5281/README.md)<br>`easyiowa/stoa-takeoff` | implemented | Building model, query planner, trained raster detector, review-to-rule learning, supplier catalogue import and order PDF with waste and sales-unit conversion. | Hosted Vercel bundle documented; no public URL found. |
| [PINPOINT / AIRAM](https://github.com/tusbuh/junction-hackathon-2/blob/456b6ab95b55449bfe69de88ea2efadba82a8e1e/README.md)<br>`tusbuh/junction-hackathon-2` | implemented | Native geometry, schedule rows, trained raster ensemble, 2D/3D evidence, drawing audit and BoQ exports. Optional language model rewrites questions rather than answers. | No public app URL found. |
| [Blueprints Talk](https://github.com/Yue-fy/Junction_Hannah_family/blob/8a895c4e4a3c9679b5d75370d0eda7345d07c015/README.md)<br>`Yue-fy/Junction_Hannah_family` | implemented | Full Stoa pipeline now present, with linked 2D/3D, source knowledge graph and drawing-versus-model discrepancies. Earlier watchlist-only classification is obsolete. | No public app URL found. |
| [ProofPlan](https://github.com/nia-soogm/proofplan/blob/53c375127a722124c976a7bb576f61885915c574/README.md)<br>`nia-soogm/proofplan` | implemented | CPU-only native parsing, PDF schedule cells, OCR labels, cross-check status and abstention gates; no model API needed for its implemented route. | No public app URL found. |
| [Léargas](https://github.com/markmannion/leargas/blob/08530debf9d6c44ba9983f576c7fa23715afb5a9/README.md)<br>`markmannion/leargas` | implemented | Now an application: native CAD/BIM, high-resolution sheet reader, OCR and scale/area measurement, fine-tuned Gemma raster reader, region and voice support. | No public app URL found. |
| [Stoa](https://github.com/chaowang0524/metsatalo-stoa/blob/39ef889c23ac9d0fb00530f1ba63489741daf715/README.md)<br>`chaowang0524/metsatalo-stoa` | implemented | Deterministic IFC/DXF/PDF tools with LLM routing; now a UI with CAD SVG overlays, visual inventories, saved edits, symbol placement and image-generated isometric views. | No public app URL found. |
| [Trace engine](https://github.com/13032585789-spec/Trace/blob/3c424f9ea7226a828a19a4b52160daa3991b20a6/README.md)<br>`13032585789-spec/Trace` | implemented | Native engine plus cached visual inventories, new free-query and historic-scan reading modules, boxed counts and disagreement from two readings. Some fallback paths use priors. | No public app URL found; no frontend in inspected tree. |
| [Drawing Desk](https://github.com/aapolipponen/drawing-desk/blob/072608f95db03ee3d49c3ece243169c65eb46921/README.md)<br>`aapolipponen/drawing-desk` | implemented | Claude tool loop over native quantities and sheet evidence, cross-sheet door-to-schedule demonstration and deliberate refusal. Public repo head unchanged. | Hostinger deployment instructions; no public app URL found. |
| [SpaceLens](https://github.com/JUNCTION26/SpaceLens/blob/8d8ea00f2133c0ecd5a8683eef7710009934ac53/README.md)<br>`JUNCTION26/SpaceLens` | implemented | Broader spatial design product: room capture, layout constraints, independent geometric checks, furniture/routes, walkthrough and exports; drawing Q&A is one feature. | [Live UI](https://junction26.github.io/SpaceLens/). Sample 2D/3D workspace loaded. |
| [Measure](https://github.com/13shreyansh/stoa-measure/blob/78d878fdd3cc42f07b9524610981109d97a30803/README.md)<br>`13shreyansh/stoa-measure` | implemented | Focused browser-only semantic DXF room calculations and boundary export, with manual PDF/image tracing. Narrower capability but a clear source-to-result explanation. | [Live UI](https://stoa-eta.vercel.app/). Native sample result loaded. |
| [Stoa Drawing QA](https://github.com/nguyenminhduc07/Stoa/blob/cf81d9e300998e9f22e2b8a157e324adb25ecbdf/DECISIONS.md)<br>`nguyenminhduc07/Stoa` | implemented | Conversation-scoped lazy ingestion and cached parsers, semantic DXF/IFC solvers, OCR room labels and optional pretrained floor-plan segmentation. Session metadata is in process memory. | No public app URL found. |
| [ChatChTG](https://github.com/d-malkov-iprally/ChatChTG/blob/8dd0bfdcd5de006416e3fec40176abad97825d3d/README.md)<br>`d-malkov-iprally/ChatChTG` | implemented | Plain multimodal LLM baseline plus a new detector comparison demo using GroundingDINO, SAM 3 and CubiCasa segmentation. The detector demo is separate from document/LLM answering. | Local Streamlit launch documented; no public app URL found. |
| [Room segmentation and symbol detection](https://github.com/AistisV/yolo-segmentation-testing/blob/95bfca94343592790f1f7437b017c35493fec364/README.md)<br>`AistisV/yolo-segmentation-testing` | experiment | U-Net room masks, tiled YOLO symbols, Gemini labels and measured scale bars. Reports substantial Swiss raster gains but explicitly says messy low-resolution CubiCasa is not yet working. | No public app URL found. |
| [Floor-plan schematic RL environment](https://github.com/AistisV/reinforcement-testing/blob/c4ea5606095a2538067afd215499f3c9117b6fc7/README.md)<br>`AistisV/reinforcement-testing` | experiment | Image-to-schematic JSON with geometry-based answer scoring and reward, Qwen SFT and tiled experiments. Same public owner as the segmentation repository, not an extra confirmed team. | No public app URL found. |
| [Brain / Face prototype](https://github.com/Georgia-coderok/okstoa-try1/blob/a0d0bf1328a1ac40547095e12fadda868b950ac0/code/brain_starter.py)<br>`Georgia-coderok/okstoa-try1` | mock | Claude tool loop and simple frontend, but current brain starter still builds an explicit mock SQLite database. Real drawing ingestion was not established. | Frontend source; no public app URL found. |
| [PlanGraph design](https://github.com/lalashutosh/blueprint/blob/2335744410fb77c339a9897116d3772c2825c441/README.md)<br>`lalashutosh/blueprint` | design | One-time scene reconstruction, exact query operations and correction ideas are documented. Four-file tree remains design material rather than an implemented app. | No public app URL found. |
| [Team MATT starter](https://github.com/ThangVuH/hackathon-finland-nov2026/blob/1869ea475a4addba1c04b1e68457743047490536/README.md)<br>`ThangVuH/hackathon-finland-nov2026` | scaffold | Challenge title, dataset overview notebook and Python starter. No answering product established from the inspected tree. | No public app URL found. |
| [Stoa Takeoff fork](https://github.com/HandanMajied2024/stoa-takeoff/blob/fd788617915ccd2a9e99ce19ac6330f89b3dd985/README.md)<br>`HandanMajied2024/stoa-takeoff` | fork | Fork of easyiowa/stoa-takeoff with deployment-bundle work. Do not count as a separate registered team. | No public app URL found. |
| [Stoa Takeoff fork](https://github.com/Beastolero/stoa-takeoff/blob/6df0e8041d7bc42d2be160d7683eeaabb5d045a5/README.md)<br>`Beastolero/stoa-takeoff` | fork | Fork of easyiowa/stoa-takeoff with room-model work. Do not count as a separate registered team. | No public app URL found. |
| [NeuralDoc; formerly tstst334/junction](https://github.com/JAPARK10/junction/blob/fed7a9405562bdd49685a58e9c5d4a2ad3e0f6de/meta/document-writing/README.md)<br>`JAPARK10/junction` | excluded | Same repository ID as the old tstst334/junction seed, now renamed. Current source implements a Meta Ray-Ban document/wrist-sketch app, so a stale Stoa description does not prove current competition relevance. | GitHub Pages configuration present; not counted as Stoa demo. |
| [Previous watchlist](https://github.com/cufelix/hackjunction)<br>`cufelix/hackjunction` | unavailable | Previously an event knowledgebase. Current public access could not be established. A 404 does not prove deletion or a private implementation. | Repository API returned 404. |

## Discovery and verification method

- Refreshed all 15 earlier seeds through public metadata and default-branch commits, followed the renamed seed by repository ID, then read pinned READMEs and relevant implementation files.
- Ran 14 GitHub repository searches covering exact challenge title, Stoa/Junction, recent creation, IFC, raster, CubiCasa, Swiss Dwellings and takeoff. Broad queries reaching 100 matches were marked as potentially truncated. Narrowed `fork:false` searches reduce unrelated fork noise; they do not make coverage exhaustive.
- Queried source for public deployment domains and read deployment documentation/configuration. Public GitHub code search sometimes returned 429; targeted retries succeeded. An initial invalid combined code query was discarded. The snapshot records coverage limits.
- GitHub's connector rejected its `/readme` and `/deployments` routes. Pinned raw-file reads supplied READMEs; the GitHub CLI supplied read-only deployment collections for 14 relevant repositories, all empty. Empty collections are not evidence that a site is absent.
- General web searches did not add a corroborated current Stoa deployment. Unrelated historical companies, architecture sites, Neovim Stoa, transcriptomics Stoat and generic blueprint repositories were excluded.
- Three public demo URLs were loaded in the browser. No competitor source, weights or dataset was executed or copied into our repository; no private repositories, contacts or credentials were accessed. No model requests, reserve scoring, registration, submission or message to another team was made.

The public web cannot enumerate private teams, unindexed commits, unpublished URLs or every non-default branch. This is a source-backed public landscape, not a complete official entry list.

# Decisions

## Agreed context

| Item | Decision or status |
| --- | --- |
| Team | MUSTA HELMI, four people |
| Event | Junction 2026, European Tech Renaissance |
| Repository | paranza/junction-2026 |
| Foundation | Stack-neutral documentation, shared agent instructions and small team skills |
| Collaboration default | Short task branches, pull requests, one task owner |
| License | MIT for team-authored content, matching the supplied submission rules |
| Challenge | Make Blueprints Talk, selected after discussion with the partner at the event |
| Product and stack | Trace in `stoa-trace/`: FastAPI/Python, React/Vite, SQLite, native PDF/DXF/IFC extraction, selectable Gemini/OpenAI vision and optional hosted Gemma review. Local Gemini access and structured image inference have been tested; confirm the current deployed provider separately. |
| Deployment | Existing protected HTTPS deployment on one Verda CPU VM. Coordinate with its owner; credentials are outside Git. |
| Credits | OpenAI inference and Verda funding were verified by the prototype owner. The user supplied a private Gemini key and authorized mass evaluation. Account secrets and credit entitlements do not transfer with this repository; production inference cost remains a Stoa criterion. |
| Team members and task owners | Assign together; personal contact details go in the event platform |

## Decision log

### 2026-11-13: initialize the team foundation

Create documentation and configuration from the supplied guide and screenshot. Keep inferred challenge themes labeled. Defer product code, dependency installation, CI build commands and provider-specific integrations until the official start and challenge selection.

For later entries, record: date, decision, reason, owner and the evidence or constraint that could change it.

### 2026-11-13: select Make Blueprints Talk and focus on measurements

Select the STOA challenge after the team's event discussion with the partner. Focus the product on a specific construction-engineering task, especially metric or material measurements, and make the evidence behind each answer clear in a simple visualization. The partner reported that its internal model performs poorly but could not share details. Vision models for rapid image-based answers are a team hypothesis, not a partner recommendation. Keep the technical stack open until the team chooses an implementation.

### 2026-11-14: hand off the working Trace prototype

At the prototype owner's request, place the application under `stoa-trace/` on `codex/stoa-trace-handoff`, preserving the existing team foundation. The implemented route uses native source records and constrained calculations first, with a hosted OpenAI vision fallback, evidence overlays and saved review state. It uses one existing Verda CPU VM and SQLite; no trained segmentation model or GPU is deployed.

`INFRA/architecture_pipeline.md` remains an earlier proposal. Its combined CenterNet/SAM2/Gemini pipeline and accuracy claims were not implemented or established by this handoff. Later Gemini provider work is recorded below and does not establish that earlier pipeline. The frozen diagnostic and vision reports under `stoa-trace/ops/reports/` record the actual measured coverage and limits. Read `stoa-trace/HANDOFF.md` before deciding the next implementation slice. Owner: the teammate handing off Trace; merging and shared deployment changes remain coordinated team actions.

### 2026-11-14: strengthen source verification and the quantity review workflow

Implement typed source-operand checks, strict unresolved-constraint handling, Swiss CAD compatibility and supported IFC quantities. Reuse versioned visual inventories and answers, record request usage with unknown dollar costs unless configured, and preserve original machine results alongside manual count revisions and reviewed working quantities. Reject unresolved model/view scope comparisons. Evaluate native changes on the same frozen 100-question sample, disjoint from the original diagnostic groups; do not present the stratified result as a competition score. Keep the existing deployment and runtime unchanged during local verification.

### 2026-11-14: add a raster specialist app with our own PyTorch models (`Michele-testing/`)

On branch `feat/blueprint-analyzer`, add a separate FastAPI app (port 9999) whose raster models are trained by us in plain PyTorch: PlanNet (U-Net segmentation plus CenterNet-style object heatmaps) and GlyphNet (CRNN text reader). Training labels come from the Swiss Dwellings DXF projected onto the PNGs and from CubiCasa5K SVG annotations; the preview's own plans stay held out. Questions are answered by deterministic multilingual templates over the extracted facts; Gemini flash-lite is a fallback over text facts only. Reason: the partner asked for accurate, visibly justified measurements at low inference cost, and `stoa-trace` reports 0 % coverage on CubiCasa raster plans. Details and measured results: `Michele-testing/docs/`. Owner: the teammate running the overnight build; integration with `stoa-trace` is a team decision.

### 2026-11-14: remove `Michele-testing/` and build only in Trace

The team works on one product, Trace (`stoa-trace/`). The separate raster app is removed from main. Its useful parts are ported into Trace under the Saturday plan: the Swiss DXF rules (`vector_dxf.py`) into the native solvers and the multilingual templates (`questions.py`) into the normalizer. The code, weights and docs remain in history at commit `a4bd811`. Owner: Michele.

### 2026-11-14: selectable Gemini provider and unknown-upload quality

The user requested switching the hosted model to Gemini and prioritized general performance on answerable drawing questions over scoreboard messages and video work. Trace keeps native extraction, deterministic calculations, evidence mapping and review history, with a Gemini Interactions adapter behind the existing model interface. The private key was successfully checked for model access and actual structured image inference. Development policy uses `gemini-4-carbon`, high image resolution, medium thinking, a 24,000-token output limit and a 600-second request timeout. The original high-thinking run exhausted its output budget; its errors remain in the evaluation record, rather than being hidden by retries. A larger frozen development run is still in progress. Production activation remains subject to its actual deployment and verification. No claim of 99.9% accuracy is made without measurement. Owner: Riccardo integration.

### 2026-11-14: optional Gemma review and bounded evidence

Add per-request hosted `gemma-4-31b-it` review without mutating the base provider or its reusable inventory. The reviewer uses minimal thinking and a schema constrained to the supplied image indexes and normalized coordinates; invalid evidence is rejected. Retain the original detection alongside any proposed revision. Two models agreeing is not ground truth, and hosted Gemma is not offline inference. The local pipeline at backend `b01af99` answered six procedural development door questions correctly across PNG, JPEG, PDF, SVG, TIFF and WebP, with zero request errors; this narrow format check does not establish a general accuracy rate or a causal Gemma benefit. A predeclared door/window development comparison is still running and will determine whether the optional review is useful. Owner: Riccardo integration.

### 2026-11-14: drawing workspace polish and session inference costs

At the user's request, remove the extra model provenance panel and refine the drawing workspace using free MIT-licensed BoardUI Button and Divider primitives with attribution preserved. Show inference spending for the current browser-tab session and for every message. Correlate actual model-attempt events with message and session identifiers; include known failed-call usage, preserve unknown usage and price cases, and avoid charging cached inventory or repeated answers twice. Prices are dated model-specific estimates before credits, separate from hosting and provider invoices. The paid-answer, cached-repeat and reload flows have been exercised in the local browser. Owner: Riccardo integration.

### 2026-11-14: prize and submission priorities

The checked Stoa brief gives equal weight to accuracy, visible verification, creativity and low inference cost. Keep one focused Stoa product and investigate meaningful Gemini and conditional Gemma entries, while preserving overall-main-prize eligibility through required all-member peer review. The [dated prize strategy](research/stoa-prize-strategy.md) separates cash from credits, vouchers and hardware. Multiple entries are permitted; unrestricted cumulative awards are not established. This is an implementation recommendation, not proof that additional selections were saved. A read-only platform inspection showed Draft MUSTAHELMI with required fields blank and a Closed countdown inconsistent with the Guide's Sunday deadline. Resolve that status before relying on final-submission access. Video and pitch PDF remain pending actual artifacts. Owner: Riccardo integration for product work; submission owner remains unassigned.

### 2026-11-14: CubiCasa annotation profile and Gemini defaults

The CubiCasa5K answers follow that collection's annotation conventions: only the main apartment on a multi-unit sheet, wardrobe fronts are not doors, a utility kitchen (APUK) is a second kitchen, a room labelled H is a bedroom, balconies need a label, a tub with a drawn shower head counts twice, a urinal is a toilet, and the window rule depends on the drawing style. The generic inventory prompt deliberately avoids source-specific rules. On 60 fresh dev plans (524 questions, gemini-4-argon at ultra-high resolution), the generic prompt got 418 right and the prompt with the CubiCasa profile 463 (88.4%); always giving the most common answer gets 300. The same model, resolution, crops and rules v2, run on the evaluation branch before the port to main (464 on these development plans), scored 421 of 482 (87.3%) on 54 held-out plans never used for any decision.

Decision: apply the profile by default, only to drawings from the CubiCasa5K collection; `STOA_ANNOTATION_PROFILE=none` restores the generic prompt everywhere, and uploads and other collections are unaffected. Default Gemini model gemini-4-argon (314 vs 306 of 355 for hydrogen on 40 dev plans; carbon matched hydrogen on the plans it finished and was several times slower), ultra-high image resolution, enlarged crops for plans of 1,600 px or less (297 vs 290 of 344), and a 65,536-token output limit for Gemini inventories because reasoning shares that budget (2,300 to 54,000 tokens per plan were measured; gemini-4-argon stayed under 27,400 and the 53,638 peak was gemini-4-hydrogen). Owner: Matteo. The evidence that could change it: a hidden test set whose CubiCasa answers do not follow these conventions.

### 2026-11-14: repeated readings flag uncertain visual counts

Each page inventory now makes two identical model requests in parallel (`STOA_INVENTORY_READINGS`, default 2). The first successful reading gives the count; when a repeat reading by the same model finds a different count, the answer carries an `agreement` record, a warning and a "Check this" line in the interface. A failed repeat never fails the answer. Reason: on 60 CubiCasa development plans, answers whose two readings agreed were right 455 of 504 times, against 6 of 15 where they differed. Repeating does not raise accuracy (the median of three readings scored 462 against 463 for one), so the count itself is unchanged. Reading the printed window and door codes was also tested and not adopted: no gain for windows, worse for doors. Details: `docs/evaluation/cubicasa-vision-development.md`. Cost: twice the inventory calls; `STOA_INVENTORY_READINGS=1` restores one call per page, and evaluation call budgets were updated. Owner: Matteo.

### 2026-11-14: unify Metria branding and the current analysis engine

Adopt Antonio's Metria identity, neutral interface, upload flow and interactive source overlays while retaining Michele's latest native extraction and question handling. Preserve server-backed session and message costs, persistent conversation, Cloudinary evidence close-ups, calibration, inspector controls, review history and explicit evidence focus. Unknown usage remains unknown; no demonstration token counts or fixed inference prices are introduced. Runtime paths and internal Trace-compatible API/configuration names stay portable so existing uploads, answers, credentials and counters survive. Owner: Riccardo integration.

### 2026-11-14: Gemini requests may take up to 600 seconds

The default Gemini timeout is now 600 seconds instead of 240 (`STOA_GEMINI_TIMEOUT_SECONDS`, 60 to 600). In the end-to-end run of commit d0c9fcd, 16 of 482 inventory readings got no response within 240 seconds; one CubiCasa plan lost both readings and all 24 of its questions. The evaluation and batch tools now wait up to 900 seconds per request by default so that they never cut a Gemini request short. The interface has no time limit of its own; a user can still stop waiting. Owner: Matteo.

### 2026-11-14: takeoff questions and spreadsheet export for routine estimating work

The user asked which routine tasks of a construction engineer Metria could simplify without changing the interface. Three came out on top: deriving finishes quantities from room geometry, adding a waste allowance to get an order quantity, and moving the numbers into a spreadsheet. Evidence: the challenge's own IFC benchmark wording asks "What is the total length of skirting boards needed?", "What is the total area of interior wall surfaces requiring painting?" and "How many square meters of flooring are required for each room?"; the partner asked for metric and material measurements; BD+C reports from JBKnowledge's 2021 construction technology survey that "more than three-fifths of those polled say they still use spreadsheets for estimating" ([article](https://bdcnetwork.com/construction-still-lags-other-industries-use-technology)); and Sage Estimating documents the usual waste convention, "When you apply waste, only the order quantity increases; the takeoff quantity remains the same" ([help page](https://help-sageestimating.na.sage.com/en-us/26_1/Content/ph_item/hidc_item_waste.htm)).

Decision: answer these in the existing chat, with no model call and no new panel, button or setting. On drawings with native room outlines, Metria now answers room perimeter, skirting length and wall area for a ceiling height stated in the question, and applies a stated waste percentage to any native area, length or volume answer. Chat options gains one entry, Export quantities (CSV), which lists every answered question and, under each sum, its measured items. Openings are not deducted, as in the RICS NRM 1 rule for wall finishes ("No deduction is made for voids (e.g. for door openings, screens or the like)"), and each answer says so. A ceiling height or waste percentage is never assumed: the takeoff panel removed earlier stays removed, and its 2.6 m and 10% defaults are not used. The new handler runs after every existing native solver, so it only sees questions they refuse. One existing error is corrected: a question about the wall area of a room was answered with its floor area.

Measured on the preview: outline lengths for 2,083 rooms on 65 Swiss floors agree with the DXF source within 0.04% through both the paired PDF and the standalone DXF; 3,720 Swiss, IFC and schedule benchmark questions give identical native answers before and after; of all 7,990 question wordings only the skirting question above triggers the handler. Details and limits are in the [application README](../stoa-trace/README.md#takeoff-questions-and-spreadsheet-export).

Not done: takeoff on IFC spaces (perimeters and wall areas sit under exporter-specific property names, and the benchmark's reference answers for these free-text questions disagree with each other), deduction of openings, comparison of drawing revisions, a schedule against plan cross-check and grouped totals. Owner: Matteo. The evidence that could change it: a partner statement on how openings should be measured, or hidden-test takeoff wording on IFC models.

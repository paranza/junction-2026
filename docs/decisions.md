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

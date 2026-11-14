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
| Product and stack | Trace prototype in `stoa-trace/`: FastAPI/Python, React/Vite, SQLite, native PDF/DXF/IFC extraction and hosted OpenAI vision. See its handoff for implemented scope and measured limits. |
| Deployment | Existing protected HTTPS deployment on one Verda CPU VM. Coordinate with its owner; credentials are outside Git. |
| Credits | OpenAI inference and Verda funding were verified by the prototype owner. Account secrets and entitlements do not transfer with this repository. |
| Team members and task owners | Assign together; personal contact details go in the event platform |

## Decision log

### 2026-11-13: initialize the team foundation

Create documentation and configuration from the supplied guide and screenshot. Keep inferred challenge themes labeled. Defer product code, dependency installation, CI build commands and provider-specific integrations until the official start and challenge selection.

For later entries, record: date, decision, reason, owner and the evidence or constraint that could change it.

### 2026-11-13: select Make Blueprints Talk and focus on measurements

Select the STOA challenge after the team's event discussion with the partner. Focus the product on a specific construction-engineering task, especially metric or material measurements, and make the evidence behind each answer clear in a simple visualization. The partner reported that its internal model performs poorly but could not share details. Vision models for rapid image-based answers are a team hypothesis, not a partner recommendation. Keep the technical stack open until the team chooses an implementation.

### 2026-11-14: hand off the working Trace prototype

At the prototype owner's request, place the application under `stoa-trace/` on `codex/stoa-trace-handoff`, preserving the existing team foundation. The implemented route uses native source records and constrained calculations first, with a hosted OpenAI vision fallback, evidence overlays and saved review state. It uses one existing Verda CPU VM and SQLite; no trained segmentation model or GPU is deployed.

`INFRA/architecture_pipeline.md` remains an earlier proposal. Its CenterNet/SAM2/Gemini components and accuracy claims are not implemented or established by the current prototype. The frozen diagnostic and vision reports under `stoa-trace/ops/reports/` record the actual measured coverage and limits. Read `stoa-trace/HANDOFF.md` before deciding the next implementation slice. Owner: the teammate handing off Trace; merging and shared deployment changes remain coordinated team actions.

### 2026-11-14: strengthen source verification and the quantity review workflow

Implement typed source-operand checks, strict unresolved-constraint handling, Swiss CAD compatibility and supported IFC quantities. Reuse versioned visual inventories and answers, record request usage with unknown dollar costs unless configured, and preserve original machine results alongside manual count revisions and reviewed working quantities. Reject unresolved model/view scope comparisons. Evaluate native changes on the same frozen 100-question sample, disjoint from the original diagnostic groups; do not present the stratified result as a competition score. Keep the existing deployment and runtime unchanged during local verification.

### 2026-11-14: add a raster specialist app with our own PyTorch models (`Michele-testing/`)

On branch `feat/blueprint-analyzer`, add a separate FastAPI app (port 9999) whose raster models are trained by us in plain PyTorch: PlanNet (U-Net segmentation plus CenterNet-style object heatmaps) and GlyphNet (CRNN text reader). Training labels come from the Swiss Dwellings DXF projected onto the PNGs and from CubiCasa5K SVG annotations; the preview's own plans stay held out. Questions are answered by deterministic multilingual templates over the extracted facts; Gemini flash-lite is a fallback over text facts only. Reason: the partner asked for accurate, visibly justified measurements at low inference cost, and `stoa-trace` reports 0 % coverage on CubiCasa raster plans. Details and measured results: `Michele-testing/docs/`. Owner: the teammate running the overnight build; integration with `stoa-trace` is a team decision.

### 2026-11-14: upgrade frontend with interactive plant shapes and Vercel design system

Download and vendor `vercel-labs/ui` under `third_party/vercel-labs-ui`. Adopt Vercel's clean, minimalist UI design system (modern typography, high contrast, clean panels, crisp badges, and keyboard navigation) in `stoa-trace/frontend`. Upgrade the plant drawing viewer so that highlighted shapes (bounding boxes, polygons, room areas, and doors/windows) are fully interactive: direct mouse hover with glow effects, floating inspection tooltips with quick actions (focus, properties, toggle exclusion), two-way synchronized hover highlighting between sidebar evidence items and drawing shapes, category filter chips on the canvas, spotlight dimming mode, and coordinate HUD. Maintain full compatibility with review state and existing unit tests. Owner: MUSTA HELMI frontend team.

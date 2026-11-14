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
| Product and stack | Product direction: a focused construction-drawing measurement tool with visual evidence for each answer. Stack remains open. |
| Deployment | Open |
| Credits | Anthropic/OpenAI support expected by teammate, not confirmed or redeemed |
| Team members and task owners | Assign together; personal contact details go in the event platform |

## Decision log

### 2026-11-13: initialize the team foundation

Create documentation and configuration from the supplied guide and screenshot. Keep inferred challenge themes labeled. Defer product code, dependency installation, CI build commands and provider-specific integrations until the official start and challenge selection.

For later entries, record: date, decision, reason, owner and the evidence or constraint that could change it.

### 2026-11-13: select Make Blueprints Talk and focus on measurements

Select the STOA challenge after the team's event discussion with the partner. Focus the product on a specific construction-engineering task, especially metric or material measurements, and make the evidence behind each answer clear in a simple visualization. The partner reported that its internal model performs poorly but could not share details. Vision models for rapid image-based answers are a team hypothesis, not a partner recommendation. Keep the technical stack open until the team chooses an implementation.

### 2026-11-14: add a raster specialist app with our own PyTorch models (`junction-testing/`)

On branch `feat/blueprint-analyzer`, add a separate FastAPI app (port 9999) whose raster models are trained by us in plain PyTorch: PlanNet (U-Net segmentation plus CenterNet-style object heatmaps) and GlyphNet (CRNN text reader). Training labels come from the Swiss Dwellings DXF projected onto the PNGs and from CubiCasa5K SVG annotations; the preview's own plans stay held out. Questions are answered by deterministic multilingual templates over the extracted facts; Gemini flash-lite is a fallback over text facts only. Reason: the partner asked for accurate, visibly justified measurements at low inference cost, and `stoa-trace` reports 0 % coverage on CubiCasa raster plans. Details and measured results: `junction-testing/docs/`. Owner: the teammate running the overnight build; integration with `stoa-trace` is a team decision.

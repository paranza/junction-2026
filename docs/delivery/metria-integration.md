# Metria integration verification

14 November 2026. The local app at <http://127.0.0.1:8791/> now combines Antonio’s Metria interface (`b6d7c42`), Michele’s native analysis fixes (`5d8598c`), and Matteo’s repeated visual readings (`d0c9fcd`). Matteo’s subsequent evaluation record (`96626c6`) is retained.

## Preserved behavior

The integration retains saved conversation, real server-backed session and message usage, Cloudinary source close-ups, explicit source focus, calibrated measurements, inspector tools, source-change guards, manual corrections and export. Category/confidence filters and metric/imperial conversion change display only. No fixed token counts, invented inference prices or local-only session totals are used.

Antonio’s branding, upload screen, collapsed library, large drawing canvas, docked composer and interactive source shapes are preserved. Additional controls use the same neutral visual system. Short landscape phone screens use the mobile conversation/drawing switch.

## Actual checks

- 318 backend tests and 36 frontend tests passed; the production frontend build passed.
- Native PDF workflow found two washbasins with two located sources. Review changed 2 to 1 and back to 2 while preserving both revisions. Repeated questions, cached answers and conversation survived reload.
- Calibrated QA geometry calculated 48 square metres from an entered reference; the current answer and history both displayed 516.667 square feet after unit conversion. This verifies the measurement flow, not the physical area of the example building.
- Native IFC API check found 211 doors with 211 evidence items. Preview, saved review/restoration, JSON and persisted server usage passed.
- A real Cloudinary evidence close-up opened in the local Metria interface with no additional model inference.
- Browser checks covered desktop, mobile portrait and short landscape, with a visible question composer and no horizontal page overflow.
- All 7,321 existing local answers and the previous model-event history remained unchanged. The cumulative ledger increased from 1 to 4 because three actual Gemini requests were used for the integration smoke tests; the 1,000-attempt ceiling was retained.

## Local Gemini configuration

The local app now uses Argon, ultra-high resolution, high reasoning, enlarged small-plan crops and two readings per page. Keep `STOA_GEMINI_MAX_OUTPUT_TOKENS` absent so each caller retains its cap, including 65,536 for inventories; the explicit-override validator accepts only 1,000-32,768. Optional Gemma review remains off until selected.

The actual Argon inventory smoke test returned four located doors from each of two readings, with an agreement record of `[4, 4]`. A separate general vision question also returned four. These are procedural development smoke checks, not a new accuracy estimate or a reserved evaluation. Argon token usage is recorded; its dollar estimate stays unavailable until a verified model-specific rate is configured.

The private project `.env` preserves the local port, dataset and existing runtime. Credentials remain in private configuration. No production Verda deployment was performed by this integration; the documented production policy is separate.

[Machine-readable verification](../../stoa-trace/ops/reports/metria-integration/verification.json).

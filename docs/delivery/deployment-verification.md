# Deployment verification

The existing protected deployment is <https://stoa-86-38-182-146.sslip.io>. Credentials remain in private local configuration. No second VM was created.

Current runtime source matches **`328d561`** from the measured-review-policy branch, deployed on 14 November 2026. All 16 server source hashes were compared with the VM. The integrated main commit is recorded in the final release record. Active inference uses **Gemini 4 Carbon**, medium reasoning, high image resolution, a 24,000-token output cap and 600-second transport timeout. Gemma 4 31B with minimal reasoning is available as an optional visual count recheck. Rechecks are off by default while their measured benefit remains unproven.

## Gemini and UI release verification

- **272 backend tests**, **23 frontend tests** and the production frontend build passed.
- Authentication, 923 existing documents, native IFC 211-door evidence, PNG preview, review/restoration, JSON export and persistence through restart passed with zero model calls.
- A separate production Gemini smoke test uploaded a procedural development PNG and found four doors with four evidence regions using **one actual Carbon request**. Estimated token cost: **$0.011496 before credits**. An exact repeat made zero model calls and cost $0. The session endpoint retained two distinct messages and charged the first inference once.
- The live request ledger was preserved from **16 to 17 requests**, with an explicitly configured **1,000-attempt ceiling** for the user-authorized testing and runtime. Credits and rate limits remain separate. No database or counter reset occurred.
- Before replacement, SQLite's backup API wrote `/srv/stoa/backups/trace-before-gemini-costs-20261114.sqlite3`; the previous image remains `stoa-junction:before-gemini-costs-20261114`.
- The polished drawing workspace uses the free MIT BoardUI primitives with attribution. It shows per-message costs and current-session totals, retains totals on reload, prices actual models separately and preserves unknown usage. Desktop and 390-pixel mobile layout checks passed without horizontal overflow.

[Machine-readable deployment evidence](../../stoa-trace/ops/reports/gemini-release/deployment.json). This small smoke test establishes live integration and cost accounting, not broad recognition accuracy.

## Earlier OpenAI release checks

## Completed checks

- **231 production Python tests** and **16 frontend tests** passed; the frontend production build succeeded.
- Final development-only native regression: 2,929/6,801 numeric correct, all 2,903 previously correct answers retained, zero errors and model calls. No reserved evaluation.
- Unauthenticated remote request rejected with 401; authenticated health succeeded with **923 documents**, including all 913 original sources and ten test uploads.
- Native IFC answer: **211 doors with 211 evidence items**. PNG preview, JSON export and saved review passed. The temporary exclusion used for the review check was restored to 211.
- Container restart preserved the saved answer and reviews.
- Six new procedural development uploads across PNG, JPEG, PDF, SVG, TIFF and WebP gave six exact visual door counts and matching reference localizations at the frozen 0.3 box-IoU threshold. They used **12 real model calls**; no broad or external accuracy claim follows.
- The runtime model-attempt ledger was preserved: four earlier upload calls plus 12 six-format calls equals **16/50 recorded attempts**. Verification and restarts made no model calls and did not reset the ledger.
- Actual browser calibration flow: 48 m² from an entered 8 m reference and outline, zero model calls, saved result restored after reload.

Before each replacement, the existing Docker image and SQLite database were backed up on the same VM. The latest backup is `/srv/stoa/data/trace-before-ifc-quality-20261114.sqlite3`; image `stoa-junction:before-ifc-quality-20261114` is retained. Uploads, source files, answers, review history and counters remain under `/srv/stoa/data`. Provider keys transfer over encrypted SSH stdin and never enter build archives or Git.

Scheduled Riccardo deployment work must fetch reviewed main, run the documented checks and preserve this state. Use `ops/verify_remote.py --exercise --restart`; it polls read-only readiness before making a single verification write. If application sources have not changed, verify the existing deployment instead of rebuilding. Scheduled runs must preserve the selected Gemini policy, cumulative request counter and configured ceiling; they must not repeat the independently released unseen-file evaluation.

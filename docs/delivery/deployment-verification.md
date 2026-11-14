# Deployment verification

The existing protected deployment is <https://stoa-86-38-182-146.sslip.io>. Credentials remain in private local configuration. No second VM was created.

Application code **`4f0d8e2`** deployed and verified on 14 November 2026. Subsequent delivery commits contain reports only. Gemini support is installed, while the active provider remains OpenAI (`gpt-6-astra`) pending a private Gemini key and successful live validation.

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

Scheduled Riccardo deployment work must fetch reviewed main, run the documented checks and preserve this state. Use `ops/verify_remote.py --exercise --restart`; it polls read-only readiness before making a single verification write. If application sources have not changed, verify the existing deployment instead of rebuilding. A live Gemini result is not yet claimed.

# Deployment verification

## Source attribute release, Saturday evening

Reviewed main `af767260c3611fb00c43e4689ea9adf105652353` is deployed on the
existing protected CPU VM. The 397 backend tests, 59 frontend tests and build
passed. All 7,066 development cases retained their native outcomes: 3,234/6,801
numeric correct, zero previously correct losses, source changes, request errors
or model calls. The preview reserve and independently released evaluation were
not rerun.

Authentication, native answers/evidence, previews, saved review/export and
restart persistence passed. SQLite backup integrity and retained previous image
were verified. Prior answers, uploads, event history, credentials and explicit
Carbon policy are preserved. The production counter remains **17/1,000**.
Optional inventory fallback and specialist detectors remain disabled. Both local
apps load the release with their original policies and unchanged counters of
4/1,000 and 140/200.

[Deployment and hashes](../../stoa-trace/ops/reports/source-attributes-recovery/deployment.json),
[native regression](../../stoa-trace/ops/reports/source-attributes-recovery/native-development.json),
[tests/build](../../stoa-trace/ops/reports/source-attributes-recovery/build-checks.json),
[local continuity](../../stoa-trace/ops/reports/source-attributes-recovery/local-continuity.json).

The lift-door counting prompt and parser process isolation were also released
before this deployment. The exact lift case changed from 35 to 36 doors with
the landing entrance located; closed shaft and drawn-entrance controls passed.
Those functional checks do not establish general door-count accuracy.

## Scheduled Saturday 18:00 verification

Latest fetched main `29f6bf9` contains the same application source as deployed release `915f768`. All 27 server-source hashes and three frontend build hashes match the running container. The existing successful 374 Python tests, 59 frontend tests/build and 7,066-case development regression apply to this identical code; no tests or reserved evaluations were repeated.

Authenticated native answer/evidence, preview, review/restoration and export checks passed again. The same image had already passed restart persistence in the immediately preceding deployment; its start time remained unchanged, so no needless rebuild, replacement or second restart was performed. A fresh SQLite backup passed integrity verification and the current image was retained. All 28 pre-existing answers, 11 uploads, credentials, configured Carbon policy and prior event history are preserved. Model attempts remain **17/1,000** and verification made zero model calls. [Scheduled verification and source hashes](../../stoa-trace/ops/reports/saturday-1800/verification.json).

## Model-scope release, 14 November evening

Reviewed main revision `915f76800db559a96a82dde0ae29d824ae503543` is deployed on the existing protected VM. It prevents whole-model answers from partial IFC-derived drawings whose model is missing. 374 Python tests, 59 frontend tests/build and the paired 7,066-case native regression passed with no losses, changed outcomes, source changes, errors or model calls. Authentication, native evidence, previews, review/export and restart persistence passed. Runtime configuration, credentials, uploads, prior answers and event history are preserved; the production model counter remains 17/1,000. [Deployment record](../../stoa-trace/ops/reports/model-coverage/deployment.json), [automatic-path evaluation](../evaluation/model-coverage-development.md).

## Quantity workflow release, 14 November evening

Reviewed main revision `8dabfa7273504db21cc77ef0272c7388a412f6dd` is deployed to the existing protected Verda VM. 371 Python tests, 59 frontend tests/build and the 7,066-question native development gate passed, with no previously correct losses, changed outcomes, source-hash changes, request errors or model requests in that gate. The reserved evaluation was not rerun.

The old Docker image and SQLite backup were retained. Authentication, the 211-door IFC answer with 211 evidence objects, PNG preview, review/restoration, JSON export and restart persistence passed. All 26 existing answers and 11 uploads remain intact; the event history and credentials are unchanged. The production policy remains Gemini Carbon, the cumulative model counter remains **17/1,000**, and verification used zero model requests. Both local apps also load the release, retaining their separate Argon/Carbon policies and counters of 4/1,000 and 137/200.

[Deployment and source hashes](../../stoa-trace/ops/reports/quantity-workflow/deployment.json), [development regression](../../stoa-trace/ops/reports/quantity-workflow/native-development.json), [tests/build](../../stoa-trace/ops/reports/quantity-workflow/build-checks.json), [local continuity](../../stoa-trace/ops/reports/quantity-workflow/local-continuity.json), [product changes and limitations](quantity-workflow-improvements.md).

The existing protected deployment is <https://stoa-86-38-182-146.sslip.io>. Credentials remain in private local configuration. No second VM was created.

The historical Saturday 13:00 release used main **`8d4b822391300e2127c30a1077222c30fb969d20`**, deployed at **13:06 Europe/Helsinki**. The latest verified application revision is recorded in the source attribute release above. Documentation-only commits can follow a deployed application revision without requiring a rebuild. The explicitly configured production policy is preserved: **Gemini 4 Carbon**, medium reasoning, high image resolution, a 24,000-token output cap, 600-second timeout and no small-image crops. Optional Gemma 4 31B review uses minimal reasoning and remains off by default. New main defaults do not replace this selected production policy.


## Saturday 13:00 deployment

- Frozen reviewed main: `8d4b822`; **301 Python tests**, **34 frontend tests**, and the production frontend build passed in an isolated worktree.
- The same **7,066 development questions** retained every previously correct case. Numeric correct increased **2,929 to 3,234 of 6,801 (47.55% across all numeric questions)**, with zero source-hash changes, request errors or model calls. Abstentions remain failures; this is a native development comparison, not a hosted-vision or unseen-file score.
- Authentication rejected unauthenticated access with 401. Authenticated health, the native 211-door IFC answer and 211 evidence items, PNG preview, review/restoration, JSON export and persistence through restart passed.
- All **25 existing answers**, all **11 uploaded files**, the model-event history and the original runtime configuration/credentials were preserved. Verification added one native answer. The cumulative ledger stayed **17/1,000**, with zero model requests from this task.
- SQLite's backup API created `/srv/stoa/backups/trace-before-saturday-1300-20261114.sqlite3`; its integrity check passed. The previous image remains `stoa-junction:before-saturday-1300-20261114`. The new image built before replacing the running container. No second VM was provisioned.
- The separate 924-question preview reserve was not scored or inspected, and the released independent-file evaluation was not repeated.

[Deployment, policy and source hashes](../../stoa-trace/ops/reports/saturday-1300/deployment.json), [paired native development regression](../../stoa-trace/ops/reports/saturday-1300/native-development-regression.json), [build checks](../../stoa-trace/ops/reports/saturday-1300/build-checks.json). Earlier releases below are historical records.

## Cloudinary evidence release verification

- **280 backend tests**, **27 frontend tests** and production build passed for the integrated release.
- The final 7,066-question native development regression retained **all 2,929 previously correct numeric answers**, with zero case outcome changes, source changes, request errors or model calls. [Paired aggregate](../../stoa-trace/ops/reports/gemini-release/native-regression.json).
- Authentication, 924 documents, native IFC 211-door evidence, PNG preview, review/restoration, JSON export and restart persistence passed again.
- A real Cloudinary crop from an existing Gemini answer returned a **320 × 336 PNG**, 5,880 bytes. Authenticated delivery and cached replay passed; unauthenticated access returned 401. The saved answer's count, evidence, source and review remained unchanged.
- The live model-request ledger stayed at **17/1,000**. Cloudinary close-ups make zero model calls; their media quotas are separate from LLM inference estimates.
- Backup before replacement: `/srv/stoa/backups/trace-before-cloudinary-evidence-20261114.sqlite3`. Retained previous image: `stoa-junction:before-cloudinary-evidence-20261114`. No uploads, answers, reviews, credentials or counters were reset.
- The existing local `localhost:8791` workspace was updated while retaining its runtime and 252 existing answers. A real browser upload, Gemini answer, Cloudinary close-up, cached replay and mobile dialog check passed. The local runtime remains separate from the shared VM's ledger.

[Deployment hashes and verification](../../stoa-trace/ops/reports/gemini-release/cloudinary-deployment.json), [actual browser crop](../assets/trace-cloudinary-closeup.jpg), [Cloudinary entry draft](cloudinary-entry-draft.md). The free Cloudinary workspace still requires the owner's private claim flow for permanence; no award form was submitted.

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

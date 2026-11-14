# Trace

Construction drawing questions with inspectable source evidence. The workspace combines native PDF, DXF, IFC and semantic SVG extraction with a hosted vision fallback. It computes quantities from checked source values, displays their locations, and lets an engineer add missed objects, exclude candidates and save an auditable review.

## Run locally

Requires Python 3.11+, Node 22+, and the extracted Stoa preview dataset.

The handoff pins Python 3.11, Node 22.14.0 and npm 10.9.2. See `HANDOFF.md` for Windows setup and `FRIEND_PROMPT.md` to resume in a new Codex session.

```sh
cp .env.example .env
chmod +x run.sh
./run.sh
```

Open <http://127.0.0.1:8787>. Set `STOA_DATA_ROOT` in `.env` to the folder containing `data/` and `questions.jsonl`. To use vision, set `OPENAI_API_KEY` in a private `.env` or `~/.config/stoa-junction-2026/secrets.env`. Visual inventories can also use Gemini (`GEMINI_API_KEY`, see `.env.example`); `ops/cubicasa_eval.py` scores them on CubiCasa plans with a hard cap on calls. Native mode needs no API key. Uploads also work without the preview dataset.

The portable default dataset location is `datasets/junction-dataset-preview/`, which is ignored by Git. Download the preview separately using the URL in `HANDOFF.md` and retain its licence files. Set a fresh local `STOA_RUNTIME_DIR`; credentials and the existing shared runtime are not part of the handoff.

For explicit cross-platform setup and after pulling dependency or frontend updates:

```sh
python3 -m venv .venv
.venv/bin/python ops/refresh_local.py
cp .env.example .env
.venv/bin/python ops/start_local.py
```

Keep an existing private `.env` when updating. `refresh_local.py` always installs the pinned Python requirements, runs `npm ci`, and rebuilds the frontend. `start_local.py` reads `.env` before choosing the host and port; exported environment variables take precedence. On Windows, use `.venv\\Scripts\\python.exe` and `Copy-Item` as documented in the handoff. `run.sh` is the macOS/Linux convenience wrapper and does not refresh dependencies on every launch.

For UI development, run the backend and `npm --prefix frontend run dev`. Vite proxies `/api` to port 8787.

## How answers work

1. Extract native words, table rows, CAD polygons and semantic entities, or IFC GUIDs and quantities. Preserve source identifiers and coordinates.
2. Attempt a deterministic operation on recognized scope and constraints. Unrecognized filters fall through rather than returning an unfiltered total.
3. For supported visual counts, prepare and cache a located category inventory once per drawing page. Other questions use source records and drawing images, including overlapping detail crops. Selected page and region requests restrict the source context.
4. Link citations to source objects or normalized image regions. Check numeric operands against typed source properties and exact native excerpts before computing. A model-selected answer type cannot bypass quantity checks. Image-only readings stay provisional.
5. Display scope, method, usage, limitations, calculations and evidence. A source ID, an exact excerpt and semantic correctness are different checks. User corrections preserve the original result and every saved review revision.

Translated questions are first rewritten into the English wording the native solvers read (`server/normalize.py`), copying labels, room numbers and apartment letters verbatim; the answer shows the rewritten text as `interpreted_question`. The template table `server/question_templates.json` is rebuilt with `python ops/build_question_templates.py --dataset-root <preview>`, which reads question wording only, never answers. Unknown wording passes through unchanged.

PDF text uses page rotation consistent with previews. Swiss CAD room polygons are projected onto paired PDFs only when multiple matching room-number anchors support an alignment; otherwise boxes are withheld. IFC entities can link to matching semantic SVG/PDF floor views. Whole-model counts and visible-floor counts are separate operations.

## Supported first-version workflows

- IFC entity counts by supported class and resolved storey, with GUID evidence.
- IFC room net/gross areas and selected wall length/area/volume totals where explicit supported quantities and units exist. Missing terms refuse the aggregate.
- Swiss semantic CAD room labels, printed room areas, unit outlines and supported symbol inventories.
- Recognized PDF door schedules and room finish schedules with row evidence.
- Vision analysis of raster drawings and other supported previews, with reusable candidate inventories and explicit completeness warnings.
- Document search, multi-file upload, page navigation, pan/zoom, selected-region questions, one-click evidence focus, manual additions/exclusions, undo, saved review revisions, explicit highlight commands and JSON export.

## Review and compare

Click a source item to open its page and focus its box or polygon. Unlocated BIM
records show properties without inventing a drawing position. Native source
records, visual candidates and manually added objects have distinct labels.

For count answers, use **Add missed object** to draw a box or point, or enter
normalized page coordinates using the keyboard. Additions must match the counted
category and remain within the original source scope. Exclude/reinclude objects,
undo draft changes, add a note and save. Original and revised counts, additions,
exclusions and revision history survive reload and JSON export.

The optional comparison control checks native versus independently located visual
counts at matching scope. It refuses model-versus-floor and schedule-versus-plan
comparisons. Room annotations can also be compared with independently calculated
native polygon areas without a model call. A reviewer can save a working quantity
and reason while retaining both source values and the original machine answer.
Agreement does not independently establish completeness or engineering correctness.
Saved answers whose sources have changed are marked outdated; their overlays and
corrections are disabled until the question is recomputed.

## Caches and usage

Repeated identical questions reuse immutable analysis and receive fresh answer
IDs, so one user's review cannot contaminate another answer. Visual inventories
can answer supported follow-up category counts without another model call.
Cache keys include source and paired-view hashes, solver/extractor, prompt,
rendering and model versions, page, region and analysis mode. Changed paired
drawings invalidate extraction, answers and previews.

Answer details show model calls, token usage, application cache hits and initial
visual extraction usage separately. Dollar cost is unknown unless token rates
are explicitly configured in the server environment. The optional rates in
`.env.example` produce estimates, not invoice totals. Hosting/storage costs are
separate. Stop waiting discards stale UI responses; it cannot cancel a model
request already running on the server.

## Accuracy and limits

Run the evaluator before making accuracy claims:

```sh
.venv/bin/python -m unittest discover -s tests -v
npm --prefix frontend test
.venv/bin/python ops/benchmark.py --dry-run
.venv/bin/python ops/benchmark.py --mode native --suite full
```

The frozen 50-case diagnostic sample deliberately includes different sources and rare task types. It is not a representative estimate of competition accuracy. Exact counts must match; measurements use the supplied 2% tolerance. Reports distinguish coverage, numeric accuracy across all questions, accuracy on answered questions, and text requiring manual review. Geometry validation checks coordinate validity, not whether a citation actually proves the claim.

The competitive-upgrade native evaluation uses the same 100 questions before and
after the change, across 70 drawing groups disjoint from the original diagnostic.
Correct numeric answers improved from **41/97 to 55/97**; coverage from **44/100
to 58/100**. Three answered numeric cases remain incorrect in both runs. The
sample contains 64 Swiss, 33 CubiCasa and three IFC-Bench text questions, so it
does not establish an overall competition score or hosted vision accuracy.
The original diagnostic improved from 21/44 to 28/44 correct numeric answers,
with two text answers requiring manual review. See
`ops/reports/competitive-upgrade/paired-comparison.md` and the underlying reports.

To reproduce the grouped run against a local backend, or create a separate
evaluation without replacing the existing manifests:

```sh
python ops/benchmark.py --manifest ops/evaluation-grouped-100.json --mode native --max-questions 100
python ops/grouped_manifest.py --dataset-root /path/to/preview --count 100 --languages all --output /tmp/new-evaluation.json
python ops/benchmark.py --manifest /tmp/new-evaluation.json --mode native --max-questions 100
```

`ops/evidence_audit.py` creates a pending human-annotation template and scores
object precision/recall only after explicit source review. Model regions never
become automatic ground truth. Keep related exports, models, buildings and
translations in the same evaluation group; do not tune on a scored final holdout.

`questions.jsonl` supplies optional example question wording only. Its answer labels stay out of extraction, prompts and indexes. Evaluation labels and results are confined to the evaluation manifests and reports under `ops/`.

Visual counts can miss objects or misinterpret symbols. A model's completeness claim is not independent verification. The app shows these as visual candidates for review. Source-based counts describe modeled or documented instances, not an as-built survey. Some source questions have ambiguous building/floor scope.

DWG uploads are accepted for project storage; analysis requires a supported paired export or an additional DWG conversion tool. Arbitrary geometry measurement, comprehensive wall/MEP quantity extraction, scans without legible dimensions, and every exporter-specific schedule are not implemented. No fine-tuned segmentation model is currently deployed. A GPU is not needed for the current hosted-vision/native architecture.

## Data, access and costs

- Original files and generated caches remain separate. The app stores uploads, extraction caches, previews, answers and model request events under `STOA_RUNTIME_DIR`.
- SQLite defaults to WAL on a local disk. Set `STOA_SQLITE_JOURNAL=DELETE` for a compatible single-writer shared-volume deployment; do not scale multiple app replicas around SQLite.
- Set `STOA_ACCESS_TOKEN` to protect backend APIs behind a server-side proxy that supplies `X-Trace-Token`. Do not embed it or provider keys in the browser. Use HTTPS and access control for a remote workspace.
- `STOA_MAX_MODEL_CALLS` limits recorded model attempts per runtime database (default 500). It is an attempt limit, not a dollar budget. Configure a provider spending cap separately.
- Hosted model requests send selected source material to OpenAI with `store: false`; this does not override the provider's retention terms. Native mode sends no model requests.
- Dataset sources retain their respective licenses; source credits are shown in the app. The dataset is not bundled into this repository. Team code uses `LICENSE`; source-derived screenshots, benchmark questions and evidence retain the terms documented in `THIRD_PARTY_NOTICES.md` and `third_party/dataset_licenses/`.

See `DATA_INVENTORY.md` for the complete preview file inventory. The full 10 GB dataset has not been loaded.

See `ops/connection-status.json` for non-secret service setup status and deployment documentation under `ops/` when available. No API keys belong in Git.

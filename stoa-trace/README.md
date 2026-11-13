# Trace

Construction drawing questions with inspectable source evidence. The workspace combines native PDF, DXF, IFC and semantic SVG extraction with a hosted vision fallback. It computes quantities from cited objects or source values, displays their locations, and lets an engineer exclude count candidates and recompute the result.

## Run locally

Requires Python 3.11+, Node 22+, and the extracted Stoa preview dataset.

The handoff pins Python 3.11, Node 22.14.0 and npm 10.9.2. See `HANDOFF.md` for Windows setup and `FRIEND_PROMPT.md` to resume in a new Codex session.

```sh
cp .env.example .env
chmod +x run.sh
./run.sh
```

Open <http://127.0.0.1:8787>. Set `STOA_DATA_ROOT` in `.env` to the folder containing `data/` and `questions.jsonl`. To use vision, set `OPENAI_API_KEY` in a private `.env` or `~/.config/stoa-junction-2026/secrets.env`. Native mode needs no API key. Uploads also work without the preview dataset.

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
3. For other questions, provide the model with source records and drawing images, including overlapping detail crops. Selected page and region requests restrict the source context.
4. Link citations to source objects or normalized image regions. Deduplicate located visual candidates and compute counts from the resulting set. Recompute measurements only from cited values with compatible units.
5. Display scope, method, limitations, calculations and evidence. Native source support and visual analysis have different labels. User corrections preserve the original result.

PDF text uses page rotation consistent with previews. Swiss CAD room polygons are projected onto paired PDFs only when multiple matching room-number anchors support an alignment; otherwise boxes are withheld. IFC entities can link to matching semantic SVG/PDF floor views. Whole-model counts and visible-floor counts are separate operations.

## Supported first-version workflows

- IFC entity counts by supported class and resolved storey, with GUID evidence.
- IFC room net areas where explicit supported quantities exist.
- Swiss semantic CAD room labels, printed room areas, unit outlines and supported symbol inventories.
- Recognized PDF door schedules and room finish schedules with row evidence.
- Vision analysis of raster drawings and other supported previews, with reviewable candidate regions.
- Document search, multi-file upload, page navigation, pan/zoom, selected-region questions, evidence inspection, count correction, explicit highlight commands and JSON export.

## Accuracy and limits

Run the evaluator before making accuracy claims:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python ops/benchmark.py --dry-run
.venv/bin/python ops/benchmark.py --mode native --suite full
```

The frozen 50-case diagnostic sample deliberately includes different sources and rare task types. It is not a representative estimate of competition accuracy. Exact counts must match; measurements use the supplied 2% tolerance. Reports distinguish coverage, numeric accuracy across all questions, accuracy on answered questions, and text requiring manual review. Geometry validation checks coordinate validity, not whether a citation actually proves the claim.

`questions.jsonl` supplies optional example question wording only. Its answer labels stay out of extraction, prompts and indexes. Evaluation labels and results are confined to `ops/benchmark-config.json` and `ops/reports/`.

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

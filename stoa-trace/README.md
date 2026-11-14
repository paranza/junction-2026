# Metria

Formerly Trace. The folder name `stoa-trace/`, the `trace-drawing-workspace` package and the `STOA_` environment prefix are unchanged.

Construction drawing questions with inspectable source evidence. The workspace combines native PDF, DXF, IFC and semantic SVG extraction with a hosted vision fallback. It computes quantities from checked source values, displays their locations, and lets an engineer add missed objects, exclude candidates and save an auditable review.

## Integrated Metria workspace

The primary interface contains Chats, Dataset and Spending. Start a chat with the plus beside Chats, attach a drawing, then ask questions and open the answer's Evidence panel. Existing conversations are nested beneath Chats. Region selection scopes registered native room queries to the selected area. There is no project or settings page in the current UI; older project records and API routes remain compatible.

Unknown wording over native quantities can use a Gemini-planned query executed by Python over source records. Supported query operators are count, value, sum, min, max and mean, with source-field filters. This does not establish arbitrary-question or arbitrary-drawing accuracy. See the [chat and region recovery verification](../docs/delivery/chat-and-region-recovery.md) for the actual checks and limits.

Antonio’s Metria branding and interactive drawing workspace are integrated with the current native parsers and question handling. Saved conversations, inference accounting, Cloudinary close-ups, source focus and review history use the existing backend. Calibration and inspector APIs remain available for integrations. Display conversion does not alter source quantities.

The `stoa-trace/` folder, `STOA_` settings, existing private configuration paths and storage identifiers remain compatible. Keep your private `.env` and runtime when updating, then run `ops/refresh_local.py` and restart the server.

## Run locally

Requires Python 3.11+, Node 22+, and the extracted Stoa preview dataset.

The handoff pins Python 3.11, Node 22.14.0 and npm 10.9.2. See `HANDOFF.md` for Windows setup and `FRIEND_PROMPT.md` to resume in a new Codex session.

```sh
cp .env.example .env
chmod +x run.sh
./run.sh
```

Open <http://127.0.0.1:8787>. Set `STOA_DATA_ROOT` in `.env` to the folder containing `data/` and `questions.jsonl`. To use vision, set `OPENAI_API_KEY` in a private `.env` or `~/.config/stoa-junction-2026/secrets.env`. Native mode needs no API key. Uploads also work without the preview dataset.

Gemini is selectable with `STOA_PROVIDER=gemini`, `STOA_MODEL=gemini-4-argon` (the default) and a private `GEMINI_API_KEY`. CubiCasa5K plans are counted with that collection's annotation conventions (`STOA_ANNOTATION_PROFILE=none` turns them off). Each new page inventory makes `STOA_INVENTORY_READINGS` model calls (default 2): the first gives the count, and a repeat reading by the same model that finds a different count flags the answer for review; `ops/cubicasa_eval.py` scores the visual inventory on CubiCasa plans with a hard cap on calls. An optional Gemma model can review visual counts through the same key. See [provider and analysis-policy setup](ops/GEMINI.md), including a prepared medium-reasoning, 24,000-token, 600-second policy with high image resolution. These settings are configuration options, not a deployment or accuracy claim. Exported variables take precedence; a private `gemini.env` sidecar activates only once it contains a key. Provider changes require a restart and invalidate model answer caches. Existing saved answers and reviews are retained.

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
- GIF, WebP, BMP and multipage TIFF input alongside PDF, PNG, JPEG, SVG, DXF and IFC. Animated inputs explicitly use their first frame.
- Area and length measurement from a user-supplied reference length and an outlined polygon or segment, with page and source binding. Automatic rectangular areas can use two explicitly quoted dimensions with compatible units.
- Material takeoff questions on drawings with native room outlines: room perimeter, skirting length, wall area for a ceiling height stated in the question, and a waste allowance on any native quantity. No model call.
- A chat's answered quantities as a CSV file for a spreadsheet, from Chat options, with one line per measured item under each total.

## Takeoff questions and spreadsheet export

These cover three routine steps of an estimator's work: deriving finishes quantities from room geometry, adding a waste allowance to get an order quantity, and moving the numbers into a spreadsheet. They use the existing chat. The only visible addition is one entry in the Chat options menu.

Ask in the chat, on a drawing with native room outlines (the Swiss CAD floors, or a DXF upload with the same layers in metre units):

- **"What is the perimeter of room 5.11?"** The closed room outline is measured and highlighted.
- **"How much skirting is needed for apartment A?"** The sum of the outlines of the indoor rooms in scope. Without a room, apartment or selected area the scope is every numbered indoor room on the drawing, and the answer says so. Balconies, loggias, shafts and voids are left out.
- **"What is the wall area of room 5.11 with a 2.6 m ceiling?"** Outline length times the stated height. A floor plan does not show the ceiling height, so a wall-area question without one gets a request for it instead of an assumed value.
- **"... plus 10% waste"** on any of the above, and on every other native area, length or volume answer (room areas, schedule areas, IFC wall and slab quantities). The net quantity, the factor and the order quantity are all shown.

Rules: door and window openings are not deducted, and each answer says so. This is the RICS NRM 1 cost-planning rule for wall finishes ("No deduction is made for voids (e.g. for door openings, screens or the like)"); detailed measurement under NRM 2 makes no deduction only for voids up to 1 m², so larger openings would be deducted there, which this version does not do. A length is scaled from the room's own outline and its metric CAD area, never from a sheet scale, DPI or a typical door width. A question with any word the handler does not resolve (a filter, a comparison, an unknown room) is refused and continues to the normal fallback. The handler runs after all existing native solvers, so it only sees questions they refuse. A question about the wall area of a room is no longer answered with the room's floor area.

Checked on the preview data: outline lengths for all 2,083 rooms on the 65 Swiss floors agree with the DXF source within 0.04%, through both the paired PDF sheet and the DXF on its own; 3,720 benchmark questions (Swiss, IFC, schedules) give identical native answers before and after the change. Not measured: drawings from other CAD exporters, and rooms with curved walls, which the room extraction already leaves out.

**Export quantities (CSV)** in Chat options downloads the chat's answered questions: question, quantity, unit, answer, drawing, scope, basis, status, review revision and answer ID. When an answer is a sum of source quantities, each measured item follows on its own line, so "What is the total net floor area of all rooms?" exports as a room schedule. Numbers use the reader's decimal mark, with semicolon separators for comma-decimal locales, so the file opens as numbers in a spreadsheet. Cells that would start a formula are written as text. The export reads saved answers and recalculates nothing; the JSON export per answer is unchanged.

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

## Cloudinary evidence close-ups

Cloudinary provides an optional source-inspection step. Select a saved, located evidence item and choose **Open evidence close-up**. The application uploads its canonical rendered page as authenticated media, asks Cloudinary for an explicit crop and enlargement, and serves the derived PNG through the protected workspace. It preserves the original source, quantity, evidence coordinates and review. No generative enhancement is used, and the close-up never becomes an inference input.

Install the pinned Python requirements, put a single `CLOUDINARY_URL=cloudinary://...` assignment in a private `.env` or `~/.config/stoa-junction-2026/cloudinary.env`, then create the restrictive signed upload preset once:

```sh
python ops/setup_cloudinary.py
```

Restart the backend after configuration changes. The optional button is hidden when the integration is unavailable. The API secret and signed delivery URLs stay on the server; repeated page uploads and close-ups use immutable caches. This consumes Cloudinary media quotas separately from the displayed LLM inference cost. Hosted media operations do not establish better recognition accuracy. See [Cloudinary entry and live verification](../docs/delivery/cloudinary-entry-draft.md).

## Caches and usage

Repeated identical questions, and recognized equivalent translations, reuse immutable analysis and receive fresh answer
IDs, so one user's review cannot contaminate another answer. Visual inventories
can answer supported follow-up category counts without another model call.
Cache keys include source and paired-view hashes, solver/extractor, prompt,
rendering and model versions, page, region and analysis mode. Changed paired
drawings invalidate extraction, answers and previews.

The interface shows inference cost for each question and a running total for the
current browser-tab session, including failed requests where provider usage is
available. A session UUID in `sessionStorage` survives ordinary reloads, and
`/api/usage` rebuilds its totals from persisted model-attempt/response events.
Native and cached answers make zero new model calls. Historical inventory usage
is not charged again to every follow-up question. Unknown usage or missing prices
stay unknown, with a known estimated subtotal kept separate.

Estimates use each model's token usage, including reasoning output, before
credits; they are not provider invoices or account balances. Dated Carbon and
hosted Gemma rates are bundled through 30 November 2026. The exact-model
`STOA_PRICE_MODEL` and rate settings can explicitly override them. Hosting and
storage are separate. Stop waiting discards stale UI responses; it cannot cancel
a model request already running on the server. See [accounting and policy
details](ops/GEMINI.md#per-message-and-session-inference-cost).

## Models and methods

Metria answers from the source file first and uses machine learning only where the source cannot answer. No model is trained or fine-tuned on the challenge data, and expected answers stay out of inference code and prompts. The translation template table contains question wording only. Every rule below reads the structure of a drawing format, so it applies unchanged to new files in that format.

| Layer | What it is | Used for |
|---|---|---|
| Native parsers (deterministic) | IfcOpenShell, ezdxf, PyMuPDF, shapely | IFC entities, storeys, quantities and spatial containment; Swiss DXF rooms, units, doors, windows and fixture symbols; PDF words, ruled schedule tables and room fill colours; polygon areas, egress paths and turning circles |
| Gemini (`STOA_MODEL`, default `gemini-4-argon`) | Hosted multimodal LLM, structured JSON output | Visual inventory of raster images and plans without native data; schedule query plans that are then executed deterministically on the extracted table; translation of question wording the template table does not cover |
| Gemma (`STOA_VISUAL_AUDIT_MODEL=gemma-4-31b-it`, optional) | Hosted open-weights model on the same key | A second review of visual counts. It is not independent verification |

How the layers combine:

1. Native first. A question the source structure answers (an IFC quantity, a CAD room area, a counted symbol) is computed without a model call, with the source IDs and calculation shown.
2. Model plans, code computes. For schedules, Gemini only chooses the table, columns and codes. The count is executed in Python on the extracted rows, so a model cannot invent a number. A plan that does not match the table is refused.
3. Vision for everything else. A drawing with no native data, such as a scan or a photo of a plan never seen before, goes to the Gemini visual inventory: located candidates per category, cached once per page, optionally audited by Gemma. These answers are labelled provisional and the reviewer can add or exclude candidates.
4. Translation is checked. A Gemini translation is used only if labels, numbers and room identifiers survive unchanged (`translation_preserves_constraints`); otherwise the original wording is used.
5. Refuse instead of guess. Missing quantities, unknown filters or ambiguous scope return no answer rather than an unfiltered total.

Format conventions the native parsers rely on, all read from file structure and never from answers:

- Swiss DXF: rooms are `ROOM_OUTLINE` polygons; a room number belongs to the smallest outline containing it, with its name and printed area taken from the text stack on that number. Apartments are `UNIT_OUTLINE` polygons with a residential tag (App., Whg., Appart.); a tag drawn on a dividing wall labels the nearest untagged outline within one metre. Doors are door-leaf frames. Fixtures are classified from symbol topology (bowl curve plus cistern stroke or tap circle, tub outline, closed tray); an export that draws doors and windows but has no `FIXTURE` layer draws no fixtures.
- IFC: storey scope is spatial containment, so an element inside an `IfcSpace` belongs to that space's storey. Parts nested in an element of the same class are not counted twice. Typed fixtures in IFC2X3 are identified through their type object. Rendered plan views supply drawing positions, never the count. A quantity name repeated inside one quantity set takes the later value, as IfcOpenShell's `get_psets` does, and the earlier value is kept on the object; conflicting values under different names or sets are refused. Quoted names are names: a room called 'Seminarraum Groß' is not a gross-area request, and a quoted storey such as '0' or 'Attic' scopes the question without selecting rooms of that name.
- PDF schedules: ruled tables are found from stroked line segments, header rows from heading vocabulary, then counted by code (OR within a column, AND across columns).

Measured results (development data only; the reserved holdout in `docs/evaluation/preview-reservation.json` is not used for tuning):

- Preview development split, official benchmark: Swiss 2,170 / 2,170 correct; IFC 1,029 / 1,049 correct, 0 wrong (the other 20 need an IFC file that is not in the preview); opening_design schedules 48 / 48 numeric answers correct in auto mode (35 native, 11 planner, 2 vision), plus 16 text answers for manual review.
- Full dataset, non-reserved groups, native mode with the current code: Swiss 37,386 / 37,396 correct (99.97%), 0 refused; IFC 3,018 / 3,062 correct (98.6%), 0 wrong, 44 refused (all Romanian or Polish wording, which auto mode translates with Gemini before the native solver runs).
- Known disagreements kept as they are: on three Swiss floors the answer key has one bathtub more than the drawing contains, and on two floors one room of an apartment is drawn in a separate untagged outline. Changing the rules to match these cases broke correct answers elsewhere, so we did not.
- Vision answers on unseen raster drawings are not part of these numbers. They depend on the hosted model and are reported per answer as provisional, not as a measured accuracy.

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

DWG uploads are accepted for project storage; analysis requires a supported paired export or an additional DWG conversion tool. Automatic arbitrary geometry measurement, comprehensive wall/MEP quantity extraction, scans without legible dimensions, and every exporter-specific schedule are not implemented. No fine-tuned segmentation model is currently deployed. A GPU is not needed for the current hosted-vision/native architecture.

## Data, access and costs

- Original files and generated caches remain separate. The app stores uploads, extraction caches, previews, answers and model request events under `STOA_RUNTIME_DIR`.
- SQLite defaults to WAL on a local disk. Set `STOA_SQLITE_JOURNAL=DELETE` for a compatible single-writer shared-volume deployment; do not scale multiple app replicas around SQLite.
- Set `STOA_ACCESS_TOKEN` to protect backend APIs behind a server-side proxy that supplies `X-Trace-Token`. Do not embed it or provider keys in the browser. Use HTTPS and access control for a remote workspace.
- `STOA_MAX_MODEL_CALLS` limits recorded model attempts per runtime database (default 500). It is an attempt limit, not a dollar budget. Configure a provider spending cap separately.
- Hosted model requests send selected source material to the configured OpenAI or Gemini service with `store: false`; this does not override the provider's retention terms. Native mode sends no model requests.
- Optional hosted Gemma review is a second model call, not independent verification or offline inference. Its image-coordinate constraints and source checks do not establish detection completeness.
- Dataset sources retain their respective licenses; source credits are shown in the app. The dataset is not bundled into this repository. Team code uses `LICENSE`; source-derived screenshots, benchmark questions and evidence retain the terms documented in `THIRD_PARTY_NOTICES.md` and `third_party/dataset_licenses/`.

See `DATA_INVENTORY.md` for the complete preview file inventory. The full 10 GB dataset has not been loaded.

See `ops/connection-status.json` for non-secret service setup status and deployment documentation under `ops/` when available. No API keys belong in Git.

## Source queries, review receipts and optional readers

The Gemini query planner supports groups, medians, explicit exclusions/OR filters, ratios, percentages and differences over typed source quantities. Python executes the plan; it refuses missing units or source IDs. Follow-up questions can retain the previous selection in the same drawing/region. Schedule tools support material groups, dimension filters, quantity multiplied by measured columns and exact-key cross-sheet references.

Counts can be corrected in the evidence artifact. Export CSV or the answer download saves pending changes first, then exports the saved revision. The whole-chat CSV is in Chat options and includes grouped quantities. `GET /api/answers/{id}/export?format=json|csv` returns a saved receipt; JSON includes its revision and SHA256. Stale review saves with `base_revision` receive HTTP 409.

Keep `STOA_INVENTORY_POLICY=repeat` and `STOA_SYMBOL_READER=standard` for reviewed behavior. Experimental `adaptive` and `focused` modes and the optional `STOA_DETECTOR_MANIFEST` adapter are documented in [the verification and limitations](../docs/delivery/quantity-workflow-improvements.md). The recovered PlanNet weights and focused-reader study did not improve measured detection, so neither replaces the release reader. Detector dependencies are separate in `requirements-detector.txt`; ONNX export requires a separate Torch environment and `python ops/export_plannet.py --help`. Weights and private manifests stay out of Git.

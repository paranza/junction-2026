# Trace handoff

Snapshot: **14 November 2026**, Junction 2026, Stoa challenge. This file lets a teammate continue without the original chat. Start with `README.md`, then `DATA_INVENTORY.md`, `DEMO.md`, and the final benchmark reports.

This is an engineering handoff, not a transcript. The owner will share a native Codex conversation snapshot separately.

## Goal and approach

The challenge is to answer natural-language questions about real construction drawings and BIM **accurately, with source evidence a human can check in seconds**. The team has four people and roughly 24 hours to deliver a convincing, competitive demo. Stoa specifically values approaches that remain useful as frontier models improve.

Trace combines deterministic extraction and calculations with a hosted vision fallback. The lasting work is the source-object inventory, coordinate mapping, scope controls, reproducible quantities, and review trail. The product centres on a drawing viewer and inspectable evidence.

The repository-root `INFRA/architecture_pipeline.md` is an earlier research proposal. Its CenterNet, SAM2, Gemini pipeline and unverified 99% figures do not describe the implemented Trace system or validated results. Use the code and benchmark reports in `stoa-trace/` for the current architecture and evidence.

## Repository and working deployment

- Repository: <https://github.com/paranza/junction-2026>.
- Handoff branch: `codex/stoa-competitive-upgrade`.
- Project folder inside that repository: `stoa-trace/`.
- Existing workspace: <https://stoa-86-38-182-146.sslip.io>.

The remote workspace requires HTTP Basic authentication. Obtain access from the owner through a secure channel; no password is included in this repository or this document. Its availability is a snapshot, not a service guarantee.

One Verda **CPU-TURIN.4V.16G** instance already exists: 4 vCPUs, 16 GB RAM, 55 GB disk, FIN-03, approximately **€1.35/day** for compute and disk. Caddy supplies HTTPS and authentication. The app and SQLite runtime persist under `/srv/stoa/data/runtime` on the host. **Reuse this deployment; do not provision another VM or erase its runtime database.** See `ops/DEPLOYMENT.md` before cloud work.

## What currently works

- A searchable library with collection filters and pagination; all 913 preview drawing/model files are registered.
- Multi-file upload, originals, multi-page navigation, pan/zoom, and selected-region questions.
- Native IFC counts and supported room quantities; Swiss semantic DXF room/symbol data and areas; recognized PDF schedules.
- Questions resolved through native operations first, with an OpenAI vision fallback for other supported previews.
- Normalized bounding boxes/polygons and source IDs; clicking evidence opens the relevant drawing/page or exposes BIM properties.
- Explicit requests such as **“Highlight all windows”** and **“Highlight room 5.11”** reuse constrained source selection. Objects without usable 2D locations remain source records, with an explanation.
- Count-candidate additions/exclusions, undo, saved review revisions and working quantities, and JSON export. Corrections preserve the original result and do not establish detection completeness.
- Source attribution, scope/method labels, calculations, and warnings.

## Architecture and important files

| Area | Implementation |
|---|---|
| Backend | Python/FastAPI, normally port 8787; `server/app.py` |
| Source inventory and state | `server/store.py`; SQLite, uploads, extraction caches and previews under `STOA_RUNTIME_DIR` |
| Native extraction | `server/extraction.py`; PyMuPDF, ezdxf/Shapely, IfcOpenShell, semantic SVG |
| Deterministic answers | `server/native_qa.py`; supported operations abstain when filters or scope are unresolved |
| Explicit highlighting | `server/selection.py` |
| Vision and coordinates | `server/llm.py`, `server/rendering.py`; Responses API, structured output, source records and image crops |
| Interface | React/JSX and Vite; `frontend/src/main.jsx`, `frontend/src/styles.css` |
| Evaluation | `ops/benchmark.py`, frozen `ops/benchmark-config.json`, `ops/reports/` |

Keep whole-model, visible-floor, page, and selected-region scope distinct. Preserve original room identifiers, units, GUIDs, and coordinate transforms. Unsupported filtered requests must not silently become unfiltered totals.

## Data and local startup

Only the preview is loaded: **374 JPG, 306 PNG, 123 PDF, 66 DXF, 20 DWG, 14 IFC, 10 SVG**. It includes elevations, wall/envelope/foundation details, schedules, historic scans and plumbing BIM, as well as floor plans. Multiple exports of one drawing count separately. Content extraction and rendering are lazy.

**The full 10 GB dataset has not been downloaded or imported.** The dataset and runtime are excluded from Git. If the preview is unavailable locally, download and extract:

<https://fwjydgxpttajiqpfmqtj.supabase.co/storage/v1/object/public/stoa-junction-2026/junction-dataset-preview.zip>

Keep dataset files out of version control. The portable default is `./datasets/junction-dataset-preview`; an existing external directory also works through `STOA_DATA_ROOT`. It must contain `data/` and `questions.jsonl`. Respect the supplied per-source licences and attribution.

Use **Python 3.11** (tested with 3.11.3), **Node 22.14.0**, and **npm 10.9.2**. Run commands from `stoa-trace/`. Virtual-environment activation is not required.

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python ops/refresh_local.py
if [ ! -f .env ]; then cp .env.example .env; fi
# Edit the private .env: set STOA_DATA_ROOT and a NEW local STOA_RUNTIME_DIR.
# Also set STOA_MAX_MODEL_CALLS=50 explicitly.
.venv/bin/python ops/start_local.py
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env: set your data directory, a NEW local runtime directory, and the 50-attempt cap.
.\.venv\Scripts\python.exe ops/start_local.py
```

The PowerShell commands were reviewed but not executed on a Windows machine during this handoff.

For later code updates, stop the local server, run `ops/refresh_local.py` with the virtual environment's Python, then start it again. That helper refreshes Python dependencies and rebuilds the frontend; it preserves dataset/runtime files. `run.sh` is also a macOS/Linux bootstrap wrapper.

Open <http://127.0.0.1:8787>, or the host/port selected in `.env`. `ops/start_local.py` loads those settings before starting Uvicorn. Native mode needs no model key. For visual analysis, use your own `OPENAI_API_KEY` or an owner-provided key received securely, stored in private configuration. Never put credentials into chat, source code, prompts, screenshots, or Git.

The deployed runtime is capped at **50 recorded model attempts**. The code fallback is 500, so configure 50 explicitly for a new runtime. This is an attempt cap, not a monetary budget; preserve existing counters and honour the owner's spending limits. Do not assume every model request is free.

At this snapshot the owner's configured OpenAI key expires **20 November 2026** and the Verda provisioning credential **16 November 2026**. Those credentials and the private SSH/deployment/access files are **not included**. Credential expiry does not itself stop the existing VM; future cloud management may need renewed access.

## Verification and honest claims

The competitive upgrade adds native quantity/source guards, cached visual inventories, manual additions and complete review history, saved working quantities, source-change warnings, and source-aware preview caching. It passed 80 Python tests, 11 frontend tests, a production frontend build, and browser checks for evidence focus, additions/exclusions, saved revisions and working quantities across reloads. Live model calls were disabled during these upgrade checks. See `README.md` and `ops/reports/competitive-upgrade/` for current results. Re-run locally after changes:

```sh
.venv/bin/python -m unittest discover -s tests -v
npm --prefix frontend test
npm --prefix frontend run build
.venv/bin/python ops/benchmark.py --dry-run
.venv/bin/python ops/benchmark.py --mode native --suite full
```

The handoff checkout also passed a clean dependency install and frontend build, manifest validation against the separately supplied preview, and a fresh local backend check with model access disabled: 913 files, Opening Design's 81 files, a PNG preview, 13 window highlights and one room highlight. Windows commands are reviewed but were not executed on Windows. The GitHub Actions definition is included as `ops/ci/github-actions.yml.example`; it is not active because the publishing credential lacks GitHub's `workflow` scope. A suitably authorized maintainer can enable it later without changing the test commands.

On Windows, replace `.venv/bin/python` with `.\.venv\Scripts\python.exe` in these checks.

The upgraded frozen 50-case diagnostic has **30/50 answered**, including **28/28 answered numeric questions matching supplied labels** and two text answers requiring manual review. Across all 44 numeric cases, it is **28/44** because abstentions count as failures. The paired disjoint-group native evaluation improves from **41/97 to 55/97** correct numeric questions, with three incorrect numeric answers remaining. The separate three-call vision check had **2/3 correct**: two areas correct, one window count wrong and flagged for review. These samples do not establish general or competition accuracy. Coordinate validation does not establish citation correctness.

The frozen manifest defaults to `./datasets/junction-dataset-preview`. Pass `--dataset-root` with your own location when using another preview directory. Historical report metadata can contain the original machine's paths; those paths are not required for setup.

Read `ops/reports/competitive-upgrade/` for the paired native evaluation and updated diagnostic, and `ops/reports/benchmark-vision-3.json` for the earlier visual cases and limitations. The benchmark defaults to native mode. Paid modes require `--allow-paid` and at most five questions per invocation; that guard does not grant a spending allowance.

**Gold-label boundary:** supplied answers belong only in evaluation/config/report files. Never put `questions.jsonl` answer labels, expected values from the frozen manifest, or benchmark results into extraction, model prompts, retrieval indexes, or training. Example-question wording is exposed separately.

## Remaining work and limits

Prioritise the demo in `DEMO.md`, reliable evidence interaction, and failure cases that the team can evaluate independently. DWG analysis needs a converter or supported export. IFC has native records and supplied 2D projections, **no general 3D viewer**. There is no fine-tuned segmentation model or GPU dependency. General geometry measurement, complete wall/MEP takeoffs, illegible scans, and arbitrary schedules remain incomplete. Some source models have missing paired views or ambiguous scope.

The intended next step is to run the existing app locally, verify the demo and current tests, inspect concrete gaps, and agree the next implementation slice with the teammate. Preserve others' work and the running shared deployment.

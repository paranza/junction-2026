# Prompt for a new Codex session

Copy the text below into a new Codex session with access to the cloned repository.

---

Continue our **Metria** project (formerly Trace) for the Junction 2026 **Stoa challenge**. Use an attached shared-chat snapshot as background if provided, and establish the current implementation from the repository before changing code. A snapshot does not transfer the original agent's tools, files, running processes or credentials.

We are four people with roughly 24 hours, aiming for a competitive demo. The challenge is to answer natural-language questions about construction drawings and BIM accurately and verifiably, showing exactly which drawing objects or source values support an answer. We want durable source extraction, geometry, scope controls and human verification that remain useful as models improve.

Repository: <https://github.com/paranza/junction-2026>, branch **`codex/stoa-competitive-upgrade`**, project subfolder **`stoa-trace/`**. If you need a fresh checkout:

```sh
git clone --branch codex/stoa-competitive-upgrade --single-branch https://github.com/paranza/junction-2026.git
cd junction-2026/stoa-trace
```

If a checkout already exists, inspect its branch and working tree first. Do not overwrite another teammate's edits.

Read **README.md, HANDOFF.md, DATA_INVENTORY.md, DEMO.md**, then the final native and vision reports under `ops/reports/`. Read any applicable `AGENTS.md`. Inspect the implementation rather than assuming this summary matches every later commit.

Repository-root `INFRA/architecture_pipeline.md` is an earlier proposal. Its CenterNet/SAM2/Gemini design and unverified 99% claims are not implemented Metria features or benchmark results. This handoff captures engineering context; the owner will share a native Codex conversation snapshot separately.

Current architecture: FastAPI on port 8787; React/JSX and Vite; SQLite with a separate persistent runtime; PyMuPDF, ezdxf/Shapely and IfcOpenShell for native extraction; hosted OpenAI Responses vision for other supported previews. Keep native calculations, visual candidates, and human-reviewed results distinguishable.

The interface includes collection filters/search, upload, page navigation, pan/zoom, selected-region questions, evidence inspection, explicit highlight commands such as “Highlight all windows” or “Highlight room 5.11,” count-candidate correction, saved history and JSON export. Whole-model, visible-floor, selected-page and selected-region queries must preserve their scopes. Do not silently discard unsupported filters and return a broader total.

**Start locally with a fresh runtime.** Use Python 3.11 (tested with 3.11.3), Node 22.14.0 and npm 10.9.2. Follow the activation-independent macOS/Linux or Windows PowerShell commands in HANDOFF.md. The entry point is `ops/start_local.py`, run with the virtual environment's Python; it loads host/port settings from `.env` before Uvicorn. Use `ops/refresh_local.py` to refresh dependencies and rebuild the frontend after code updates. Set your `STOA_DATA_ROOT` and a new local `STOA_RUNTIME_DIR` in private `.env`, and explicitly set `STOA_MAX_MODEL_CALLS=50`. Native mode works without an API key. Use your own API key or one the owner provides through a secure channel; never request or paste credentials in chat, commit them, or print them.

The dataset is excluded from Git. The preview contains **913 registered files**: 374 JPG, 306 PNG, 123 PDF, 66 DXF, 20 DWG, 14 IFC and 10 SVG. It includes elevations, sections, envelope/foundation details, schedules, historic scans and plumbing models, not just floor plans. Several files are exports of the same drawing. Extraction/rendering happen on demand.

If the preview is not already available, download and extract this explicit public URL into a data directory excluded from Git. The portable default is `./datasets/junction-dataset-preview`, and an existing external directory also works:

<https://fwjydgxpttajiqpfmqtj.supabase.co/storage/v1/object/public/stoa-junction-2026/junction-dataset-preview.zip>

Point `STOA_DATA_ROOT` at the folder containing `data/` and `questions.jsonl`. Preserve source licences/credits. **Do not download the full 10 GB dataset as an automatic setup step; it is not currently loaded.**

Last reported verification: **80 Python tests and 11 frontend tests passed**, with a successful frontend build and browser checks of saved reviews and working quantities across reloads. The upgraded frozen native diagnostic answered **30/50** cases; **28/28 answered numeric questions** matched their labels, while accuracy across all numeric cases was **28/44**. Two text answers need manual review. A separate paired 100-case evaluation improved numeric correctness from **41/97 to 55/97**, with three incorrect numeric answers remaining. Earlier vision examples produced **2/3 correct**, with a cropped-window overcount flagged for review; the new visual inventory's live accuracy remains unmeasured. These are limited diagnostics, not general accuracy claims. Read `ops/reports/competitive-upgrade/` and rerun native checks after changes. Pass the evaluator `--dataset-root` with your own preview directory when checking its source-label hash.

Do not send supplied gold answers, benchmark expected values, or evaluation results into inference prompts, retrieval indexes, native extraction or training. The benchmark is an evaluator, not an answer lookup. Preserve the frozen selection when comparing changes. Start with zero-API native tests; any paid testing must stay within the owner's authorised budget and the configured attempt cap.

Existing remote app: <https://stoa-86-38-182-146.sslip.io>, protected by HTTP Basic authentication. Obtain access securely from the owner if needed. It already runs on a Verda CPU VM with **4 vCPUs, 16 GB RAM and 55 GB disk**, costing approximately **€1.35/day**. **Do not provision a duplicate VM, wipe/reset the shared SQLite database, replace its persistent runtime, or reset model-call counters.** Read `ops/DEPLOYMENT.md` before coordinating any deployment. No cloud credentials, runtime keys, SSH keys or access passwords are included. At handoff, the owner's OpenAI key expires 20 November 2026 and Verda provisioning credential 16 November 2026; verify current access rather than assuming they remain usable.

Known limits: DWG requires conversion/export; IFC provides native data and linked 2D views, not a general 3D viewer; no trained segmentation model or GPU is deployed; complete geometry measurement and wall/MEP takeoffs are unfinished. Visual counts can miss or misclassify objects. A valid box does not prove a citation or detection completeness.

After reading the files, boot the local app, run the tests and dry-run/native benchmark, and check the demo end to end. Give me a concise assessment of what works and the highest-value remaining gap, then continue the implementation slice I request. You are not alone in the repository: preserve others' work and keep changes reviewable.

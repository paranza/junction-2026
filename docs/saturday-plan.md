# Saturday plan

Updated 14 November 2026, 09:50 Helsinki, after Riccardo's Trace handoff (`stoa-trace/`, commit 35a663f) and Michele's overnight work (now on main in `Michele-testing/`). This replaces the 02:15 version. Every number below was measured this morning on Matteo's laptop unless it says otherwise.

**In one line:** Trace is our product. Keep its viewer, evidence, review trail and Verda deployment as they are, and raise how many questions it answers. Plug last night's EDA solvers into its native layer, add a question normalizer so all seven languages reach them, and give cubicasa one cached detection call per image. Score every change on all 7,990 questions: a full run takes 90 seconds.

## 1. Where Trace stands

Trace's own evaluator (`ops/benchmark.py`, native mode, no API key, 0 model calls) on all 7,990 preview questions:

| Source | Questions | Answered | Correct | Last night's EDA scripts |
| --- | ---: | ---: | ---: | --- |
| cubicasa5k | 4,270 | 0 | 0 | Needs vision. Careful counting by eye: about 85% |
| swiss_dwellings | 2,358 | 1,164 | 1,105 | 2,358 / 2,358 |
| ifc_models | 1,049 | 505 | 483 | 1,025 / 1,025 testable |
| ifc_bench | 249, free text | 1 | Not auto-scored | 35 / 39 reproduced on a sample |
| opening_design | 64 | 12 | 10 | 60 / 64 |
| **Total** | **7,990** | **1,682 (21%)** | **1,598** | |

When Trace gives a number it is right 95% of the time. Precision is fine; coverage is the problem. It abstains on 79% of questions. The causes, each checked in the code or the results:

1. **Only English reaches the native solvers.** The question checks are English word lists. Correct answers by language: English 1,523 of 3,887 numeric questions, Finnish 0 of 2,135, French 0 of 395, Danish 0 of 197, German 20 of 422, Estonian 17 of 315, Italian 38 of 374. Translated questions have the same answers as their English twins.
2. **cubicasa has no native path, and even with an API key most of its questions skip the cached inventory.** `count_category` (`server/inventory.py:43`) accepts a question only if it names exactly one category in plain words. Of the 24 cubicasa question variants (12 templates, English and Finnish), only windows (both languages) and saunas (English) qualify: 647 of 4,270. The other 3,623 would each trigger a separate general model call. "How many floors" (482 questions) and "separate WC rooms" (224) have no category at all.
3. **One bug blocks 64 English swiss questions.** "Net floor area of apartment B (C, D, ...)": the word check at `server/native_qa.py:78` allows "a" as an article, so apartment A passes and every other letter is rejected.
4. **Labels containing an apostrophe break the quote parser** (`native_qa.py:103`): 14 questions about 'Cage d'escalier'.
5. **Three swiss rules disagree with the answer key.** Doors are overcounted by 1 to 9 on 28 of 65 floors. Apartments are one too many on 8 of the 10 misses (the EDA counts only App., Whg. and Appart. tags, not commercial units). The indoor-total net area is wrong on 10 floors. The EDA solver gets all three right.
6. **IFC.** 24 room areas unanswered and 9 wrong (the EDA falls back to floor-face geometry when NetFloorArea is missing); slab volumes unanswered; stairs wrong on 4 of 9; whole-model counts asked in Estonian get the wrong scope (for example 42 doors instead of 211).
7. **opening_design.** Schedules work only in the A-801 layout; the Cannery Trail sheets and enlarged plans abstain.
8. **ifc_bench.** Free-text answers need a model writing from IFC query results. Trace has no such path.

If the EDA results carry over, the native layer alone goes from 1,598 to about 3,400 correct numeric answers, still with no model calls. cubicasa decides the rest: every 10 points there is 427 questions, about 5% of the set.

## 2. What to build today, in order

**First, Michele's overnight work.** It was a second app in `Michele-testing/`, removed from main on 14 November after the team chose Trace; the last commit containing it is `a4bd811`. Its notes (`Michele-testing/docs/evaluation.md`; not re-run by us) report:
- an exact swiss DXF parser: 1,614 / 1,614 counts and 732 / 744 areas across English, German, French and Italian, tuned on these same questions;
- question templates in English, German, French, Italian and Finnish;
- that CubiCasa5K's own annotations reproduce 4,210 of the 4,270 cubicasa answers (98.6%), so the cubicasa answer key almost certainly comes from them;
- small CPU models trained from scratch (PlanNet for symbols and rooms, GlyphNet for words). The CubiCasa model trains on about 4,700 public CubiCasa5K plans, with the 241 preview plans held out. Held-out results are pending.

Proposal for the team: one product, Trace. Port the DXF parser and the templates into Trace rather than rewriting them; they cover much of items 1 and 2 below. Add the raster model to the cubicasa bake-off as arm (d) once it has held-out numbers. Before relying on it, ask Stoa (section 7, question 4): if the hidden test images also come from public CubiCasa5K, training on CubiCasa5K means training on test images and their answers.

| # | Change | Where in Trace | Questions at stake | Owner |
| --- | --- | --- | ---: | --- |
| 1 | Question normalizer: rewrite each non-English question into the English wording the native layer already supports, copying labels verbatim | New `server/normalize.py`, called at the start of `_compute_analysis` (`server/app.py:319`) | About 1,700 swiss and IFC, plus the 2,135 Finnish cubicasa twins | Matteo |
| 2 | Swiss: the apartment-letter and apostrophe fixes first (about 78 questions), then the EDA rules for doors, apartments and indoor totals | `native_qa._native_cad`; `extraction._dxf`, `_pdf` | About 1,250 with item 1 | Michele |
| 3 | cubicasa: a table mapping the 12 templates to categories, new floors and WC-room categories, combined categories, one cached inventory per image, the window rule by drawing style | `inventory.py`: `count_category`, `CATEGORIES`, `SYSTEM`, `page_inventory` | 4,270 (53%) | Matteo |
| 4 | IFC: floor-face fallback for room areas, slab volumes, stairs, whole-model scope in other languages | `native_qa._native_ifc`, `_ifc_scope`; `extraction._ifc_explicit_quantities` | About 540 | Michele |
| 5 | opening_design schedules from the EDA (sum the Count column, answer from the revision in the path) | `extraction._word_schedules`, `native_qa._native_schedule` | About 50 | Michele |
| 6 | ifc_bench free text, written by a model from IFC query results | New path | 249 | Whoever is free after 18:00, and only once Stoa says how text is graded |
| 7 | Batch answer runner | `ops/` | | Riccardo, only if Stoa will run a hidden question set |

**Normalizer.** Start deterministic, from Michele's templates (removed from main on 14 November; read it with `git show a4bd811:Michele-testing/backend/stoa/questions.py`); Estonian and Danish still need adding. The non-English questions are generated twins of the English templates and sit next to their twin in `questions.jsonl`, so build a pattern table from the question wording. Never read the answers to build it. For phrasing the table does not know, fall back to Trace's existing `llm.translate_question` (`server/llm.py:124`), cached on disk, and accept the result only if every quoted label in the original appears verbatim in the translation. Today that translation runs only in automatic mode with a model key. Show "Interpreted as: ..." in the answer panel.

**cubicasa.**
- Keep Trace's rule: the count is the number of located boxes, never a number the model states.
- A typical cubicasa image (median 876 px) goes to the model as one overview at `high` detail with no crops, because crops start above 1,600 px (`server/rendering.py:98`). Test 2x upscaled, overlapping crops for the small symbols.
- With crops, merge duplicates by intersection over the smaller box instead of IoU above 0.65 (`inventory.py:123`). A symbol cut by a crop edge leaves a partial box that IoU does not match.
- Floors: answering 1 is right on 80% of images, and the EDA's blob counting only matched that. Ask the inventory to box each separate floor drawing.
- Bake-off by 12:00 on 40 dev images, every answer cached: (a) the current inventory, (b) with upscaled crops, (c) Gemini tiled detection from the EDA scripts, and (d) Michele's PlanNet once its held-out numbers exist. Keep the winner per category, and add a new provider only if it wins clearly.
- One inventory call answers all of an image's questions, about 18 on average: 241 calls for the preview instead of about 3,900 with today's routing. That is also our cost story.

## 3. First 30 minutes

- [ ] **Pull main.** One branch per task, small PRs.
- [ ] **Get the dataset outside iCloud.** This morning iCloud had offloaded 850 of the 925 files in the Desktop `preview_dataset` again (52 MB left on disk). Download the public preview instead (500 MB, about a minute):

```sh
mkdir -p ~/stoa-data && cd ~/stoa-data
curl -fL -o preview.zip "https://fwjydgxpttajiqpfmqtj.supabase.co/storage/v1/object/public/stoa-junction-2026/junction-dataset-preview.zip"
unzip -q preview.zip   # creates junction-dataset-preview/ with data/ and questions.jsonl
```

- [ ] **Run Trace.** Checked on macOS with Python 3.12.7: the pinned requirements install and all 80 tests pass in about 4 seconds. Not checked on this Mac: the frontend build (Trace pins Node 22.14.0).

```sh
cd stoa-trace
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env:
#   STOA_DATA_ROOT=~/stoa-data/junction-dataset-preview
#   STOA_RUNTIME_DIR=~/stoa-data/runtime    (keeps SQLite out of iCloud)
#   STOA_MAX_MODEL_CALLS=50
.venv/bin/python -m unittest discover -s tests
.venv/bin/python ops/start_local.py         # backend on 127.0.0.1:8787
```

- [ ] **Reproduce the baseline** in a second terminal while the backend runs:

```sh
cd stoa-trace
echo '{"cases": []}' > ~/stoa-data/no-exclusions.json
.venv/bin/python ops/grouped_manifest.py --dataset-root ~/stoa-data/junction-dataset-preview \
  --exclude-manifest ~/stoa-data/no-exclusions.json --count 100000 --max-per-group 100000 \
  --languages all --output ~/stoa-data/eval-full.json
.venv/bin/python ops/benchmark.py --manifest ~/stoa-data/eval-full.json --mode native \
  --max-questions 100000 --dataset-root ~/stoa-data/junction-dataset-preview \
  --output ~/stoa-data/reports/native-full-$(date +%H%M).json
```

  Expect 7,990 cases with `cases_sha256` starting `29c62329`, then 1,682 answered and 1,598 correct. The `.md` next to the JSON has per-source and per-type tables; per-language results are under `by_language_hint` in the JSON. The manifest holds every answer label: keep it out of Git.
- [ ] **Model access (Matteo and Riccardo, 5 min).** Trace's vision calls OpenAI (`gpt-6-astra`, Responses API). The key goes in a private `.env` or `~/.config/stoa-junction-2026/secrets.env`. Riccardo's key is the only one confirmed. Matteo needs a development key for cubicasa; Michele's work needs none. Use the Gemini credits only for the bake-off. Keys never go in Git, chat or screenshots.
- [ ] **Licence (Riccardo).** PyMuPDF, which is AGPL-3.0, is now a core dependency of Trace's extraction (see `THIRD_PARTY_NOTICES.md`), while team code is MIT. Ask the organizers whether that is acceptable. Replacing it would take most of a day, so don't unless they require it.
- [ ] **Stoa booth (Riccardo).** The questions in section 7.
- [ ] **File ownership** to avoid conflicts in three large files: Matteo owns `server/inventory.py`, `llm.py`, `rendering.py` and the new `normalize.py`; Michele owns `native_qa.py`, `extraction.py` and `verification.py`; Antonio owns `frontend/`; Riccardo owns `app.py`, `store.py`, `ops/` and deployment. The two-line normalizer hook in `app.py` goes through Riccardo.

## 4. Who builds what

| Person | Owns today | By 12:00 | By 18:00 |
| --- | --- | --- | --- |
| Matteo | Normalizer, cubicasa vision path | Normalizer merged; non-English swiss and IFC answers rise toward their English rates | Template table and bake-off winner in `inventory.py`; cubicasa scored on the dev images and the holdout, with model calls and cost |
| Michele | Native solvers | Apartment-letter and apostrophe fixes merged | Swiss doors, apartments and totals; IFC areas and scope; opening_design schedules |
| Antonio | Interface | Evidence legible at fit-to-page zoom; one status chip per answer | Area answers with filled polygons; cost per answer; demo presets |
| Riccardo | Merges, scoreboard, Stoa, deployment, demo | Baseline posted, holdout frozen, Stoa answers in `docs/decisions.md` | Morning merges deployed to Verda; demo script drafted |

**Antonio, in order.** The partner asked for a simple interface that shows visually why an answer is right (`docs/challenges.md`).
1. Evidence legibility. In the handoff screenshot (`frontend/qa/reviewed-history.jpg`) 36 numbered circles cover the rooms at 31% zoom. Zoom to the evidence when an answer arrives, draw thin outlined boxes, show numbers on hover or when zoomed in, and link hover between the list and the drawing.
2. One status chip per answer with three states: "From source" (native), "Model reading, check it" (vision), "Not answered". Put the long warnings behind a Details toggle.
3. Area answers: fill the room polygons and show the sum as clickable terms (room 5.11: 13.62 m²).
4. Cost per answer next to the answer: model calls and estimated dollars (native answers show 0 calls). Set the `STOA_*_USD_PER_MILLION` rates in `.env` so estimates appear. `INFRA/architecture_pipeline.md` records low inference cost as one of four equally weighted criteria in the challenge brief.
5. An "Interpreted as" line for normalized questions.
6. Demo presets: the five questions in `DEMO.md` plus one cubicasa question, one click each. Keep the 11 frontend tests passing.

**Riccardo, in order.**
1. Merge captain. Check each PR against the rule in section 6, merge, rerun the baseline and post the per-source and per-language lines in the team chat.
2. Freeze a holdout of about 15% of drawing groups now, with a fixed seed. Nobody debugs on it until Sunday. In the pitch, quote the holdout and say the rest was used for development.
3. Stoa and licence questions; record the answers in `docs/decisions.md`.
4. Deploy merges to the existing Verda VM at 13:00, 18:00 and Sunday 07:00 (`ops/deploy_verda.py sync`, then `start`; check with `ops/verify_remote.py --exercise`). Never create a second VM or reset the runtime.
5. If Stoa runs a hidden set: a batch runner in `ops/` that reads (path, question) rows and writes answers with evidence.
6. Demo script, 2-minute video and submission text, led by measured numbers: questions answered, correct, model calls and cost per answer.

## 5. Reading, done by about 09:45

**Everyone first (15 min):** `stoa-trace/README.md`, `HANDOFF.md` and `DEMO.md`, then ask demo question 1 in the running app.

### Matteo (about 70 min)

| # | Read | Min | What to read | Why |
| --- | --- | --- | --- | --- |
| 1 | Trace `server/inventory.py` (whole), `rendering.py` `image_inputs`, `llm.py` `_request` and `answer_with_model` | 25 | All of it | Every cubicasa answer will come from here: `count_category`, one cached call per page, the IoU merge. |
| 2 | [OpenAI: Images and vision](https://developers.openai.com/api/docs/guides/images-vision) | 8 | "Choose an image detail level", "Model sizing behavior" (the gpt-6-astra row), "Limitations" | `high` caps an image at 2,500 patches of 32 px; `original` keeps full size up to 30,000 patches. The guide lists counting and precise localisation as weaknesses, so count boxes and review them. |
| 3 | [AECV-Bench (arXiv 2601.04819)](https://arxiv.org/pdf/2601.04819v1) | 10 | 3.1.2, Table 1, the failure-mode paragraph in 4.1.1 | Whole-plan counting scores about 0.39 on doors and 0.34 on windows; room labels are read well. Symbols need crops, labels do not. |
| 4 | [CubiCasa5K paper](https://arxiv.org/pdf/1904.01920), Section 3 and Table 4; [repo](https://github.com/CubiCasa/CubiCasa5k) `floortrans/loaders/house.py`, icon maps | 14 | As listed | What "one window" or "one sink" means in the annotations: DoubleSink is one sink, Urinal maps to Toilet. |
| 5 | [Gemini: Image understanding](https://aistudio.google.com/docs/image-understanding) | 6 | "Object detection" only | For bake-off arm (c). `box_2d` is [ymin, xmin, ymax, xmax] on 0 to 1000. |
| 6 | [Hamel Husain: Evals FAQ](https://hamel.dev/blog/posts/evals-faq/) | 8 | "Error analysis", "binary pass/fail" | The loop: read 30 wrong answers per category, fix the biggest failure bucket, rerun from cache. |

### Michele (about 70 min)

| # | Read | Min | What to read | Why |
| --- | --- | --- | --- | --- |
| 1 | Trace `server/native_qa.py` | 20 | Whole file (615 lines) | Every rule you port lands here. A handler returns None to abstain; the word lists decide what reaches it. |
| 2 | Trace `server/extraction.py` | 20 | `_pdf`, `_word_schedules`, `_dxf`, `_swiss_fixtures`, `_project_dxf_to_pdf`, `_ifc_explicit_quantities`, `_ifc` | The records your rules read. Swiss counts come from the DXF here; the EDA used PDF paths. |
| 3 | EDA `swiss_dwellings/pdf_solver.py`, `ifc_models/final_solver.py` | 10 | The rules for doors, apartments, totals; the floor-face fallback | These reproduce the answer keys. |
| 4 | [ifcopenshell.util.element](https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/element/index.html) | 12 | `get_psets(qtos_only=True)`, `get_container`, `get_aggregate`, `get_decomposition` | Spaces hang under storeys by aggregation, so `get_container(space)` returns None. |
| 5 | [PyMuPDF: Page](https://pymupdf.readthedocs.io/en/latest/page.html) | 8 | `get_drawings`, `get_text`, `remove_rotation` | 31 of 55 opening_design sheets are rotated. |

Only if you take ifc_bench: the [IFC-Bench judge prompt](https://github.com/sylvainHellin/ec3-2026-hellin-fuchs-nousias-borrmann/blob/main/prompts/answer_verifier.baml) (8 min).

### Antonio (about 35 min)

| # | Read | Min | Why |
| --- | --- | --- | --- |
| 1 | `stoa-trace/DEMO.md`, then run its five questions in the app | 15 | The flows the judges will see. |
| 2 | `docs/challenges.md`, "Partner discussion" | 2 | What Stoa asked for. |
| 3 | [Shape of AI: Citations](https://www.shapeof.ai/patterns/citations) | 4 | Every answer links to its exact region; an explicit "could not verify" state. |
| 4 | [NN/g: Explainable AI](https://www.nngroup.com/articles/explainable-ai/) | 6 | Evidence next to the number, and which method produced it. |
| 5 | [Google PAIR: Explainability and Trust](https://pair.withgoogle.com/chapter/explainability-trust/), part 3 | 8 | Three status chips, each tied to an action. |

### Riccardo (about 30 min)

| # | Read | Min | Why |
| --- | --- | --- | --- |
| 1 | `docs/submission.md`, `docs/demo.md` | 6 | Sunday 09:00 deliverables. |
| 2 | [Hamel Husain: Evals FAQ](https://hamel.dev/blog/posts/evals-faq/), "Error analysis" | 8 | How to run the scoreboard. |
| 3 | [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | 12 | Code graders for numeric answers; the benchmark becomes the regression suite. |
| 4 | [Devpost: hackathon demo](https://info.devpost.com/blog/how-to-present-a-successful-hackathon-demo) | 3 | Open on a real drawing and question, end on the evidence. |

## 6. Rules

Trace's rules, kept:
- Answer labels stay in the evaluation files under `ops/`. Never in extraction, prompts, indexes, training or the normalizer's pattern table.
- Abstain rather than return an unfiltered total. Keep model, floor, page and region scopes separate.
- A count is the number of evidence objects. A model's stated total is never used.

From the EDA:
- Merge crop and tile boxes by intersection over the smaller box, smallest box first.
- Cache every model call so reruns are free. Trace caches answers and inventories in `STOA_RUNTIME_DIR`.
- Normalise text with NFKC and handle `'...'`, `«...»`, `„...“` and apostrophes inside labels.
- With 30 to 50 questions per category, accuracy moves 14 to 18 points by chance. Compare changes on the same questions.

For every PR: the 80 tests pass, the full benchmark runs, the per-source line goes in the PR, and no source loses correct answers.

## 7. Ask Stoa (ranked)

Already answered on Friday (`docs/challenges.md`): keep the interface simple and show visually why an answer is right; solve a specific technical task, especially metric and material measurements; their internal model performs poorly.

Still open:
1. How is accuracy judged: a hidden question set run through our system (by URL or a batch file), the demo only, or both? At test time, do we get only `path` and `question`, or also `type`, `unit` and the sibling files (DXF, SVG, parent IFC)?
2. How is inference cost judged: per question, per drawing or in total? Do cached calls count?
3. How are free-text answers graded (ifc_bench, opening_design text)?
4. The cubicasa5k answers match the public CubiCasa5K annotations (98.6% in Michele's check). May we train on CubiCasa5K, and are the hidden test images part of it?
5. Windows: openings or panes? On sheets with several apartments, only the target apartment?
6. Are the duplicate door and window records in swiss_dwellings intended?
7. Will the scans have questions?

## 8. EDA code to port

The EDA scripts are in `eda/` (see `eda/README.md`); the reading-list checks are in `eda/research/`. They score themselves against the answer labels: port the rules, never the label reading.

| EDA file | Goes into Trace at |
| --- | --- |
| `eda/swiss_dwellings/pdf_solver.py` (doors, apartments, totals) | `native_qa._native_cad`; `extraction._dxf` or `_pdf` |
| `eda/ifc_models/final_solver.py`, `model_facts.py` | `native_qa._native_ifc`, `_ifc_scope`; `extraction._ifc_explicit_quantities` |
| `eda/opening_design/tables_auto.py`, `reproduce.py` | `extraction._word_schedules`; `native_qa._native_schedule` |
| `eda/ifc_bench/reproduce.py`, `sweep.py` | The new free-text path |
| `eda/research/vision-check/scripts/gemini_detect.py`, `tile_merge_count.py` | Bake-off arm (c); the smaller-box merge in `inventory.page_inventory` |
| Michele's `vector_dxf.py` and `questions.py` (archived: `git show a4bd811:Michele-testing/backend/stoa/<file>`) | `native_qa._native_cad` and the normalizer |
| `eda/cubicasa5k/` sample sheets and window notes | The window rule by drawing style and the test images for the bake-off |

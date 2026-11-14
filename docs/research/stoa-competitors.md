# Public Stoa project assessment

Refreshed **14 November 2026, approximately 09:33-09:40 Europe/Helsinki / 07:33-07:40 UTC**. This is public-source research, not independently rerun competitor evaluation. The [snapshot](stoa-competitor-snapshot.json) records exact HEADs and check times. Our comparison version is `35a663f`.

## What changed since the first pass

Three of the original seven tracked implementation HEADs changed: **Hour49/Junction26, Akshaz7/junction and 13032585789-spec/Trace**. Their [original HEADs](initial-heads-2026-11-13.json) were checked at 23:33 UTC on 13 November. Drawing Desk, NiceK1, Metsatalo and SpaceLens retained those HEADs at this refresh. Leargas, tstst334 and the Yue-fy watchlist also retain their earlier inspected HEADs.

**Lorikjashari/stoa has become a Stoa implementation**, superseding its earlier AfterQuery/ProcureBench exclusion. **Georgia-coderok/okstoa-try1** and **lalashutosh/blueprint** are newly discovered related public projects. We now track **13 challenge-related repositories**, including design documents, mocks and scaffolds, plus **two watchlist repositories**. That is not a count of 13 independently registered competing teams.

The most consequential changes are Hour49's raster and conflict improvements, Plumbline's native/raster hybrid, and Hologram's expansion into a full interface with linked 2D/3D evidence. Our earlier statements that these projects had no raster capability, no conflicts or no UI are historical and must not be used as current comparisons.

## Repository map

Commit times below are UTC. Repository `pushed_at` is a separate signal and may include activity outside the default branch. Neither proves deployment time.

| Repository | Public evidence at inspected HEAD | HEAD | Latest commit UTC |
| --- | --- | --- | --- |
| [Hour49/Junction26](https://github.com/Hour49/Junction26) | Countersign: extraction, raster readers, quantity pipeline, review/signoff, API and React interface | `e5c11b5` | Nov 14 07:17:24 |
| [lorikjashari/stoa](https://github.com/lorikjashari/stoa) | Plumbline: native solvers, hybrid raster counts, constrained planner, linked 2D/3D | `35586e7` | Nov 14 07:12:49 |
| [Akshaz7/junction](https://github.com/Akshaz7/junction) | Hologram: plan maps, vision, FastAPI/PostgreSQL, web 2D/3D and native iPhone AR code | `ee7f719` | Nov 14 07:21:28 |
| [13032585789-spec/Trace](https://github.com/13032585789-spec/Trace) | Structured quantity engine and cached raster vision; no frontend in this repository | `f99d725` | Nov 14 00:49:01 |
| [aapolipponen/drawing-desk](https://github.com/aapolipponen/drawing-desk) | Native IFC/DXF quantity tools, selective vision and marked evidence | `072608f` | Nov 13 21:35:33 |
| [NiceK1/stoa-spike](https://github.com/NiceK1/stoa-spike) | Geometry/quantity spike, raster answer caching and scorer | `37df416` | Nov 13 21:32:39 |
| [chaowang0524/metsatalo-stoa](https://github.com/chaowang0524/metsatalo-stoa) | Tool-routed Python quantity backend, deterministic terminal answers, vision fallback | `8ea707c` | Nov 13 20:59:15 |
| [JUNCTION26/SpaceLens](https://github.com/JUNCTION26/SpaceLens) | Browser-first drawing/2D/3D product and printed-text quantity answers | `94a9f6e` | Nov 13 21:34:33 |
| [Georgia-coderok/okstoa-try1](https://github.com/Georgia-coderok/okstoa-try1) | Tool-calling agent over a hardcoded mock database | `e463299` | Nov 14 00:54:01 |
| [lalashutosh/blueprint](https://github.com/lalashutosh/blueprint) | PlanGraph design and evaluation plan; no executable implementation | `2335744` | Nov 14 02:14:55 |
| [markmannion/leargas](https://github.com/markmannion/leargas) | BlueprintTrace voice/evidence plan; public tree is README-level | `386cb5a` | Nov 13 21:56:07 |
| [tstst334/junction](https://github.com/tstst334/junction) | Explicit challenge README and empty scaffold | `e2a5cfb` | Nov 13 21:01:28 |
| [d-malkov-iprally/ChatChTG](https://github.com/d-malkov-iprally/ChatChTG) | Drawing-chat description and Stoa dataset-download setup | `4778784` | Nov 13 20:24:49 |

The PlanGraph commit timestamp is later than the API's reported push timestamp. Both are retained without inferring a chronology from that inconsistency. A validated HEAD is the comparison anchor.

## Material overnight changes

### Countersign: Hour49/Junction26

Previously the pipeline was largely vector-PDF focused, with raster F1 and detected real conflicts reported as zero. The current tree includes raster components, IFC extraction, PDF tables, review/signoff, photo rectification and confidence gating. [Snapshot comparison](https://github.com/Hour49/Junction26/compare/3b840f5c6e69a2b18f8acc9c5428d3c7361a0267...e5c11b5292d493d15a962be978c63b1fc2250407)

Their latest committed golden answering run reports **2,709/2,948 correct (91.89%)**, holdout **518/560 (92.5%)**, raster **1,132/1,342 (84.35%)**, evidence coverage **92.20%**, 30 answers marked abstained, **55/60 paraphrases**, and **25/25 unsupported requests refused**. These are their selected evaluation population and definitions. Evidence coverage is not independently verified citation correctness. [Answering artifact](https://github.com/Hour49/Junction26/blob/e5c11b5292d493d15a962be978c63b1fc2250407/eval/results/runs/20261114-082045-answering-pipeline.json)

The extraction run finds **14/14 labelled conflicts**, no false alarms on **102 labelled agreements**, and **123 additional unlabelled conflicts**. Those extra conflicts prevent treating the labelled subset as a complete false-positive assessment. [Extraction artifact](https://github.com/Hour49/Junction26/blob/e5c11b5292d493d15a962be978c63b1fc2250407/eval/results/runs/20261114-082044-extraction-pipeline.json)

Their experiment report describes YOLO26 L at 1024 pixels for elements, category-specific Gemini substitution for shower/bathtub and sauna, a room reader with a predicted apartment mask, cached ingestion and a certified "Sure" gate. Kitchen still uses a prior when it outperforms readers. A separate raster test reports **5,708/6,718 (85.0%)**, with an image-bootstrap interval **83.4-86.5%**. Golden answering reports zero current model cost because extraction is precomputed; the experiment report separately records approximately **EUR 53.76 GPU rental and USD 23.1 hosted-model spend**. [Experiment details](https://github.com/Hour49/Junction26/blob/e5c11b5292d493d15a962be978c63b1fc2250407/docs/EXPERIMENTS.md)

**Implication for us:** raster capability is now a demonstrated public competitive focus. Test categories separately and preserve the distinction between count accuracy, abstention, evidence and full ingestion cost. Their negative experiments also caution against assuming tiles, higher resolution or generic detect-then-verify will improve exact counts. Windows remain a weak category in their report.

### Plumbline: lorikjashari/stoa

The old ProcureBench/AfterQuery exclusion no longer applies. Current code implements deterministic native/precomputed answers, a constrained language planner, PDF text and vision, with a FastAPI application and linked views. The planner proposes table/filter/aggregation JSON; code computes the result and evidence. [README](https://github.com/lorikjashari/stoa/blob/35586e76d3017111874e66807c9ac0fdb034cdf9/README.md), [pipeline](https://github.com/lorikjashari/stoa/blob/35586e76d3017111874e66807c9ac0fdb034cdf9/stoa_qa/pipeline.py), [planner](https://github.com/lorikjashari/stoa/blob/35586e76d3017111874e66807c9ac0fdb034cdf9/stoa_qa/planner.py)

Published figures are **37,392/37,584 Swiss (99.49%)**, **3,059/3,062 IFC (99.90%)**, and a raster hybrid **65.9% on 3,398 held-out questions**; Gemma alone is 63.4% on those 3,398 questions. Network alone is 50.2% on **2,842 questions**, with different category coverage because it lacks shower/floor counts. The displayed **76.7% overall is explicitly a projection**, not a directly scored full run. These multilingual question counts should not be treated as independent drawings. [Benchmark](https://github.com/lorikjashari/stoa/blob/35586e76d3017111874e66807c9ac0fdb034cdf9/web/benchmark.json)

The hybrid selects a reader per category using validation data. The current configuration has `yolo_run: null`, so YOLO support in the code is not proof that YOLO contributes to the shipped hybrid. Importantly, a selected count may come from a reader without geometry while displayed marks come from another reader and need not sum to that count. The explanation discloses this mismatch. Confidence is a fixed 0.9 when another reader agrees, otherwise 0.5; it is not per-answer calibrated probability. [Selection configuration](https://github.com/lorikjashari/stoa/blob/35586e76d3017111874e66807c9ac0fdb034cdf9/stoa_qa/cubicasa_picks.json), [raster answer and evidence](https://github.com/lorikjashari/stoa/blob/35586e76d3017111874e66807c9ac0fdb034cdf9/stoa_qa/cubicasa.py)

**Implication for us:** category-specific readers and a constrained planner are useful ideas. Preserve one-to-one provenance between a selected count and its counted objects. Agreement between readers alone should not become a source-verification badge.

### Hologram: Akshaz7/junction

This has grown from an IFC conversion spike into a much larger application: native solvers, vision ingestion, structured plan maps, FastAPI/PostgreSQL, React/three.js and SwiftUI/RealityKit/ARKit source. Shared element IDs connect 2D evidence, 3D highlights and intended phone AR. AR source presence does not establish a successful physical-device demo. [README](https://github.com/Akshaz7/junction/blob/ee7f71928b22d185acb4343a53a242284c9f4dc8/README.md), [snapshot comparison](https://github.com/Akshaz7/junction/compare/ae2bf7c11a7e82794ca64c5d3ba472054ffa212f...ee7f71928b22d185acb4343a53a242284c9f4dc8)

The latest 200-case sample reports **124/187 numeric questions correct (66.31%)**, or **124/171 answered (72.51%)**, with 13 text questions separate. Its first full English numeric run reports **35,900/63,307 (56.71%)**, **62.72% answered accuracy**, and 6,071 abstentions. That is the English set, not the entire multilingual dataset. Source performance varies sharply; lengths and volumes abstain in that run. [200-case artifact](https://github.com/Akshaz7/junction/blob/ee7f71928b22d185acb4343a53a242284c9f4dc8/results/bench/e09_text.json), [full English artifact](https://github.com/Akshaz7/junction/blob/ee7f71928b22d185acb4343a53a242284c9f4dc8/results/bench/full_1.json)

Category verification and a bathroom crop reportedly improve shower/bathtub exact accuracy from **12.3% to 33%**, at **USD 0.00062 per drawing**; windows remain **32%**. Their public web URL and committed six-check deployment report are evidence of deployment work, not a browser test we independently performed. WebSocket synchronization is unsupported on that Vercel deployment. [Vision artifact](https://github.com/Akshaz7/junction/blob/ee7f71928b22d185acb4343a53a242284c9f4dc8/results/vision/v09_final.json), [deployment check](https://github.com/Akshaz7/junction/blob/ee7f71928b22d185acb4343a53a242284c9f4dc8/results/e2e/deployed-check.md), [public app](https://hologram-khaki.vercel.app)

**Implication for us:** their visual breadth is a real demo consideration. Shared IDs and reliable evidence interaction are useful; reproducing their AR scope before validating our raster accuracy would add significant work.

### The other Trace: 13032585789-spec/Trace

Five commits follow our initial inspected HEAD. The pilot now has preflight requests, four workers, model failover for availability/rate-limit errors and an experimental overlapping 2x2 crop path. The newest commit fixes tile implementation issues and **disables tiles by default because they performed worse**. [Snapshot comparison](https://github.com/13032585789-spec/Trace/compare/930e7ca6e11c370d2e6d8a051ff9738c7f4ef983...f99d72547f254f4955ecfc29e72368b671977c0e)

Native adapters use Swiss DXF and IFC; routing depends on dataset source folders. Raster analysis gets twelve categories in one vision call and caches boxes. README claims **83.0% on 110 images / 1,014 questions**; the HEAD commit separately claims **83.3% on 183 images / 3,350 questions**. These are self-reported subsets without a new committed full score artifact. The older **31.75%** score file predates this raster work and must not be used to describe current performance. [README](https://github.com/13032585789-spec/Trace/blob/f99d72547f254f4955ecfc29e72368b671977c0e/README.md), [raster code](https://github.com/13032585789-spec/Trace/blob/f99d72547f254f4955ecfc29e72368b671977c0e/engine/cubicasa.py), [historical score](https://github.com/13032585789-spec/Trace/blob/f99d72547f254f4955ecfc29e72368b671977c0e/eval/results/score_all_all.txt)

Missing shower/tub detections can fall back to a prior count of one with empty evidence and a warning. Pilot outcomes influenced those fallbacks and crop choices, so that same pilot is not an untouched final test. No frontend or public demo URL appears in this engine tree; another developer/repository may own its UI. [Pilot selection](https://github.com/13032585789-spec/Trace/blob/f99d72547f254f4955ecfc29e72368b671977c0e/vlm_pilot.py), [answer routing](https://github.com/13032585789-spec/Trace/blob/f99d72547f254f4955ecfc29e72368b671977c0e/engine/answer.py)

**Implication for us:** keep the efficient cached inventory, but make fallback guesses distinct from measured quantities. Do not spend time adding tiling without a measured improvement.

## Unchanged implementations and newly discovered plans

- **Drawing Desk:** native IFC/DXF tools plus vision with drawing markers. Its IFC area fallback accepts a narrow closed straight-edge footprint rather than treating every geometry as net area. This remains a useful bounded geometry idea. [Pinned README](https://github.com/aapolipponen/drawing-desk/blob/072608f95db03ee3d49c3ece243169c65eb46921/README.md)
- **NiceK1:** a deterministic geometry/scorer spike with cached raster answers. Located evidence is weaker than the inventory/count idea. Our original comparison records the source and limitations. [Pinned README](https://github.com/NiceK1/stoa-spike/blob/37df416f54ac3bed62c49e560560836c3a3234c1/README.md)
- **Metsatalo:** the LLM selects deterministic IFC/DXF/PDF tools; terminal tool results return without another synthesis call, while raster-only inputs go directly to vision. README reports 30 sampled questions per source: Swiss/IFC 100%, CubiCasa 47%, Opening Design 26%; separately tuned full-preview figures are not held-out evidence. Internal evidence has locations, but its answer summary drops boxes/pages and its vision fallback gives no per-object regions. [Pipeline](https://github.com/chaowang0524/metsatalo-stoa/blob/8ea707cf463b1845e2348812993233f71440f27b/stoa/pipeline.py), [answer summary](https://github.com/chaowang0524/metsatalo-stoa/blob/8ea707cf463b1845e2348812993233f71440f27b/stoa/answer.py), [README](https://github.com/chaowang0524/metsatalo-stoa/blob/8ea707cf463b1845e2348812993233f71440f27b/README.md)
- **SpaceLens:** a broad browser-first 2D/3D product, with printed text/dimensions and rule-based quantity answers. Its 2,358-question Swiss PDF artifact has **1,118 correct, 1,124 answered**: **99.5% on answered**, **47.7% coverage**, **47.4% overall**. No comparable raster/IFC result was established. [Artifact](https://github.com/JUNCTION26/SpaceLens/blob/94a9f6ea1baf625917330f95c55fc8e2b8b74a1a/public/samples/stoa/eval-results.json), [answer implementation](https://github.com/JUNCTION26/SpaceLens/blob/94a9f6ea1baf625917330f95c55fc8e2b8b74a1a/src/features/drawings/answer.ts)
- **New: Georgia-coderok/okstoa-try1:** Claude tool agent, eight-step limit, citation-ID existence validation, five synthetic smoke cases. The actual database is hardcoded mock data; real drawing ingestion and a viewer were not found. Existence of an ID does not prove semantic correctness or exact localization. [Explicit mock and agent](https://github.com/Georgia-coderok/okstoa-try1/blob/e463299155a91ffaa930ef94b119ce7b9be118ce/brain_starter.py)
- **New: lalashutosh/blueprint:** PlanGraph proposes one-time reconstruction, CubiCasa segmentation, native IFC/DXF tools, exact query operations, editable scale, corrections and held-out evaluation. Current public files are design material, not an implemented engine. Its pretrained-model split policy is a useful evaluation consideration. [Design](https://github.com/lalashutosh/blueprint/blob/2335744410fb77c339a9897116d3772c2825c441/plangraph_system_design.md)
- **Leargas/BlueprintTrace:** a voice-first Gemini/ElevenLabs and cited-evidence plan; implementation and detailed plans are not in the public tree. [README](https://github.com/markmannion/leargas/blob/386cb5aa6e4394292596590a11d4e403dab638f7/README.md)
- **tstst334:** names the challenge, but the inspected public tree is a scaffold with empty requirements. [README](https://github.com/tstst334/junction/blob/e2a5cfbcd33eb1af337a33aa7cbca9c9196e063d/README.md)
- **ChatChTG:** drawing-conversation description and Stoa dataset-download setup, without a visible answering implementation at this HEAD. [README](https://github.com/d-malkov-iprally/ChatChTG/blob/4778784172c239705e1abd8e769647fd01a9646c/README.md), [Stoa download script](https://github.com/d-malkov-iprally/ChatChTG/blob/4778784172c239705e1abd8e769647fd01a9646c/scripts/download_data.sh)

## Watchlist and exclusions

**Yue-fy/Junction_Hannah_family** still records Stoa as a captain's initial preference, with undecided specification. Do not call it a confirmed Stoa build. [Event notes](https://github.com/Yue-fy/Junction_Hannah_family/blob/b52f06e04b31cc7ad257e0dfc20518bf82ee83fd/docs/EVENT.md)

**cufelix/hackjunction** remains an event research knowledgebase whose current README says it is leaning Hostinger. Stoa mentions in its challenge research do not establish Stoa participation. Its current HEAD is retained to catch a future pivot, as happened with Plumbline. [Current README](https://github.com/cufelix/hackjunction/blob/af4b430ff8da0bff5ae4010130e93fd136698e2f/README.md)

Other generic-query false positives included a cancer-care/FirstLine application, unrelated payments-directory forks, engineering-assurance software and an on-device trail-guide hackathon. No private repositories or personal contact information were used.

## What this means for our Trace

Our current code has native source/quantity guards, source-focused evidence, cached visual inventories, add/exclude/undo, append-only review revisions, saved working quantities, scope-aware comparisons, source-change checks and usage accounting. Those were the most useful slices from the [original comparison](initial-research.md). The upgraded native sample improved from **41/97 to 55/97 correct numeric answers**, with three incorrect cases remaining; its 70 drawing groups are disjoint from our original diagnostic. The sample is source-stratified and native-only. It cannot establish that we outperform these teams. [Our paired result](../../stoa-trace/ops/reports/competitive-upgrade/paired-comparison.md)

| Priority | Remaining gap or opportunity | Concrete next check |
| --- | --- | --- |
| 1 | New visual inventory has no measured live accuracy | Audit an unseen, category-balanced raster sample; score exact counts and one-to-one object evidence separately. Respect the existing model budget. |
| 2 | Semantic evidence truth is not measured by valid coordinates | Use our human-annotation audit tool; verify actual counted objects, page/scope and label support. |
| 3 | Structured accuracy does not cover arbitrary geometry | Test missing explicit IFC quantities and unsupported shapes; preserve abstention instead of calling footprint area net area. |
| 4 | Evaluation populations differ greatly | Keep correct/all, correct/answered, coverage, source, language, drawings and trained/tuned/test partitions explicit. Never rank teams by incompatible headline percentages. |
| 5 | Ingestion can dominate inference cost | Report first ingestion and follow-up requests separately; unknown configured prices stay unknown. |
| 6 | Competitors have broader 3D/AR presentations | Make our question-to-source-to-correction flow convincing on a real unseen drawing before expanding the demo scope. |

Useful next experiments are category-specific readers, targeted bathroom crops and a constrained planner over typed source data. These are hypotheses for our data, not automatically proven improvements. Reusing an idea does not require copying another team's implementation, weights or dataset artifacts. Arbitrary 3D/AR scope, broad GPU training and tiling without measured benefit remain costly choices with limited time.

## Search coverage and limits

Refreshed GitHub names/descriptions/README searches for Stoa/Junction, exact challenge title, recent creation dates, IFC, blueprint, drawing, quantity, takeoff and dataset wording. Reviewed forks and public repository lists for 14 known owners; commit/issue search and general web indexing were also used. Broad Stoa/Junction returned **22 raw repositories, 29 including forks**; the seven extra forks were unrelated directory copies. Exact challenge-title README search returned **seven**. Recent IFC/Junction wording found PlanGraph; Stoa/drawing wording found the mock agent. The [snapshot queries](stoa-competitor-snapshot.json) are repeatable seeds, not an exhaustive claim.

GitHub API rate limits resumed during this refresh. Public `git ls-remote` and GitHub Atom feeds verified HEADs and commit dates where API metadata was unavailable. Search indexing lags, non-default branches may contain additional work, related repositories may belong to the same team, and private work is invisible. No competitor source was executed, no paid inference was used for this research, and no competitor result or deployment was independently rerun.

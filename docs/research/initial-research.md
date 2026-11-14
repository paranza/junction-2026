# Initial research archive

Historical notes from the first research pass and comparison, around 14 November 2026, 01:33 Europe/Helsinki (13 November, 23:33 UTC). These are our own research notes, not copied competitor source code. **This archive is not the current assessment.** Several capabilities, exclusions and scores below were superseded overnight. Read [the refreshed report](stoa-competitors.md) and [current HEAD snapshot](stoa-competitor-snapshot.json).

The implementation recommendations here were subsequently addressed in our upgrade, with limits recorded in the current report. Original accuracy figures describe the earlier Trace version.


---

## Original GitHub discovery

# GitHub discovery and three-repository deep review

Public-only snapshot researched 14 Nov 2026, Helsinki time. No competitor code executed. Read source from GitHub HTML and raw content, public metadata/search, and git ls-remote. All performance claims below are repository authors' self-reports; not reproduced independently. A public repo is not proof of a distinct registered competing team or final submission.

## chaowang0524/metsatalo-stoa :  confirmed Stoa/Junction 2026

URL: https://github.com/chaowang0524/metsatalo-stoa
Main SHA: 8ea707cf463b1845e2348812993233f71440f27b
GitHub search metadata updated 2026-11-13T21:07:05.066Z (23:07 Helsinki). This field is repository metadata update, not guaranteed latest code commit.

What: Python CLI quantity-answer backend with structured source evidence and an evaluator. Supports IFC, DXF, text PDFs and rendered raster vision fallback. No browser UI visible in inspected current tree.

How: File inspector identifies source type and finds IFC/DXF siblings from filenames; an LLM routes the question to available deterministic tools. IFC uses ifcopenshell, quantity sets or tessellated geometry, unit conversion, storey/class filters. DXF uses ezdxf + Shapely, known semantic layers and fixture/symbol rules. Terminal deterministic tool results return immediately without a second synthesis call. Raster-only questions skip the router and go directly to vision. Verda OpenAI-compatible endpoint, default DeepSeek model named in code, logs calls/tokens/latency; prices default zero unless supplied, so cannot claim zero paid model cost.

Evidence:
- Architecture: https://github.com/chaowang0524/metsatalo-stoa/blob/8ea707cf463b1845e2348812993233f71440f27b/stoa/pipeline.py#L1-L11
- Tool registry: same file L61-L172; max 4 turns L24, router L239, immediate terminal return L284-L288.
- Sibling-source mapping: https://github.com/chaowang0524/metsatalo-stoa/blob/8ea707cf463b1845e2348812993233f71440f27b/stoa/inspect_file.py#L35-L73
- Default model + cost config: https://github.com/chaowang0524/metsatalo-stoa/blob/8ea707cf463b1845e2348812993233f71440f27b/stoa/verda.py#L16-L22
- DXF layer + known-symbol dependency: https://github.com/chaowang0524/metsatalo-stoa/blob/8ea707cf463b1845e2348812993233f71440f27b/stoa/tools/dxf_tools.py#L1-L6 and L162-L180.

Authors' numeric claims (README L28-L38): 30 random questions per source, seed 0: swiss_dwellings100%, ifc_models100%, cubicasa5k47%, opening_design26%, text IFC-Bench unscored. Calls per question1.0,1.1,1.0,3.4 respectively. Authors say tuning directly against all English questions gives513/513 IFC-backed and1168/1179Swiss; tuned preview scores are not held-out results.
https://github.com/chaowang0524/metsatalo-stoa/blob/8ea707cf463b1845e2348812993233f71440f27b/README.md#L28-L38

Observable gaps:
- README explicitly says Cubicasa53% of questions raster-only and detector fine-tuning is next step, opening_design table columns misread, missing IFC backing on one source, area heuristics, vision token cost underreported. https://github.com/chaowang0524/metsatalo-stoa/blob/8ea707cf463b1845e2348812993233f71440f27b/README.md#L40-L46
- Evidence objects carry bounding boxes/page internally, but Answer.summary serializes only ref,label,value, dropping boxes/pages before pipeline/CLI JSON output: https://github.com/chaowang0524/metsatalo-stoa/blob/8ea707cf463b1845e2348812993233f71440f27b/stoa/answer.py#L10-L20 and #L35-L47. Strong opportunity to show usable visual evidence rather than internal IDs.
- Vision fallback downsizes drawing longest side to1600px and returns just page + explanatory text, no per-object locations: https://github.com/chaowang0524/metsatalo-stoa/blob/8ea707cf463b1845e2348812993233f71440f27b/stoa/tools/vision_tools.py#L11-L16 and #L54-L63.
- More technical uncertainty: IFC quantity code silently skips missing quantity values in sums and substitutes gross/net alternatives; geometry length is axis-aligned bbox. Source supports deterministic arithmetic but not proof every semantic quantity is correct. Useful for fair comparison, not a claim their demo necessarily fails.

Assessment: credible numeric pipeline, cheap routing design, unusually concrete scores; weak visible visual-verification experience and weak raster/schedule accuracy. Do not compare their30-per-source stats with another repo's full-preview or held-out figures without a common denominator.

## markmannion/leargas / BlueprintTrace :  confirmed Stoa track, public plan only

URL https://github.com/markmannion/leargas
Main SHA386cb5aa6e4394292596590a11d4e403dab638f7
GitHub search metadata updated2026-11-13T22:01:12.431Z (14Nov00:01 Helsinki).

What: voice-first construction-drawing Q&A, cited answers with highlighted source regions and refusal when evidence absent.

How planned: ingest→retrieve→Gemini answer/citations/highlights; ElevenLabs voice. Separate model-training workstream split raster PDFs/images/SVG versus structured DWG/DXF/IFC, using quantity-question dataset. README says detailed architecture/build/eval/demo docs are local and gitignored. Current public main tree only .gitignore,LICENSE,README; no visible implementation or scores. Explicitly label as intentions, not working capabilities.

Source https://github.com/markmannion/leargas/blob/386cb5aa6e4394292596590a11d4e403dab638f7/README.md#L3-L14 and #L28-L36.

Assessment: clear product/demo emphasis and training ambition; public evidence insufficient to judge execution. A voice feature alone will not distinguish another team from this stated direction.

## tstst334/junction :  confirmed challenge, scaffold only

URLhttps://github.com/tstst334/junction
Main SHAe2a5cfbcd33eb1af337a33aa7cbca9c9196e063d
GitHub metadata updated2026-11-13T21:01:41.863Z (23:01 Helsinki).
README only project name and Stoa Make Blueprints Talk Challenge. Current public tree .gitignore,LICENSE,README.md,requirements.txt; requirements file empty. No method or actual functionality can responsibly be inferred.

https://github.com/tstst334/junction/blob/e2a5cfbcd33eb1af337a33aa7cbca9c9196e063d/README.md

## Additional watchlist candidate from commit search

Yue-fy/Junction_Hannah_family: https://github.com/Yue-fy/Junction_Hannah_family
Main SHA b52f06e04b31cc7ad257e0dfc20518bf82ee83fd, commit2026-11-13T20:34:33Z (22:34Helsinki).
README says project description to come once challenge chosen. docs/SPEC entirely TBD. docs/EVENT says Stoa captain's first choice, not final; records dataset facts and possible geometry/CV/small model approaches, and access to96GB GPU workstation. Do not list as confirmed Stoa implementation. https://github.com/Yue-fy/Junction_Hannah_family/blob/b52f06e04b31cc7ad257e0dfc20518bf82ee83fd/docs/EVENT.md#L102

Excluded newly screened candidate HienNguyen-ComputerScience/junction-2026-app: issue search matchedStoa in historic message board, but current README explicitly FirstLine/AstraZeneca cancer-care county dashboard.

## Search methods and outcomes

Native GitHub search HTML contains structured JSON usable without code-search authentication. REST API initially rate limited403 on this machine, but native search succeeded, occasionally429 on bursts then succeeding later.

Successful queries:
- stoa junction repositories:5 results, original five confirmed descriptions.
- stoa in:readme junction:19 results, both pages inspected. Relevant10: Hour49/Junction26, chaowang0524/metsatalo-stoa,tstst334/junction,markmannion/leargas,NiceK1/stoa-spike,aapolipponen/drawing-desk,Akshaz7/junction,13032585789-spec/Trace,cufelix/hackjunction,JUNCTION26/SpaceLens. Other9 noise.
- "Make Blueprints Talk" repository names/descriptions:2; in:readme4 (tstst,Trace,SpaceLens,cufelix).
- stoa created:>=2026-11-13:9 raw, includes lorikjashari/stoa and original six;2 unrelated bot/editor projects. (Name/description search misses repos mentioning sponsor only in code.)
- "junction2026" construction/blueprint/drawings:zero each; naming variants matter.
- "junction 2026" "construction" in:readme:9 raw, no extra verified competitors.
- "Stoa" "drawing" in:readme created:>=2026-11-01:11 raw, both pages inspected, no additional relevant.
- "junction" "IFC" in:readme created:>=2026-11-01:27 raw, first page only, noisy non-hackathon IFC tooling. No extra relevant on first page.
- "junction" "blueprint" in:readme created:>=2026-11-01:180 raw, first page only, noisy traffic/game matches. No extra confirmed.
- "junction-dataset" in:readme:81 raw, first page only, noisy splice-junction biology/traffic matches.
- stoa in:readme junction fork:true:26 raw, all3pages inspected. Extra7 all unrelated awesome_mpp payment-directory forks; no extra Stoa team forks.
- stoa junction commits: relevant NiceK1 code commit and Yue-fy candidate notes; unrelated game/urban science noise otherwise.
- "Make Blueprints Talk" commits:1 unrelated UnrealEngine tutorial commit2025.
- stoa junction issues:5raw, relevant Hour49 #4,#15,#24,#34; Hien message board excluded based current AstraZeneca focus.
- junction2026 topics:zero topic results.
- Web engines exact Stoa+Junction+GitHub returned no relevant current repos; partner announcement confirmed2026 construction drawing Q&A challenge.

All source/main trees, explicit README plans, code modules and scoring code inspected read-only. Did not use private/auth-only code search, inaccessible teams, private model/dataset artifacts, secrets, contacts, or tests. Cannot guarantee completeness: repos may omit identifying terms, branch implementation may differ, some teams private, GitHub indexing may lag, and repository does not equal independent competing team.


---

## Original alternate discovery

# Alternate discovery findings :  public GitHub, Junction 2026 Stoa

All findings read-only. Repo code was inspected as text, never executed. Scores below are team-published, not independently reproduced. Snapshot early 14 Nov 2026 Helsinki.

## Confirmed / strongly tied

### Hour49/Junction26 :  working name Countersign
- https://github.com/Hour49/Junction26
- Explicit Stoa README, substantial Python/FastAPI backend and eval code. Ingest drawing once, choose richest source, create structured drawing model, precompute quantity takeoff, answer via multilingual template parser; independent second count intended to reveal disagreements; evidence as numbered drawing marks/boxes. Engineer and surveyor roles/signoff in requirements.
- Actual implementation at snapshot is vector-PDF focused. BIM/CAD/raster adapters mostly hello stubs. Building-code checks explicitly cut. docs/PIPELINE.md accurately separates built/planned.
- Latest saved pipeline eval: 2109/2948=71.54%; holdout 410/560=73.21%; $0 model inference; evidence coverage46.88%; 1498/2948 marked abstain but still supplied prior guesses. High-confidence/non-abstained1450 questions99.03%. Golden set includes translated templates, so these are question counts, not independent drawings.
- 95.99% parser-v1 result reads GOLD extraction; not an end-to-end figure. README Swiss counts99.91%, areas99.97%, IFC plan areas96.99% are full-dataset prototypes explicitly tuned before heldout split existed, dependent on drawing style.
- Raster extraction F1=0; none of14 real conflicts found. Strong infrastructure and honest tracking, raster and conflict-handling gap.
- Demo folder is explicitly a synthetic clickable mock; no integrated live user flow proven.
- Sources: https://github.com/Hour49/Junction26/blob/main/docs/PIPELINE.md ; https://github.com/Hour49/Junction26/blob/main/eval/results/runs/20261114-004132-answering-pipeline.json ; https://github.com/Hour49/Junction26/blob/main/eval/results/runs/20261114-004132-extraction-pipeline.json ; https://github.com/Hour49/Junction26/blob/main/prototypes/pdf-extract/README.md ; https://github.com/Hour49/Junction26/blob/main/demo/README.md

### 13032585789-spec/Trace :  junction-stoa-engine
- https://github.com/13032585789-spec/Trace
- Explicit Make Blueprints Talk engine, no frontend in snapshot. Pure Python standard-library ASCII DXF/IFC STEP parsers; NumPy/OpenCV for image-box calibration.
- Swiss: classify layer polygons and fixture geometry, room labels and apartment outlines; IFC: object classes/storeys/quantities/extruded footprint or B-rep bottom-face areas. Answer object includes IFC GlobalIds and image/PDF boxes for highlighting.
- Raster path does one vision-model call per image for all12categories, caches detections; supports Gemini2.5Pro/NVIDIA. Without credential, most-common answer priors with low-confidence warning.
- README claims Swiss98.6% (test99.0%), IFC98.0%; CubiCasa54.9% is prior-only baseline, not image understanding. Eval code stable80/20 split by DRAWING path; good independent-drawing split structurally, but selfreported results not independently rerun.
- Older committed score_all_all.txt shows31.75%overall, raster unsupported. Do not conflate old score with current README claims.
- Known gaps: storey total area77%, wall side area88%, wall volume91%; opening_design not started, IFC-Bench text not automatically scored.
- Sources: https://github.com/13032585789-spec/Trace/blob/main/README.md ; https://github.com/13032585789-spec/Trace/blob/main/engine/cubicasa.py ; https://github.com/13032585789-spec/Trace/blob/main/eval/run.py ; https://github.com/13032585789-spec/Trace/blob/main/eval/results/score_all_all.txt

### JUNCTION26/SpaceLens
- https://github.com/JUNCTION26/SpaceLens
- Explicit Stoa project with live public link https://junction26.github.io/SpaceLens/ (link found, not browser-tested by this agent).
- Broad visual product: phone-camera/A4 calibration, PDF/image blueprint reading, dimensioned2D editor, 3D walkthrough, layout solver and independent checker, door-fit/route simulations, evidence and uncertainty, exports.
- Vite/React/TypeScript, three.js/r3f, pdf.js text index, Zustand; browser-only, local-first; optional Gemini. Source code evidence Q&A primarily reads printed text/dimensions/room labels then rule-based multilingual templates. Door/window route counts unique text tags if available, so not full symbol detection.
- Committed benchmark first2358 Swiss PDF questions across65files:1118correct,1124answered,1234abstained;99.5% accuracy ON ANSWERED;47.7%coverage;47.4%overall;0 model calls;0.4ms/Q. Not99.5%overall, no raster/IFC benchmark proven.
- Strength polished/broad product narrative; weakness core quantity coverage and risky breadth. Route checks geometric, not legal/accessibility certification.
- Sources: https://github.com/JUNCTION26/SpaceLens/blob/main/public/samples/stoa/eval-results.json ; https://github.com/JUNCTION26/SpaceLens/blob/main/src/features/drawings/answer.ts ; https://github.com/JUNCTION26/SpaceLens/blob/main/src/features/drawings/textCore.ts

### Akshaz7/junction
- https://github.com/Akshaz7/junction
- Explicit Junction2026 construction dataset spike; IFC to GLB plus searchable per-element JSON index, joining on IFC GlobalId. Not a full competitor submission confirmed. NoUI orQ&A layer.
- IfcOpenShell/IfcConvert geometry; normalizedcategory/type/storey/world-space boundingbox, property metadata kept in separate JSON. Specialhandling IFC2X3MEP types and aggregate boxes. Has validation script for model/node/GUID/bbox fidelity.
- README conversion claims: 0.18s smallstairs to~10s clinic-plumbing; index0.2-99s;705/705and6587/6587GLB-node GUID matches. Actual sampleGLBs+JSON and extraction/validation scripts exist. Claimed geometry accuracy not rerun.
- Sources: https://github.com/Akshaz7/junction/blob/main/README.md ; https://github.com/Akshaz7/junction/blob/main/scripts/extract_elements.py

### d-malkov-iprally/ChatChTG
- https://github.com/d-malkov-iprally/ChatChTG
- Description: Junction demo of drawing conversational platform. README same phrase; only download_data.sh besides gitignore.
- Script downloads preview/full from stoa-junction-2026 public dataset. Strong Stoa relationship despite no explicit challenge-name in README.
- At snapshot setup only; no visible parser,model,Q&A implementation or benchmark. Do not infer intended architecture.
- Source: https://github.com/d-malkov-iprally/ChatChTG/blob/main/scripts/download_data.sh

## False positives excluded
- https://github.com/lorikjashari/stoa : repo name stoa, README is ProcureBench, explicitly AfterQuery Break the Agent kitchen-procurement RL environment, README only. Not Stoa competitor.
- https://github.com/cufelix/hackjunction : event/team knowledgebase, all challenges research, leaning Hostinger. No Stoa build.
- https://github.com/tstst334/junction : explicit Stoa, minimal skeleton; other research agent owns details.

## Coverage
REST repository searches: junction2026 (27 results initial); junction-2026 (91); junction2026 string in README (115 inclpage2); hackjunction created>=Nov10 (8); construction+junction(15);drawing+junction(13);blueprint+junction(7). Current-event broad README scan ~100 repos yielded no additional Stoa builds beyond explicit discoveries above and other agent-owned aapolipponen/drawing-desk, NiceK1/stoa-spike, chaowang0524/metsatalo-stoa.

## Strategic implications (inference)
1. Several competitors already use cheap deterministic geometry with selective vision fallback. A generic RAG/chat wrapper is unlikely to distinguish.
2. Raster drawings dominate reported dataset (~67%questions); current competitors have weak/absent real raster results. A reliable detector with visible item-level evidence may be valuable.
3. Show end-to-end on unseen drawings, free paraphrases and real PDFs, include correct/total+coverage. Competitor headline figures often exclude abstentions or use gold extraction.
4. Trust can be shown through drawn numbered marks, uncertainty, duplicate counting rules, and real disagreements resolved; Hour49's conflict feature currently misses all14 real cases despite planned UX.
5. SpaceLens wins on scope and visualstory; a narrower working quantity/evidence flow may be easier to prove live.


---

## Original comparison and improvement plan

# Stoa competitive improvements

Checked **14 November 2026, 01:33 Helsinki / 13 November, 23:33 UTC**. Public sources only; competitor code was inspected as text and never executed. Our README and HANDOFF were read at `stoa-trace/`. The detailed implementation review subsequently informed the upgrade.

## Competitor changes

**No changes since approximately 23:28 UTC:** all seven current HEAD commits predate that time.

| Repository | HEAD | Last commit UTC |
|---|---|---|
| aapolipponen/drawing-desk | `072608f95db03ee3d49c3ece243169c65eb46921` | 21:35:33 |
| NiceK1/stoa-spike | `37df416f54ac3bed62c49e560560836c3a3234c1` | 21:32:39 |
| Hour49/Junction26 | `3b840f5c6e69a2b18f8acc9c5428d3c7361a0267` | 23:00:53 |
| chaowang0524/metsatalo-stoa | `8ea707cf463b1845e2348812993233f71440f27b` | 20:59:15 |
| 13032585789-spec/Trace | `930e7ca6e11c370d2e6d8a051ff9738c7f4ef983` | 22:17:04 |
| JUNCTION26/SpaceLens | `94a9f6ea1baf625917330f95c55fc8e2b8b74a1a` | 21:34:33 |
| Akshaz7/junction | `ae2bf7c11a7e82794ca64c5d3ba472054ffa212f` | 22:47:13 |

## What we already have

Our implemented Trace already has native PDF/DXF/IFC/semantic SVG extraction, conservative unresolved-filter fallback, page/region scope, evidence overlays, candidate deduplication, count exclusion and recomputation, saved original/review history, JSON export, lazy caches, and hosted vision fallback. The real deployment and 913 registered preview files are ahead of several public skeletons and synthetic mocks. These are existing strengths, not new proposals.

The known result is **22/50 answered** on a deliberately nonrepresentative diagnostic: **21/21 answered numeric questions correct**, but **21/44 numeric questions correct overall**. The three-call vision check included a wrong window count. These figures do not demonstrate an accuracy advantage over competitors.

Potential gaps, subject to code review: persistent visual inventories shared across questions, adding missed objects rather than only excluding extras, IFC geometry fallback where net quantities are absent, semantic evidence validation, and explicit conflict review.

## Recommended slices

### 1. Cache a visual object inventory once per drawing

**Value:** high. **Effort:** approximately 3-5 engineer hours for a narrow count workflow.

Competitor evidence: [Trace's raster implementation](https://github.com/13032585789-spec/Trace/blob/930e7ca6e11c370d2e6d8a051ff9738c7f4ef983/engine/cubicasa.py) makes one vision call per image, returns boxes for 12 categories, and caches those detections. NiceK1 also caches raster answers per drawing, but returns counts without locations. We can combine the efficiency with our existing reviewable overlays.

Proposed implementation:

- `server/llm.py`: add an explicit inventory operation returning located candidates for supported categories. Each candidate has a stable ID, category, normalized box/polygon, extraction method, and review status. Counts derive from candidate sets.
- `server/store.py`: reuse existing runtime storage. Cache by file hash, page, rendering/crop version, model, and schema version. Keep native objects and visual candidates distinguishable.
- `server/native_qa.py`: resolve recognized quantity questions against a prepared inventory after native methods. Other questions retain the current fallback.
- Reuse current overlays and correction UI. A request to inspect a region should create a new, traceable refinement rather than silently replacing reviewed page results.

Verify three different counts on one page: extraction occurs once, follow-ups reuse it, edits persist, and first-ingest cost is reported separately from answer cost. A single vision pass still does not prove completeness.

### 2. Add missed-object marking

**Value:** high for recall and the demo. **Effort:** approximately 1.5-3 hours.

Exclusion can repair an overcount; it cannot repair an undercount. This matters because raster doors/windows remain weak across public projects, and our small vision test included a wrong window count.

Proposed implementation:

- Add a review mode for drawing a box or point with a category and optional note, using existing coordinate transforms.
- Save it as a user-added candidate and patch event alongside exclude/restore events. Never overwrite the original extraction or original answer.
- Validate page and coordinates in `server/app.py`; persist through `server/store.py`; recompute from the effective candidate set.
- Show original and reviewed counts and export the correction provenance. Do not imply authenticated attribution if the app has no user identity.

Verify add, exclude, save, reload, recompute and export, including a rotated/cropped page. The original answer must remain recoverable.

### 3. Expand native IFC answers where the diagnostic shows misses

**Value:** medium to high. **Effort:** approximately 2-4 hours for carefully bounded cases.

Competitor evidence: [Drawing Desk](https://github.com/aapolipponen/drawing-desk/blob/072608f95db03ee3d49c3ece243169c65eb46921/README.md) supports a single closed, straight-edge `FootPrint` when an explicit space area is absent, and labels the source as geometry. [Trace](https://github.com/13032585789-spec/Trace/blob/930e7ca6e11c370d2e6d8a051ff9738c7f4ef983/README.md) reads extrusion/profile and B-rep bottom-face areas.

Two possible slices; select using actual failures:

- Add room-footprint area fallback in `server/extraction.py`, retaining explicit supported quantities as first choice. Use existing IfcOpenShell/Shapely, preserve holes and units, attach the GUID and geometric source. `server/native_qa.py` must distinguish footprint area from an explicit net area and reject unsupported shapes or ambiguous scope.
- Broaden explicit wall/slab length, area and volume aggregation, retaining a quantity and unit per GUID. Refuse partial sums when requested elements lack supported quantities.

Reuse registered SVG floor evidence where possible. A missing 2D registration should produce inspectable source records, not fabricated boxes. Do not label a gross footprint as net floor area.

### 4. Build one real conflict workflow

**Value:** high for reasoning and creativity. **Effort:** approximately 3-5 hours.

Competitor evidence: [Hour49's pipeline](https://github.com/Hour49/Junction26/blob/3b840f5c6e69a2b18f8acc9c5428d3c7361a0267/docs/PIPELINE.md) centres on independent counts and surveyor review, but its published snapshot finds **0/14 real conflicts**. A single working real conflict could be more persuasive than broad planned functionality.

Proposed implementation:

- Compare only matching category, storey, scope and units. Whole-model windows and windows visible in a floor view answer different questions; their difference is not automatically a contradiction.
- Start with one pair: printed room area versus polygon area, or registered native count versus visual count on the same floor.
- Return both values, methods, evidence, scopes and difference. Show disputed marks, let the reviewer choose a working value with a reason, and preserve both sources.
- Two prompts to the same model are not independent ground truth. A count difference involving above-cut or hidden IFC objects must explain that visibility issue.

Verify one agreement, one real disagreement, and one intentional scope mismatch that must not trigger a false conflict.

### 5. Strengthen evaluation and semantic evidence checks

**Value:** highest for choosing useful work. **Effort:** approximately 2-3 hours for an offline suite; paid inference remains subject to the owner's cap and authorization.

Competitor evidence: Hour49 groups evaluation by drawing/building and records code/config, cost, latency and evidence precision/recall. Its [71.54% pipeline result](https://github.com/Hour49/Junction26/blob/3b840f5c6e69a2b18f8acc9c5428d3c7361a0267/eval/results/runs/20261114-004132-answering-pipeline.json) includes prior guesses; its much higher parser score reads gold extraction. SpaceLens's [99.5% accuracy on answered questions becomes 47.4% overall](https://github.com/JUNCTION26/SpaceLens/blob/94a9f6ea1baf625917330f95c55fc8e2b8b74a1a/public/samples/stoa/eval-results.json).

Proposed implementation:

- Preserve the frozen 50-case diagnostic. Add a separate source/type/language-stratified manifest in `ops/benchmark.py`, grouped by building/drawing; sibling exports and translations stay together. Holdout should be scored only at selected milestones.
- Report all-question accuracy, coverage, answered accuracy, source/type breakdown, ingestion cost, answer cost, model calls and latency, plus source/config hashes.
- Add a small human-audited evidence set that checks whether markers identify the correct counted objects and whether cited labels and scope support the claim. Coordinate validity only proves that a box is on the page.
- Add free paraphrases and unsupported filtered questions to assess routing and appropriate abstention.
- Keep expected answers entirely within evaluation files, never extraction, prompts, retrieval indexes or training.

## Practical order

Spend the first hour classifying actual diagnostic misses. With only 4-6 hours left, prioritize missed-object marking, one proven native IFC gap, and an honest benchmark/demo. With a longer window, cache the visual inventory first and build one conflict demonstration after measuring it.

For four people, these slices can be owned separately: review corrections; native quantity coverage; visual inventory/cache; evaluation and demo. Adjust ownership after source explorers confirm what already exists.

Defer full 3D walkthrough/furniture/layout work, broad building-code reasoning, new orchestration frameworks, and a fresh GPU training pipeline. They carry scope and validation cost without directly repairing our known quantity/evidence gaps.

## Positioning

Our strongest story is a real question on an unseen drawing, object-level proof, transparent method/cost, and a correction that persists. Published competitor accuracy figures frequently use tuned templates, partial coverage, prior guesses or gold extraction. We should demonstrate the whole flow and report comparable denominators, without implying those competitor limitations make our own unmeasured accuracy stronger.

# Stoa differentiation: what is taken, what is open

Written **14 November 2026, about 10:30 Europe/Helsinki**, from public GitHub repositories and one live deployment. It builds on the [current competitor assessment](stoa-competitors.md), which has per-repository detail, pinned HEADs and source links. This page answers one question: **where can Trace still be different?**

The usual caveats apply. Competitor numbers are self-reported on different question populations and were not rerun by us. Do not rank teams by headline percentages.

## TL;DR

1. **Commodity, don't pitch it:** Swiss DXF and IFC answers near 99%, a vision fallback, evidence boxes, a self-scoring benchmark, 3D views.
2. **Hour49 ("Countersign") is the team to beat.** It covers almost everything: 91.9% on its golden set, CubiCasa raster 84-85%, takeoff table, review and sign-off, raster scale, conflicts, phone photos.
3. **Two gaps are still open in public code:**
   - **ifc_bench text questions:** 0 teams score them.
   - **opening_design real drawing sets:** the best public result is 51% on counts and 44% on text.
4. **Recommendation:** first close our Swiss/IFC coverage gap, then own **real BIM questions (ifc_bench)** and **real US drawing sets (opening_design)**. Skip 3D, AR, voice and the CubiCasa detector race.

## Repositories reviewed

There are 8 public repositories with a working implementation. Another 5 are plans, mocks or empty scaffolds (see the [assessment](stoa-competitors.md)).

| Repo | Product name | One-line position |
| --- | --- | --- |
| [Hour49/Junction26](https://github.com/Hour49/Junction26) | Countersign | Broadest and most measured. YOLO raster detector, sign-off, conflicts, about 100 commits |
| [lorikjashari/stoa](https://github.com/lorikjashari/stoa) | Plumbline | Native solvers, hybrid raster reader, constrained query planner, linked 2D/3D |
| [Akshaz7/junction](https://github.com/Akshaz7/junction) | Hologram | Plan maps, 2D/3D/iPhone AR, voice. Live at <https://hologram-khaki.vercel.app> (health check OK at 10:20) |
| [13032585789-spec/Trace](https://github.com/13032585789-spec/Trace) | Trace (**same name as ours**) | Engine only: Swiss/IFC parsers and Gemini raster boxes |
| [aapolipponen/drawing-desk](https://github.com/aapolipponen/drawing-desk) | Drawing Desk | Claude tool loop, plan→schedule across sheets, abstains when unsure |
| [chaowang0524/metsatalo-stoa](https://github.com/chaowang0524/metsatalo-stoa) | – | LLM routes to IFC/DXF/PDF tools, vision fallback |
| [NiceK1/stoa-spike](https://github.com/NiceK1/stoa-spike) | – | Geometry solvers + scorer + SVG evidence overlay |
| [JUNCTION26/SpaceLens](https://github.com/JUNCTION26/SpaceLens) | SpaceLens | Room capture, layout solver, 3D walkthrough. Drawing Q&A is a side feature |

## Feature count

How many of the 8 implementations have each feature in public code or README. Trace column = us.

| Feature | Teams | Who | Trace |
| --- | --- | --- | --- |
| Vision-model fallback for raster | **8/8** | all | yes |
| Self-scoring against `questions.jsonl` | **8/8** | all | yes |
| Exact DXF/IFC parsing | **7/8** | all but SpaceLens | yes |
| Evidence boxes on the drawing | **7/8** | all but Metsatalo (drops boxes in summary) | yes |
| Cost / tokens per answer | 5/8 | Hour49, Plumbline, Hologram, Drawing Desk, Metsatalo | yes |
| Multilingual questions | 5/8 | Hour49, Plumbline, Trace(other), NiceK1, SpaceLens | partial |
| Abstains instead of guessing | 4/8 | Hour49, Plumbline, Hologram, Drawing Desk | yes |
| Schedule / PDF text reading | 4/8 | Hour49, Plumbline, Drawing Desk, Metsatalo | yes |
| 3D view | 3/8 | Plumbline, Hologram, SpaceLens | no |
| Numbered count markers | 3/8 | Drawing Desk, Plumbline, Hologram | yes |
| Trained raster detector | 2/8 | Hour49 (YOLO26), Plumbline (network) | in progress (glyph) |
| Confidence badge | 2/8 | Hour49 ("Sure" gate), Plumbline (agreement, fixed 0.9/0.5) | no |
| Phone photo of a printed plan | 2/8 | Hour49, SpaceLens | no |
| Takeoff table + review/sign-off | 1/8 | Hour49 | review trail, no sign-off |
| Raster scale + room areas | 1/8 | Hour49 | no |
| Source conflict detection | 1/8 | Hour49 | no |
| Cross-sheet plan→schedule | 1/8 | Drawing Desk | partial |
| AR | 1/8 | Hologram | no |
| Voice | 1/8 | Hologram (Leargas plans it) | no |
| **ifc_bench text answers scored** | **0/8** | – | no |
| **opening_design counts above 52%** | **0/8** | – | unknown |

## Published accuracy, by source

These are self-reported numbers on different question sets. Use them for orientation only.

| Source | Best public | Others |
| --- | --- | --- |
| swiss_dwellings | ~99-100% (Hour49 golden 100%, Plumbline 99.5% on 37,584) | Trace(other) 98.6%, Metsatalo 100% on 30 |
| ifc_models | ~99-100% (Hour49 golden 100%, Plumbline 99.9% on 3,062) | Trace(other) 98% |
| cubicasa5k (raster) | Hour49 85.0% test (CI 83.4-86.5) | Trace(other) ~83% pilot, Plumbline 65.9%, Metsatalo 47% |
| opening_design | Hour49: counts 20/39 (51%), area 8/9, text 7/16 (44%) | Metsatalo 26%, Plumbline schedules 51%, others none |
| ifc_bench (text) | **none scored** | everyone marks it "unscored" or skips it |

Hour49 spent about **EUR 54 of GPU and USD 23 of hosted models** to reach 85% on CubiCasa. We cannot catch that cheaply before Sunday 10:00.

## Where we stand

- **Strength:** we only answer when native extraction is certain, and we keep an auditable review trail (add/exclude/undo, revisions, saved working quantities).
- **Weakness:** coverage. Our paired native sample is 55/97 correct, and our earlier 50-case run answered 44% of questions, with 100% correct among those. Competitors answer nearly everything on Swiss/IFC.
- **Name clash:** another team's repo is also called "Trace". Consider renaming before submission.

## Open gaps

### 1. ifc_bench text questions

- Preview: **249 questions** on IFC models (about 820 in the full set). Example: *"What is the building's type and its function?"* → "Office Building, Buerogebaeude, 5 floors".
- No public team scores them. They are real BIM questions an engineer asks, not dataset counting.
- We already parse IFC with IfcOpenShell. Each answer can cite the IfcBuilding / IfcBuildingStorey / property set GUIDs.
- Scoring is free-form. State the rule up front: an LLM judge with a published rubric, plus a manual-check sample. Never claim exact accuracy.

### 2. opening_design real drawing sets

- Real US practice drawing sets: door/finish schedules, ft-in units, multi-sheet.
- Preview: 39 count, 9 area, 16 text questions. Best public result: 51% on counts.
- This is the partner's stated focus: metric and material measurements for construction engineers.
- Most misses are about summing a quantity column versus counting rows, and reading imperial dimensions. Both are deterministic once the table is extracted.
- Demo value is higher than the question count suggests: "a real building's door schedule, with every row highlighted".

### 3. Archive scans (habs, finna, europeana, wikimedia)

- These have no questions in the preview, and we saw no team handling them.
- Only worth it as a demo moment (a historic Helsinki drawing), not for accuracy. Low priority.

## Recommended plan

| # | Work | Why | Estimate |
| --- | --- | --- | --- |
| 1 | Push Swiss + IFC coverage to ~95%+ | Table stakes; judges compare accuracy | ~3h |
| 2 | ifc_bench text answers with GUID evidence + stated judge rubric | 0/8 teams, real BIM value | ~4h |
| 3 | opening_design schedule takeoff (sum columns, ft-in parsing, row highlights) | Best public is 51%; matches partner focus | ~4h |
| 4 | Pitch: "real projects, not dataset trivia", with cost per answer shown | Differentiates from Hour49's breadth | ~1h |

**Skip:** 3D, AR, voice (3 teams have them already), the CubiCasa detector race (Hour49 leads with a big compute budget), tiling (two teams measured it as worse).

## Sources and method

GitHub repository, code and README search (Stoa, Junction 2026, blueprint, IFC, DXF, takeoff, floor plan, swiss_dwellings), plus a README keyword scan over 94 recent Junction repositories. Per-source Hour49 numbers come from their committed [answering run](https://github.com/Hour49/Junction26/blob/main/eval/results/runs/20261114-082045-answering-pipeline.json). Feature presence comes from file trees and READMEs, not from running competitor code. Private repositories and unindexed work are invisible.

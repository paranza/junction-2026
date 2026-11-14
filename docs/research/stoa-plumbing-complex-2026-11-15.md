# Plumbing and complex drawing research, 15 November

Checked public sources on 14 November, approximately 22:00–22:54 UTC
(15 November, 00:00–00:54 Europe/Helsinki). The accompanying
[snapshot](stoa-plumbing-complex-2026-11-15.json) records the inspected revisions,
discovery methods and live-site limitations. A repository is not proof of a
separately registered team. Findings below distinguish source inspection from
claims and browser observations; competitor inference was not independently run.

## Finding

The strongest relevant implementations combine positional OCR, calibrated
geometry and question-driven tools. I did not find a verifiable demonstration
among the inspected competitors of complete physical pipe lengths from an
arbitrary monochrome scanned MEP sheet. Several substantial plumbing features
instead read IFC ports and properties. Others identify equipment or candidate
symbols, which does not establish traced network lengths.

This does not mean those teams cannot answer difficult questions. Léargas has
useful implemented scan geometry; Vellum has interesting legend-conditioned
readers; OQVAR has specialist detection and tiled OCR. The main opportunity for
Metria is to give its source-inspection agent measurable geometry and persistent
OCR tools, rather than add individual handlers for anticipated judge questions.

## Most relevant competitors

| Project | Implemented technique found | What remains unestablished | Useful direction for Metria |
| --- | --- | --- | --- |
| [Léargas](https://github.com/markmannion/leargas/tree/73b23fbd9198cfa0511c93749b69f086d7037dbb) | Original-resolution tiled OCR, scale extraction, room flood-fill and contour measurements, equipment-tag and annotation tools | General pipe connectivity and complete physical network lengths on scans | Persistent position-aware OCR and calibrated region geometry |
| [Vellum, previously Countersign](https://github.com/Hour49/Junction26/tree/3e5d5eeb2cb52a2fe1b4bcf44cdad626918d91c6) | PDF path/style readers, colored-line masks, legend symbol templates; typed observations and disagreement handling | Automatic legend acquisition and complete orchestration for unknown scans; raster mask deliberately skips black/gray runs | Legend-conditioned selection, local geometry and explicit missing information |
| [OQVAR](https://github.com/lorikjashari/stoa/tree/0df652cdf3f85ee9eab381640bac3ddca87ed95b) | Tiled/rotated OCR, source-row selection, P&ID specialist candidates | Candidate detector is not an exact count; its MEP connectivity tools read IFC | Better OCR retrieval and a specialist proposal stage that still needs verification |
| [PlanProof](https://github.com/Willi-CQ/Planproof/tree/bf64999bb7980a09a2be591e06a8a4d9b9c14731) | Gemini question agent with bounded, page-scoped tools and source citations; CAD and ML geometry work | End-to-end general scanned-pipe measurement | Expand the agent's actual tools, not just the prompt |

### Léargas: the most useful scan implementation inspected

Its [word reader](https://github.com/markmannion/leargas/blob/73b23fbd9198cfa0511c93749b69f086d7037dbb/backend/app/sheet/words.py)
uses native PDF words when present and RapidOCR ONNX for scanned content.
Original-resolution tiles are 2,400 pixels with 480 pixels of overlap, with
position-aware results cached for reuse. This makes small annotations
retrievable without repeatedly asking a model to locate them in a whole sheet.

The [scale reader](https://github.com/markmannion/leargas/blob/73b23fbd9198cfa0511c93749b69f086d7037dbb/backend/app/sheet/scale.py)
considers graphic bars, dimension chains and printed scale/paper information.
Independent agreement raises its confidence. Metria should prioritize explicit
source calibration and record its extent; inferred paper sizes or conventional
dimensions must not silently become exact measurements.

The [room geometry](https://github.com/markmannion/leargas/blob/73b23fbd9198cfa0511c93749b69f086d7037dbb/backend/app/sheet/rooms.py)
uses morphology, gap closing, connected components and flood-fill around room
labels. Pixel area and contour length become physical quantities through the
scale. Door-gap deductions support approximate baseboard lengths. This is
substantive geometric work, but wall styles, open boundaries, glazing and
leafless passages can break its assumptions.

Its [sheet answer tools](https://github.com/markmannion/leargas/blob/73b23fbd9198cfa0511c93749b69f086d7037dbb/backend/app/sheet/answer.py)
cover printed dimensions, regions, room quantities and numbered equipment tags.
Exact slab-outline support elsewhere relies on named CAD layers and schedules;
it should not be mistaken for arbitrary raster reconstruction. The source also
contains an optional cached-answer fallback, which is not evidence that the
observed live deployment has enabled it or that answers are looked up from gold.

### Vellum: promising readers with important dependencies

The [PDF path reader](https://github.com/Hour49/Junction26/blob/3e5d5eeb2cb52a2fe1b4bcf44cdad626918d91c6/backend/app/adapters/discipline_pictures/paths.py)
matches legend styles and symbols against vector paths, chains segments and
measures runs with a supplied scale. Its documented limitation includes PDF
dash-array strokes. This technique is useful for vector PDFs but does not
recover vectors from a scanned image.

The [raster mask reader](https://github.com/Hour49/Junction26/blob/3e5d5eeb2cb52a2fe1b4bcf44cdad626918d91c6/backend/app/adapters/discipline_pictures/mask.py)
estimates colored line runs; it explicitly excludes black and gray because
those colors also represent text and walls. It therefore is not a ready answer
for our monochrome piping example. Its
[template reader](https://github.com/Hour49/Junction26/blob/3e5d5eeb2cb52a2fe1b4bcf44cdad626918d91c6/backend/app/adapters/discipline_pictures/template.py)
matches legend symbol crops across rotation and scale while suppressing
overlapping detections and excluding the legend itself.

These readers require supplied legend and scale providers. The
[adapter dependency definitions](https://github.com/Hour49/Junction26/blob/3e5d5eeb2cb52a2fe1b4bcf44cdad626918d91c6/backend/app/adapters/discipline_pictures/__init__.py)
leave automatic VLM legend acquisition as future work. Source presence and
adapter tests do not demonstrate an integrated unknown-upload pipeline. The
[typed picture facts](https://github.com/Hour49/Junction26/blob/3e5d5eeb2cb52a2fe1b4bcf44cdad626918d91c6/backend/app/core/picture_facts.py)
retain disagreements and unknowns. Two-reader agreement is a useful check,
not independent proof of completeness.

The repository also has a substantial editable network graph, but the inspected
graph construction reads IFC distribution ports and systems. This is distinct
from reconstructing the same graph from raster pixels. The project was still
receiving commits during research; the links above pin the files actually read,
not a claim that this revision will remain its newest HEAD.

### OQVAR: P&ID candidates, not a solved length problem

The [construction detector](https://github.com/lorikjashari/stoa/blob/0df652cdf3f85ee9eab381640bac3ddca87ed95b/stoa_qa/construction_detect.py)
adds valve, pump and instrumentation candidates. Its P&ID answer route returns
possible detections with confidence 0.45 and no numeric answer. Availability
depends on configured weights. This is a proposal stage, not a demonstrated
exact inventory or physical pipe-length solver.

Its [OCR reader](https://github.com/lorikjashari/stoa/blob/0df652cdf3f85ee9eab381640bac3ddca87ed95b/stoa_qa/sheet_ocr.py)
uses original-resolution overlapping tiles, a rotated pass for vertical text,
edge handling and a content-hash cache. Its
[document QA](https://github.com/lorikjashari/stoa/blob/0df652cdf3f85ee9eab381640bac3ddca87ed95b/stoa_qa/docqa.py)
can select source rows and execute arithmetic over them. Some source-specific
profiles are also present, so copying its dispatch rules would not establish
generalization. The [MEP graph tools](https://github.com/lorikjashari/stoa/blob/0df652cdf3f85ee9eab381640bac3ddca87ed95b/stoa_qa/mep.py)
operate on IFC, which the user reports is excluded from the final evaluation.

## Other discoveries and live sites

Newly located [PlanProof](https://github.com/Willi-CQ/Planproof/blob/bf64999bb7980a09a2be591e06a8a4d9b9c14731/backend/question_agent.py)
has a genuine tool-using question agent. Its context documents acknowledge
coverage still to extend. [Trilobyte](https://github.com/PianoPiston/trilobyte/tree/10fa79cb3afbcb2d870b858c99d8b1542e5effcb)
combines structured drawing data, native readers, symbol detection and a
fine-tuned small vision-language model. Its published answered-question metrics
do not establish accuracy on unfamiliar complex scans.
[Blueline](https://github.com/Paulsg777/blueline-stoa/tree/e67333cf0482fb3369452c7b8ea3e406f7d93c7c)
exposes a frontend and API contract; the inspected tree does not provide its
full inference backend. These repositories are additional public Stoa-related
projects, not proof of three newly registered competitors.

| Public site | Browser observation | Limit of the observation |
| --- | --- | --- |
| [Léargas](https://leargas-blue.vercel.app/) | Drawing register opened, original 10,200 × 6,600 piping scan loaded, geometry and model controls present | No question submitted; model quality and latency not measured |
| [Vellum](https://junction.hour49.com/stoa/) | Public sample workflow opened and rendered a result | Site explicitly labels this a clickable demo using its fixed sample; full app requires an access code |
| [Hologram](https://hologram-khaki.vercel.app/) | Workspace reached a connected state with question controls | No upload or question tested; not proof of complex drawing performance |

No competitor files were uploaded, inference requests made, access codes entered
or competitor code executed. A static sample, live frontend and functioning
general inference service are different evidence.

## An external implementation closer to the missing pipe graph

[Microsoft's public P&ID digitization sample](https://github.com/Azure-Samples/digitization-of-piping-and-instrument-diagrams/tree/c51302e3ec34147c676ef6eedbdd7551ea908b05)
is not a Junction competitor. Its implemented pipeline separates symbols and
text from line detection, then constructs a connectivity graph. The
[line service](https://github.com/Azure-Samples/digitization-of-piping-and-instrument-diagrams/blob/c51302e3ec34147c676ef6eedbdd7551ea908b05/src/app/services/line_detection/line_segments_service.py)
uses OpenCV Hough segments, and the
[graph service](https://github.com/Azure-Samples/digitization-of-piping-and-instrument-diagrams/blob/c51302e3ec34147c676ef6eedbdd7551ea908b05/src/app/services/graph_construction/graph_construction_service.py)
connects geometry to components. This is a concrete architectural reference,
not a drop-in calibrated-length guarantee. A schematic's drawn lengths may not
represent physical distances. No Azure infrastructure was provisioned or sample
code executed.

A separate [public P&ID VLM experiment](https://github.com/deepkick/pid2graph-vlm-eval/tree/7b3a08d290d29d41c3d82bd79f5d98af47154824)
reports better symbol recall after tiling and seam filtering, but very poor
connection-edge extraction. Its author reports roughly 0.884 node F1 and 0.03
edge F1, on a small study not reproduced here. These are different metrics.
They support investigating a hybrid geometry pipeline; they do not prove its
performance on Stoa or justify advertising symbol scores as network accuracy.

## What to build next in Metria

Metria already has original-resolution, question-driven inspection, scoped
evidence and checked dimensional expressions. Its
[small paired development study](../evaluation/complex-source-inspection.md)
improved seven complex numerical checks from 5/7 with the prior Carbon path to
7/7 with source inspection. That does not validate complete pipe geometry.

1. **Persistent positional OCR.** Build a content-addressed index of words,
   polygons, orientation and source scale, using native PDF text first and
   overlapping scan tiles where needed. Let the agent retrieve text and nearby
   source pixels together. This helps schedules, room labels, dimensions,
   equipment tags and technical notes across drawing types.
2. **Source-calibrated geometry tools.** Read explicit dimension references and
   scale bars with located evidence. Expose polygon area/perimeter, path length
   and region intersection. Do not infer real lengths from typical door sizes
   or resized-screen pixels. Track different detail-view scales separately.
3. **Legend-conditioned extraction.** Identify symbols, relevant stroke styles
   and system labels from the actual legend. Exclude legends and repeated
   details from counts. Give overlapping tiles unique ownership and merge
   shared observations in original coordinates.
4. **A measured graph for networks.** Trace selected line centerlines, preserve
   junction/crossing ambiguity, link components and continuation tags, and
   attach diameter/system labels to edges. Queries can then sum or filter
   measured edges rather than ask the model to estimate a network's total.
5. **Adversarial complex checks.** Include monochrome crossings, dashed runs,
   rotated labels, multiple scales, repeated details, partial selections and
   multi-sheet continuations. Freeze changes before comparing cases. Verify
   geometry and final answers separately; a symbol detector's score cannot
   substitute for correct end-to-end quantities.

These are follow-on implementation priorities, not features delivered by this
research update. No competitor source was copied into Metria. MIT-licensed
references still require attribution if code is reused; public visibility alone
does not grant permission to copy the unlicensed projects.

## Search coverage

Discovery combined GitHub repository queries, exact challenge-title code
search, domain-specific code searches across 17 seed/new repositories, public
source trees and linked websites. The snapshot includes newly qualified
projects, metadata-only refreshes, unrelated matches explicitly excluded and
external references. It is a bounded public search, not an exhaustive inventory
of hidden, unindexed or subsequently published work. No private repositories,
credentials, reference answer files or model weights were accessed.

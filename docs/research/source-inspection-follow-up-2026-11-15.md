# Source inspection research follow-up

Checked 15 November 2026, approximately 02:13 UTC. This extends the earlier
[public competitor inspection](stoa-plumbing-complex-2026-11-15.md). Source code
and a published paper are evidence of methods, not measured competition wins.
No competitor service received an upload or inference request.

## Research that informs the implementation

[Zhu et al., From P&ID Drawings to Process Graphs](https://arxiv.org/abs/2607.19568)
separates visual extraction from process topology reasoning and evaluates two
ANSI P&IDs. That distinction is useful, but topology extraction does not establish
scaled physical lengths. Metria separates source localization and route review
from host geometry and unit arithmetic. It does not create unseen connections
or vertical lengths to make a graph look complete.

[Microsoft's digitization architecture](https://github.com/Azure-Samples/digitization-of-piping-and-instrument-diagrams/blob/main/docs/architecture.md)
combines symbol detection, OCR, line extraction and graph construction. This
supports using multiple kinds of source evidence. Summing every dark line in a
monochrome scan would also measure walls, text and leaders, so Metria retains
semantic selection and displays the actual proposed paths over the source.

## Changes in public competitor source

Vellum advanced substantially since the earlier snapshot. The inspected revision
is [8e07aa4](https://github.com/Hour49/Junction26/tree/8e07aa41e5176547335b47155315d9af7c99aeb2).
Its [picture lane](https://github.com/Hour49/Junction26/blob/8e07aa41e5176547335b47155315d9af7c99aeb2/backend/app/adapters/discipline_pictures/lane.py)
now wires local OCR legend acquisition, symbol templates and colored-run readers
into stored, low-confidence picture facts. The earlier missing-provider finding
is therefore historical. The [legend reader](https://github.com/Hour49/Junction26/blob/8e07aa41e5176547335b47155315d9af7c99aeb2/backend/app/adapters/discipline_pictures/legend.py)
documents a single-column heuristic and limited scale-bar recognition; automatic
acquisition is not equivalent to arbitrary legend understanding.

Its [DINO verifier](https://github.com/Hour49/Junction26/blob/8e07aa41e5176547335b47155315d9af7c99aeb2/backend/app/adapters/discipline_pictures/dino_match.py)
uses frozen DINOv2-small features to reject some template look-alikes. It explicitly
does not discover missing candidates, and the inspected default targets scanned
air terminals after other categories regressed. This is not a ready solution to
our missed office chairs or passage doors. A useful next experiment is to build
source-derived symbol proposals and audit alternative shapes, retaining both
false-positive and false-negative checks rather than optimizing one total.

PlanProof's current inspected HEAD is
[d8ecb51](https://github.com/Willi-CQ/Planproof/commit/d8ecb5120ed3f145c40e9ab3e223729f1bcbd44c),
with a deployment-verification record. That commit alone does not establish an
improved complex takeoff algorithm. Leargas repository metadata still reported
its 14 November 22:29 UTC push. The previous OQVAR repository URL now redirects;
no conclusion about its current backend is drawn from that redirect.

## Applied changes

The implementation adds OCR prime preservation and bounded context recovery,
closed perimeter and disjoint-route measurement, source overlays with focused
opening details, and resumable audited tiles bound to source, question and policy.
These are general mechanisms, without per-drawing answer profiles. Large tiled
counts and whole-route tracing remain opt-in while the actual-source studies
run. Research source was read, not copied into the application.

## Open-vocabulary counting follow-up

[CountGD](https://proceedings.neurips.cc/paper_files/paper/2024/hash/57c56985d9afe89bf78a8264c91071aa-Abstract-Conference.html)
combines text and visual exemplars for open-world counting. The later
[CountGD++ implementation](https://github.com/niki-amini-naieni/CountGDPlusPlus)
adds exclusion prompts and inferred exemplars; its documented installation uses
CUDA, compiled GroundingDINO operations and detectron2. These results do not
establish accuracy on construction symbols or passage-versus-cabinet semantics.
The applicable design principle is to discover candidates separately from deciding
whether each source object satisfies the question, preserving explicit exclusions.

The candidate implementation now finds compact source components and enclosed
forms using the existing located objects' scale and ink style. It can propose an
alternative shape without a filename-specific symbol template. A question-driven
model classifies every supplied ID on original source crops; the host validates
ID coverage and reconciles positions. Image processing alone never contributes a
count. This is implemented with existing CPU dependencies, not a claim that a
CountGD model was installed or trained.

[SAM 3's official installation](https://github.com/facebookresearch/sam3#installation)
documents CUDA requirements and approved Hugging Face checkpoint access. It is a
possible concept-segmentation experiment, not an already integrated feature.
Neither a CUDA stack on the protected application VM nor another GPU VM was
provisioned for this follow-up. Product inference and the independently recorded
source-only studies continue with the authorized Gemini configuration.

The implemented follow-up now audits all initial locations before discovery,
reads original source keys for symbol meanings and requires a physical role for
accepted objects. Source components only propose locations. This directly caught
the difference between a walk-in store and a shallow wall cupboard, and between
legend-defined chairs and excluded stools. A matching aggregate total alone is
not sufficient evidence of correct object grounding. Checker-bar pixel alignment
also separates source scale geometry from a model's approximate coordinates.

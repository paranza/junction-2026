# Stoa final evaluation guidance, 14 November 2026

Read directly in Junction Community's [Stoa channel](https://discord.com/channels/1268184974784336004/1564622781994508369)
and the authenticated [challenge brief](https://hackjunction.app/participate/45/challenges/335).
Times below are Europe/Helsinki. These are partner statements, not a scoring
guarantee or a description of an automated hidden-test API.

## Confirmed guidance

| Source | What the partner said | Consequence for our work |
|---|---|---|
| Eino, 11:56, edited 12:10 | Evaluation uses a few complex drawings and questions; real questions can be more complex than dataset examples. | Simple preview QA coverage is an incomplete proxy for the final task. |
| Eino, 15:32 | Evaluation drawings are unreleased; performance on the provided dataset is also considered. | Test unfamiliar sources and preserve a separate regression benchmark. |
| Eino, 11:58 | Replied affirmatively when asked whether the questions target numerical quantities. | Make checked numerical quantities the primary path, rather than relying on descriptive responses. |
| Eino, 15:41 | Examples include floor areas, baseboard linear metres, door/window counts and slab area by thickness and reinforcement; piping understanding would impress them. | Prioritize scanned quantity takeoff and clear evidence, including structural and MEP examples. Piping is a suggested differentiator, not a mandatory feature. |
| Eino, 18:43 | Formats are mixed, with the hardest questions focused on scanned PDF/PNG drawings. | Reading small annotations and preserving image detail is a first priority. |
| Eino, 18:45 | An interactive interface is acceptable; accuracy is judged against a specific blueprint. | Clarify sheet, area and quantity scope through the existing chat and selection workflow. |
| Eino, 18:47 | Projects can contain multiple buildings/drawings, but accuracy is evaluated on one blueprint; innovation and impact cover the whole chosen workflow. | Do not assume that restoring a Projects page is necessary for scoring. |
| Eino, 18:51 | Judges adapt to submitted interfaces and accuracy is only one evaluation component. | Exercise upload, selection, evidence inspection and corrections in the actual app. |
| Eino, 10:07 | Ingestion cost of a few cents is not weighted heavily; a drawing costing around ten dollars would matter. | Record ingestion and follow-up usage separately and report list-price cost before credits. |
| Eino, 11:57 and 22:09 | Human-created reference answers may contain errors. | Preserve the frozen scorer; audit disputed source facts separately rather than quietly changing gold labels. |
| Pyry, 18:14 | Some proposed door examples are closet doors. | Preserve explicit door-category interpretation and the existing distinction from furniture fronts. |
| Eino, 19:07 | A screen recording with spoken narration is acceptable for the demo video. | Professional editing is not required by this guidance. |

The current challenge page gives equal weights: answer accuracy 25%, visible
verification 25%, creativity 25% and low inference cost 25%. It lists Stoa
prizes of EUR 1,000, EUR 750 and EUR 250, with a work trial for the overall winner.
No assumption about stacking other awards follows from these statements.

## Public sample drawings

Eino attached these examples at 15:41. Copies and source URLs are held privately;
the repository does not redistribute the images or reference-bearing answers.

| Filename | Source pixels | Initial gap |
|---|---:|---|
| `uk_dfe_sen-dfe-xx-00-d-x-0201-special_school_plan_level_00-a-c01_p001.png` | 14,000 x 9,902 | 138.6 MP exceeded the app's old 100 MP processing limit. |
| `us_aw_078-24-28_march_2020_p096.png` | 10,200 x 6,600 | Dense piping labels and imperial dimensions need source-resolution inspection. |
| `us_aw_078-24-33_p056.png` | 9,934 x 7,017 | Slab classes, reinforcement notes and dimension chains require more than counting residential symbols. |
| `us_daf_dorm_sd_drawings_april_2026_p003.png` | 10,200 x 6,600 | Area summaries use square feet and require explicit scope and unit conversion. |

These are now development examples. They must not later be described as
untouched hidden tests. The separate 924-question preview reserve remains
quarantined, including duplicate cases appearing in a larger download.

## Current implementation response

The raster limit is explicitly bounded at 160 MP and 120 MB. Large scan rendering
uses the existing two-slot, time-bounded parser process pool. Preview rendering
reduces image size before expensive RGB copies where possible. A selected raster
region comes from original oriented pixels, not an already reduced overview.
PDF/SVG selections render the source clip directly; rotated PDFs preserve page
appearance without saving changes to the file. This improves readability and
does not itself establish measurement accuracy.

The visual quantity calculator converts compatible source units, such as SF to
square metres. It refuses quantities of the wrong physical dimension. Source
readings remain provisional when native text has not verified them. No example
filename, reference answer or per-drawing count is added to the application.

Google's [published standard Gemini rates](https://aistudio.google.com/docs/pricing)
were checked again: Argon and Carbon list USD 2/1M input, USD 0.10/1M cached
input and USD 10/1M output through November 30, 2026. Output includes thinking.
Argon now has the same dated pricing support already present for Carbon.
Unknown usage and expired rates remain unknown, and explicit overrides retain
precedence. These are token estimates before credits, not invoice totals.

## Focus for the next implementation slices

1. Verify the four public examples through upload, region selection and source
   inspection, with bounded real model calls and independently read checks.
2. Build reusable annotation and dimension evidence for scans, with exact source
   crops and explicit units. Keep transcription verification separate from
   arithmetic and semantic selection.
3. Connect those operands to checked area/perimeter calculations. Baseboard
   lengths need clear opening deductions; slab grouping needs explicit type
   and reinforcement selection. The current visual fallback can sum compatible
   printed quantities and has a conservative quoted-rectangle path, but is not
   a general dimension-chain or pipe-network solver.
4. Add targeted inspection of piping symbols, tags and diameters. Do not claim
   whole-network topology or pipe lengths from a few successful note readings.
5. Use the full archive to select additional unfamiliar complex drawings. Check
   integrity, disk space and duplicates before extraction. Keep raw data, gold
   labels and credentials outside Git and inference prompts.

The user directed current work toward this evaluation. Detector fine-tuning and
competitor work are not the current priority; the rejected detector stays off.

# Complex drawing source inspection

The user redirected work to difficult unseen blueprints, rather than improving
a mixed benchmark dominated by easier native cases. IFC is compatibility only.
This work adds a question-driven source inspection path without training on
question answers or adding per-drawing lookup rules.

## Implemented path

The agent reads an overview, requests relevant source-resolution regions and
then answers from those views. Counts begin with six overlapping sectors
covering the complete requested page or selection. Each crop is rendered from
the original raster or PDF clip, rather than enlarged from a reduced overview.
All located evidence maps back to the original page. Overlapping observations
of the same source item are removed.

For quantities, the model supplies source operands and a bounded expression.
Python checks quoted quantities, unit compatibility and arithmetic. Supported
operations include sums, differences, products, division with supported physical
output units, minima, maxima and means.
There is no execution of generated Python, no arbitrary constants and no
fallback to summing everything when a comparison was requested. Printed bare
dimensions require a source unit note or an explicit drawing-unit declaration
in the question. Source reading and semantic selection remain provisional.

The default is `STOA_COMPLEX_READER=auto`: use this fallback for PDF files and
rasters of at least four megapixels, after available native tools. The selected
inspection model is `gemini-4-argon`, with high reasoning, ultra-high image
resolution and a 65,536-token per-request output allowance. The inspection stage
has at most three requests and eight detail views. Other enabled tools, such as
question translation, can make additional requests. Every request uses the existing
cumulative model-attempt cap, usage accounting and provider key. Set
`STOA_COMPLEX_READER=off` to retain the previous visual path. The base provider
and inventory policy are separate settings.

## Paired live comparison

Application prototype `c52da9a` was frozen before the comparison. Seven numerical
checks on the four public Stoa example drawings used identical questions and
whole sheets, without manually selected regions. They covered equipment and
classroom counts, annotation reading, unit conversion, area differences and
maximum selection. Reference values were independently read from the source,
kept private and never included in inference inputs.

| Path | Correct checks | Actual requests | Estimated USD before credits |
|---|---:|---:|---:|
| Existing Carbon visual path | 5 / 7 | 7 | 0.21225 |
| Existing visual path with Argon | 2 / 7 | 7 | 0.33933 |
| Argon with source inspection and checked expressions | 7 / 7 | 12 | 0.37301 |

The existing path sometimes treated an area comparison as a sum, or counted a
quantity twice when it was cited in multiple views. The inspection path
correctly executed the requested differences and maxima. Its median latency
was 38.2 seconds, with a range of approximately 32 to 65 seconds in this run.
The isolated runtime retained all 26 attempts under its unchanged 64-attempt
ceiling. There were no technical request failures and no reserved cases were
inspected or scored.

These are development checks on public example drawings. They establish a
functional improvement on these cases, not a general accuracy percentage or
proof that every complex blueprint can be answered. Simply selecting a more
capable model did not fix the application's evidence and calculation errors.

## Application validation

The enabled path at `a492d7c` passed an actual API count, exclusion and
restoration, JSON export and cached replay with zero new calls. A selected-region
area comparison passed after independently auditing that both source operands
were inside the region. The first validation region excluded one operand: the
application correctly refused, while the initial harness incorrectly expected
a numerical answer. Its original record is preserved, with this source audit
kept separate from the frozen comparison.

A missing-project network control returned no invented total and identified
missing continuation sheets and vertical information. One later request failed
with HTTP 503 after a transport wait of about 629 seconds. It remains a recorded
failed attempt with unknown usage; a separately recorded retry succeeded. The
isolated cumulative counter is 34/64, without resetting or replacing failures.
This provider reliability limit remains even when source reasoning succeeds.

The final backend suite passed 427 tests, including dimensional-expression,
scope, duplicate and inspection-budget checks. The native solver source files
and the native analysis prefix are unchanged from the last full regression.
At the user's direction, the 7,066-case simple/native benchmark was not repeated
for this model-path change. The prior frontend tests and build apply to the
identical frontend source tree and compiled assets. No new interface controls
or provenance panels were added.

## Remaining limits

The current agent operates on one page or selected region. A document-wide
request over several pages falls back to existing scope-aware tools; it does
not silently describe one inspected page as a complete packet. Unknown
wording can choose different source regions and expressions, but operations
outside the expression language remain unsupported.

Original pixels do not recover detail absent from a low-resolution source.
The agent does not yet establish arbitrary polygon tracing, dimension-chain
reconstruction or complete pipe-network topology. Multiplying two quoted
dimensions checks arithmetic, not the correctness of an assumed rectangular
boundary. A visual quantity is reviewable evidence, not independent proof of
OCR, geometric interpretation or detection completeness. Missing off-sheet or
vertical information must remain explicit.

Raw images, question-level reference values, model responses and private
configuration remain outside Git. No fine-tuned residential detector was
enabled, and no new GPU or VM was provisioned.

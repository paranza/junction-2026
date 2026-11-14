# Drawing geometry tools

15 November 2026. This extends the complex-source reader with source tools,
without question-answer lookups, drawing-name dispatch or a new trained model.
The application still attempts native tools before complex PDF/image inspection.

## Implemented behavior

- Persistent positional OCR uses original-resolution overlapping tiles and a
  rotated pass. Native PDF words retain the page rotation. Cache keys include
  source content, page, source region, orientation policy and tool revision.
  Cached content is source text and coordinates, not model or reference answers.
- Source calibration requires a located printed length and actual reference
  endpoints. OCR/native text must reproduce the quote and support its units.
  Calibration is restricted to the same source, page and declared scale region.
- Polygon area, perimeter and polyline length are computed locally with source
  aspect ratio retained. Self-intersections, scope escapes and fabricated
  calibration IDs are rejected. Closed-ink room regions are also measurable.
- Network tracing supports selected colors or monochrome ink, optional located
  OCR removal and a connected-component seed. Skeleton edges are visited once,
  including closed loops and shared branches. Located edges retain lengths and
  optional nearby source labels for model-assisted system selection.
- Legend/example symbol matching considers rotation and nearby scales, excludes
  the source template and suppresses overlaps. Results are proposals, not exact
  inventories. Original straight PDF vector segments expose their source stroke
  style, dash information and calibrated lengths; unsupported curves are explicit.
- The reader can call these tools and cite their stored result IDs in checked
  expressions. The server substitutes its own computed values and coordinates;
  model-supplied numbers and forged IDs cannot override them. Measurement tools
  cannot masquerade as count evidence. All geometry remains provisional.

The source reader permits three visual decisions and three tool rounds, with
eight detail views and ten local tool attempts. The same existing cumulative
provider-attempt ledger accounts for every model request. Reaching the view
budget now requests an answer from collected evidence or an available local
tool rather than abandoning an otherwise readable count.

Named drawing regions such as Area A no longer force an area answer when the
question requests a diameter. A bare table cell can use a separately located,
aligned single-unit header; missing or conflicting headers cannot establish
units. Feet-only prime annotations are recognized without truncating combined
feet-and-inches dimensions. These are general source/quantity rules.

## Verification and comparison protocol

The initial integration passed 441 backend tests; the final scope, header,
rotation, graph, geometry and agent checks bring the suite to 447 passing tests.
The frontend source tree is identical to the previous release with its passing
59 tests and production build. No frontend controls were added.

The source-tool candidate retained all seven previously frozen public complex
checks in a live development rerun. Two generated geometry fixtures separately
exercise capabilities unavailable in the old reader. Newly located public
drawing checks compare the prior reader and candidate on identical questions.
Expected values are private and used only after inference. These are development
checks, not a hidden-test or general accuracy estimate. Raw records and failures
are retained outside Git; release results are recorded separately.

An initial provider rejection exposed excessive schema decoding states. Nested
array limits moved to host validation; a real provider request confirmed schema
acceptance. That failed candidate remains recorded rather than replaced. A later
reference audit found a blank pump-table header, invalidating an assumed unit in
one expected answer. The original manifest and results remain unchanged, and
the corrected interpretation is recorded separately. A refusal on missing units
must not be reported as a failure to read a valid quantity.

No reserved questions or independent reserved-file evaluation were used. The
large native development benchmark was not repeated. Native geometry/query
modules remain unchanged; native quote parsing only adds feet-only candidates
and preserves existing combined-dimension matching. Relevant native tests remain
part of the backend suite.

## Remaining limits

Source text, calibration endpoints and semantic selection can still be wrong.
Room flood-fill depends on closed walls and can include furniture artifacts.
Template similarity cannot establish complete detection. Monochrome tracing
also sees walls and text; a color or a spatial selection does not automatically
separate all pipe systems. Crossings, dashed gaps, obscured runs and symbols
interrupting lines require interpretation. Nearby text is a candidate edge
annotation, not a proven diameter assignment.

A detected centerline graph is not proof of complete physical installed length.
Vertical runs, missing continuation sheets and not-to-scale schematics remain
outside what a calibrated page proves. The current complex inspection session
is single-page/selected-region; packet-wide requests retain the existing
scope-aware fallback. PDF curves are not measured by the straight-vector tool.
Large OCR regions and dense graphs have processing caps and return errors or
incomplete results rather than silently publishing a partial total.

See the [48 source-linked practice questions](complex-practice-questions.md) for
six sheets covering plumbing, schedules, renovation, geometry and electrical
questions. These are practice prompts, not known judge questions. Source files
stay outside Git and their public links do not grant redistribution rights.

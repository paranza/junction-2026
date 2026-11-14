# Native attributes and bounded inventory recovery

The question planner selects operations over source records. Python retrieves
exact attributes and computes quantities; model prose does not supply operands.
This extends the available tools rather than adding question-answer lookups.

IFC extraction now retains all exported entities' property sets, material names,
declared material-layer thicknesses and typed opening dimensions. Room area
heuristics remain restricted to spaces. Project units must be explicitly known
before dimensions or layer thickness become SI quantities. Original properties
and quantity provenance remain available for checking.

The planner can retrieve one textual attribute, list distinct source strings,
list attributes per object, or return typed quantities for each selected object.
Every measurement row requires a compatible source quantity. An untyped numeric
property cannot become a measurement merely because the model selects it.
Missing operands reject the result rather than producing a partial total.
Text retrieval cannot bypass count or measurement checks.

Large IFC schemas share property-set paths across entity types in the prompt.
Examples remain bounded and explicitly incomplete. Queries execute over the
complete selected source collection, including objects omitted from examples.
The catalogue does not establish that every entity has each field.

An optional `STOA_INVENTORY_FALLBACK_MODEL=gemini-4-argon` enables one stronger
read only after all normal visual inventory readings fail recoverably. It is
off by default. It does not replace a successful primary reading. Authentication,
configuration, quota and allowance failures do not trigger it. Each real attempt
uses the existing atomic cumulative request counter. The request-local policy
uses ultra-high images, high thinking, 65,536 output tokens and detail crops;
other concurrent requests retain their configured policy.

Optional ONNX box models now declare RGB or grayscale preprocessing and either
whole-page or overlapping tile inference. Tile ownership and global suppression
prevent duplicate boundary objects. Outputs remain visual candidates, never
verified physical dimensions. No detector is enabled by default.

The source-level checks use generated IFC data, missing-field cases, mixed intent,
independent unit conversions and tile-boundary geometry. Real Gemini functional
checks of exact source attributes previously passed 4/4 generated cases. Those
small checks are not an accuracy benchmark. Dataset results, native regressions,
deployment and detector selection are recorded separately with source hashes.

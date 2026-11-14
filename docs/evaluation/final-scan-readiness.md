# Final evaluation readiness: PDF and image drawings

The user reports that final evaluation excludes IFC files as too easy. Treat
structured-model results as compatibility evidence, not as evidence of scan
accuracy. The partner previously emphasized complex scanned PDF/PNG drawings
and numerical questions. See [the source guidance and later team update](../research/stoa-final-evaluation-20261114.md).

## What is actually measured

The frozen development run at `190e116` scored visual CubiCasa counts at
3,063/3,426 answered questions, or 89.40%. Against every selected CubiCasa
question, including nonanswers, errors and unrun cases, it scored 3,063/3,534,
or 86.67%. These are residential drawing counts, not a benchmark of complex
structural or MEP measurements. The mixed-source 94.54% precision includes
structured data and must not be used as the headline for final scan readiness.
See [the frozen full development report](development-auto-190e116.md).

At `24b7a66`, four public Stoa example scans passed original upload, document
retrieval and preview. Three source-audited numerical checks passed live Gemini
Carbon requests after generic notation and unit fixes. All three failed the
application's validators before these fixes, even though the model had read the
source operands correctly. They are debugged development checks, not fresh
independent tests or an overall accuracy estimate. They do not demonstrate
whole-network pipe lengths, arbitrary floor areas or complete geometry tracing.

Twelve additional PDF/image files from the full archive passed document
retrieval and preview with no model calls. Their questions have not been scored.
The two accompanying native IFC checks are excluded from scan readiness.

## Development priority

Use one question-to-evidence workflow across quantities and object classes.
Inspect original source regions, collect relevant symbols or printed operands,
check source scope and units, and execute reproducible calculations. Exercise
counts, aggregates, comparisons, attributes and selected regions across drawings.
Do not specialize for a guessed final question or one object category.

The application does not yet establish high accuracy for arbitrary dimensional
chains, unlabelled geometry, network topology or off-sheet continuations.
Native arithmetic checks cannot prove that a visual reader selected every
relevant object or the correct annotation. Preserve those distinctions in
evaluation rather than increasing coverage by accepting unsupported numbers.

The 924-question preview reserve and the independently released reserved-file
evaluation are not part of these development checks. Raw assets, gold answers
and credentials remain outside Git and model prompts.

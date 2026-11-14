# Independent upload evaluation

This corpus tests files outside the Trace preview and the four earlier upload spot checks. It is separate from the prospective preview reservation, which remains untouched. No corpus file is used to train a model or supply an inference answer. Source selection and procedural generation were performed without inspecting outputs from the new analysis pipeline. The freeze predates its first evaluation, not necessarily the start of every implementation change.

The [public frozen snapshot](unseen-generalization-snapshot.json) contains source URLs, licences, input hashes, split membership and private-reference hashes. Actual files, seeds, references and raw answers stay under an ignored `.local/` directory. Source identity is not an inference feature: file names are opaque, and the existing batch runner sends only the uploaded drawing, question and ordinary scope fields. Reference values never go to the application.

## Corpus scope

- Development: six novel procedural drawings, one each in PNG, JPEG, PDF, SVG, TIFF and WebP; 18 questions.
- Reserved: six different procedural drawings across those same formats, plus four external architectural floor plans; 26 questions.
- Procedural questions cover doors, windows, printed areas, dimensioned rectangular footprints and missing-scale controls. Door orientation, room count, dimensions, layout proportions and whole-plan rotation vary. Each input group belongs to only one split; related format exports are not divided across splits.
- The six-format test is format coverage, not six independent real-world drawing styles. The procedural renderer has its own conventions, and passing it does not establish general architectural accuracy.
- External references come from independent visual inspection of readable labelled rooms, standard fixtures or explicitly scoped exterior doorways. Ambiguous total-door or floor-area interpretations remain unscored. These are analyst annotations, not an expert-certified external benchmark.
- Eight external sources were fixed in advance. Four download successfully and enter this frozen corpus; four are unavailable under Wikimedia's current `429` response and `Retry-After`. They are not counted as tested inputs or added silently after the freeze. A later supplement requires a new, separately hashed freeze.

All four downloaded external originals were checked against preview file byte hashes and exact original raster pixel hashes; no match was found. This does not detect every crop, resized copy or cross-source derivative. Public web images might also have appeared in a foundation model's pretraining. "Unseen" here means not present as an exact preview input or earlier app test and not used to train our own model; it is not proof of foundation-model novelty.

## Run without exposing reference labels

Use the repository's Python environment with Pillow and PyMuPDF. The frozen private corpus on the research machine is `/tmp/stoa-blind-generalization/.local/generalization-corpus`; it is not transferred by Git. Teammates need a separate explicitly frozen local corpus or a secure transfer of this one. The private seed file makes its generation reproducible, and the generator refuses to overwrite an existing freeze.

From `stoa-trace/`, prepare ordinary JSONL requests. Choose a new output filename for each selection:

```sh
python ops/generalization_corpus.py requests \
  --corpus /path/to/private-corpus --split development \
  --kind procedural --tasks doors --output /tmp/development-doors.jsonl
```

Freeze the application commit, model, prompts, extraction settings and spending limit before releasing reserved requests. Do not read reserved references or inspect errors while changing the algorithm. A compact blind count run can use the six procedural door questions plus the four external count questions:

```sh
python ops/generalization_corpus.py requests \
  --corpus /path/to/private-corpus --split reserved \
  --kind procedural --tasks doors --output /tmp/reserved-doors.jsonl
python ops/generalization_corpus.py requests \
  --corpus /path/to/private-corpus --split reserved \
  --kind external --tasks counts --output /tmp/reserved-external-counts.jsonl
```

Pass these label-free files to `ops/batch_answers.py`, with the private corpus directory as `--input-root` and explicit `--upload-unmatched`. Native mode is the zero-model default. Automatic or vision mode requires `--allow-paid` and still obeys the server's existing request cap. A count plus an independent audit can consume two calls, so budget the run before starting; this corpus tool itself makes no network or model requests.

After the frozen code has answered, score locally:

```sh
python ops/generalization_corpus.py score \
  --gold /path/to/private-corpus/reserved-gold.json \
  --answers /tmp/reserved-answers.jsonl --code-revision TESTED_GIT_SHA \
  --release-reserved --output /tmp/reserved-score.json
```

The scorer rejects changed frozen references, unknown or duplicate answer rows and missing code revisions. It reports unrun and ambiguous cases explicitly. Counts require exact values. Areas use compatible units and a 2% tolerance. Missing-scale cases require a genuine non-error abstention and are reported separately, so refusing answerable questions cannot inflate numeric accuracy. Procedural object localization uses one-to-one matching at 0.3 box IoU, separate from count accuracy.

After this reserved result is inspected, the set has been consumed for that milestone. Fixes motivated by its errors need a new independently selected test set. Do not repeatedly optimize against it and continue calling it blind. No result from this small corpus can establish 99.9% accuracy on arbitrary files or every blueprint format.

## Verification

Six model-free tests cover six-format generation, split separation, source variation, immutable freezes, label-free requests, exact count scoring, unit conversion, non-error abstention, spatial evidence matching and missing/duplicate cases. No live model requests were made to prepare this corpus.

## Frozen Gemini milestone, 14 November 2026

The independent reserve was released once against runtime code `a8a8422` (recorded solver `8dd0564f1b9a9c16f9ad`), Gemini 4 Carbon with medium reasoning, high image resolution, a 24,000-token output cap, 600-second timeout, no small-image crops and no visual recheck. The separate 924-question preview reserve was not scored or inspected.

All 26 questions across ten new drawing groups completed without request errors. Of 20 answerable numeric questions, **18 were correct and two were unanswered**, for **90% including abstentions as failures**. All 18 answered numeric questions were correct. Three required-abstention controls passed; three ambiguous external references remained unscored. The four external plans supplied four scoreable numeric questions, all correct, one abstention control and three unscored interpretations. The six procedural plans supplied 16 numeric questions, 14 correct, and two successful abstention controls.

Twelve procedural localization cases had precision and recall 1.0 at the predeclared **0.3 box IoU** threshold. That lenient synthetic-location check is separate from real-world detection quality. The run used 26 actual model calls and an estimated **$0.653022** in provider tokens before credits. Counts are exact; compatible areas use 2% tolerance.

[Aggregate result and policy identity](../../stoa-trace/ops/reports/gemini-release/independent-uploads.json). Raw files, responses and references remain private. This reserve is now consumed for this milestone; its errors must not be used for tuning followed by another blind claim on the same files. Subsequent Cloudinary close-ups operate on selected source regions and do not supply measurements or model answers. This result does not establish 99.9% accuracy or general reliability across arbitrary internet plans.

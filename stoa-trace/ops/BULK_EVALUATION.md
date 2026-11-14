# Bulk evaluation

`bulk_evaluate.py` runs an explicitly selected frozen source partition. Labels are used only by the local evaluator. Requests contain document ID, raw question, page, scope, mode and visual-recheck policy. It never uploads reference labels, expected quantities, source categories or benchmark hints.

For CubiCasa development, all 3,534 questions cover 198 drawings and 1,767 unique normalized image/question pairs. Workers run different drawings concurrently, with each drawing's questions sequential. The default disables per-question visual recounts so the initial inventory can serve all translated/category questions. Expect roughly 198 inventory calls on a cold server, rather than 3,534 second passes. Rendering, failures and cache state can change actual usage.

Start a dedicated backend with Gemini configured privately and an explicit persisted server model-attempt cap. Do not reset production counters or use the final reserved partition for development. Then, from `stoa-trace/`, using the application's Python environment:

```sh
python ops/bulk_evaluate.py \
  --manifest /path/to/frozen/development.json \
  --source cubicasa5k --base-url http://127.0.0.1:8796 \
  --mode auto --allow-paid --concurrency 4 --max-model-calls 250 \
  --code-revision ACTUAL_APPLICATION_GIT_SHA \
  --output .local/gemini-cubicasa/raw.jsonl \
  --summary .local/gemini-cubicasa/summary.json
```

`--verify-visual` enables the normal second pass for every raw question and substantially increases model usage. Compare explicitly frozen policies and report them separately. The no-recount inventory baseline is not the default product's full automatic pipeline.

The client guard stops scheduling when its observed calls plus conservative in-flight reservations reach the requested allowance. **The backend's atomic persisted attempt cap is the hard limit.** Failed HTTP requests can conceal one or more provider attempts and token usage; they are reported as unknown, never as free. There are no automatic inference retries. Authentication/configuration failures stop immediately; three consecutive failures stop the run. Already-running requests can finish after a stop signal.

Raw JSONL checkpoints and `.meta.json` are private evaluation artifacts. Resume with the same command plus `--resume`; completed successes and errors are not requested again. Model, provider, declared code, manifest, source, normalizer and analysis-policy mismatches are rejected. Provider, inventory and solver signatures are also pinned when reported by `/api/health`. Do not change the running backend's code or configuration during a run. The declared commit must actually match the server; an older server lacking signatures needs a new output whenever image resolution, crops or other provider settings change. A leftover `.lock` after a crash requires checking that the old process has stopped before removing only that lock. Malformed or duplicate checkpoint rows are rejected rather than silently discarded.

The summary includes all raw questions, a separate unique normalized analysis with a fixed preference for English, per-category/language/source/type aggregates, errors, unrun cases, latency, tokens, cache hits and observed model calls. Use `all_selected.usage` for the run's actual usage: unique representatives can omit initial inventory calls made for translated copies. Unrun questions stay in the full denominator. Translations are not independent test drawings. Reference boxes are absent from this manifest, so coordinate validation cannot establish detection precision, recall or correct highlighting. The `.md` companion is a readable summary. Do not commit raw gold-bearing manifests or per-case output as an aggregate-only report.

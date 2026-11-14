# Gemini and optional Gemma review

Trace keeps native source extraction, deterministic calculations, coordinate mapping and review history when the hosted model changes. The following is a prepared analysis policy, not a claim that this configuration is deployed or that an evaluation has passed:

```dotenv
GEMINI_API_KEY=your-private-key
STOA_PROVIDER=gemini
STOA_MODEL=gemini-4-argon
STOA_GEMINI_IMAGE_RESOLUTION=ultra_high
STOA_GEMINI_THINKING_LEVEL=high
STOA_SMALL_IMAGE_CROPS=1
STOA_INVENTORY_READINGS=2
# Leave STOA_GEMINI_MAX_OUTPUT_TOKENS unset; the inventory caller uses 65536.
STOA_GEMINI_TIMEOUT_SECONDS=600
STOA_MAX_MODEL_CALLS=50
```

Store these in a private `.env`, exported environment, or `~/.config/stoa-junction-2026/gemini.env` with owner-only permissions. Keep the actual key out of chat, Git, browser JavaScript and screenshots. An empty sidecar does not activate Gemini. Exported variables take precedence. `STOA_PROVIDER=openai` explicitly selects the other supported provider.

Restart with `python ops/start_local.py`. `/api/health` reports the selected provider/model, key presence and non-secret analysis signatures. Key presence and model-catalog visibility do not prove successful inference. Check the key without inference using `python ops/check_gemini.py`, then run a real structured image request before describing the integration as live-tested. The actual production revision and verification belong in `docs/delivery/deployment-verification.md`; local checks do not update that deployment automatically.

## Analysis policy

| Setting | Supported values and behavior |
| --- | --- |
| `STOA_GEMINI_IMAGE_RESOLUTION` | `low`, `medium`, `high`, `ultra_high` (default); applied to each inline image. On CubiCasa dev plans ultra_high was level with or slightly above high (309 vs 306 of 355; 464 vs 460 of 524). |
| `STOA_GEMINI_THINKING_LEVEL` | `low`, `medium`, `high`; default `high`. The current Argon example uses the published `high` default. |
| `STOA_GEMINI_MAX_OUTPUT_TOKENS` | Optional integer 1,000–32,768. When unset, each analysis caller keeps its own cap. Leave it unset to preserve the current inventory caller cap of 65,536; setting an explicit override limits that caller. |
| `STOA_GEMINI_TIMEOUT_SECONDS` | Integer 60–600; default 600, because 16 of 482 inventory readings hit the former 240-second limit in the end-to-end run. This is a transport timeout, not a latency promise. |
| `STOA_SMALL_IMAGE_CROPS` | `1` enables enlarged overlapping crops for small plans. Upscaling does not restore missing detail; compare policies on development inputs. |

Google counts reasoning tokens inside the output-token cap. An analysis can therefore return `incomplete` before producing valid JSON. Increasing the cap alone is not an accuracy fix; reducing reasoning depth can prevent it consuming the whole response budget. Bounded text requests below 1,000 output tokens retain their original cap and use low Gemini reasoning. Invalid settings fail before another model-attempt reservation or network call. Inference is not automatically retried.

Resolution, reasoning, output cap and timeout are part of model-dependent cache identities. Equivalent questions covered by the deterministic translation normalizer can share analysis while retaining their original wording and fresh answer/review IDs. Unrecognized wording is not collapsed into a template.

## Optional Gemma review

Use the same private Google key to select a supported second model for visual count review:

```dotenv
STOA_VISUAL_AUDIT_MODEL=gemma-4-31b-it
STOA_GEMMA_THINKING_LEVEL=minimal
```

The other supported Gemma model is `gemma-4-26b-a4b-it`. Gemma accepts `minimal` or `high`; its analysis default remains `high` when the setting is omitted. Bounded Gemma text uses `minimal`. With no explicit auditor, the application uses the active initial model again. Model selection is local to each request, so concurrent calls do not change a global model or cross provider credentials.

Visual rechecks are **off by default**. Enable **Recheck visual counts** or set `verify_visual: true` for a particular API question. They can change or withhold counts and have not established a general accuracy improvement. Visual audit revision v4 constrains Gemma's image indices and normalized coordinates, then applies the same source-page mapping, category, crop-containment and scope checks as other visual results. The review can propose missed objects and reject candidates. A second model is not independent ground truth, and its output remains provisional. Changing the auditor invalidates audited answers while allowing unchanged initial-model inventories to be reused. Hosted Gemma is an API service here, not offline inference; no Gemma weights are bundled or trained by this integration.

## Per-message and session inference cost

The interface shows a cost estimate for each question and a running total for the current browser-tab session. Its UUID is kept in `sessionStorage`, so ordinary reloads retain the session; a new tab can have a different session. The backend persists request and response events, and `GET /api/usage?session_id=<uuid>` returns a revisioned aggregate and per-message breakdown. Native and cached questions record zero new model calls; a previously paid inventory is not charged again in every follow-up answer.

These are estimated provider token costs **before credits**, not invoices or an account balance. Hosting and storage are separate. Reasoning output tokens count toward inference cost. Each model is priced separately when Gemini and Gemma share a question. Failed or incomplete responses retain any usage the provider reported. A network failure or missing usage remains unknown; a known subtotal is shown separately from an unknown total. Closing the browser request or stopping waiting does not cancel work already running on the server.

`server/costs.py` contains published rates verified on 14 November 2026, valid for calls before 1 December 2026:

- Gemini 4 Carbon: $2.00 per million uncached input tokens, $0.10 per million cached input tokens and $10.00 per million output tokens, including reasoning.
- Hosted Gemma 4: the documented free-tier token rates. A zero estimate is not a guarantee about account access, quotas or an invoice.

Calls outside the dated rate window, unknown models and missing usage do not receive invented prices. An operator can explicitly override rates for one exact provider/model with `STOA_PRICE_MODEL`, `STOA_INPUT_USD_PER_MILLION`, `STOA_CACHED_INPUT_USD_PER_MILLION` and `STOA_OUTPUT_USD_PER_MILLION`. Wrong-model or invalid overrides do not silently price another model's tokens.

## Existing deployment and evaluation

`python ops/deploy_verda.py sync` transfers only the selected runtime provider key over encrypted SSH stdin. `start` rebuilds and restarts the existing app. Preserve SQLite, source files, saved answers, reviews and the model-attempt ledger. `STOA_MAX_MODEL_CALLS` is a per-runtime attempt ceiling, separate from credits and provider rate limits. An explicit larger evaluation budget must not reset that ledger or remove its history.

For development-scale runs use [bulk evaluation](BULK_EVALUATION.md). Freeze the code, model, prompts and analysis policy first. Reports must distinguish an inventory baseline with per-question recount disabled from the audited product flow. Count abstentions on answerable questions as failures and keep unsupported controls separate. Release reserved inputs only under their evaluation protocol; do not repeatedly tune against them. Model selection and request-volume success do not establish 99.9% accuracy.

## Official references

Checked 14 November 2026:

- [Gemini 4 Carbon](https://aistudio.google.com/docs/models/gemini-4-carbon); the default is now gemini-4-argon, which beat gemini-4-hydrogen on CubiCasa dev plans (314 vs 306 of 355) while carbon matched hydrogen and was several times slower.
- [Structured output](https://aistudio.google.com/docs/structured-output) and [image understanding](https://aistudio.google.com/docs/image-understanding)
- [Media resolution](https://aistudio.google.com/docs/media-resolution#token-counts) and [reasoning token limits](https://aistudio.google.com/docs/thinking#token-limits)
- [Hosted Gemma](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)
- [Published API pricing](https://aistudio.google.com/docs/pricing)

The adapter uses Google's Interactions API with `store: false`. That flag does not override provider data-use or retention terms.

# Gemini provider setup

The hosted model is replaceable; native source extraction, calculations, coordinate mapping and review history remain in Trace. Select Gemini with private settings:

```dotenv
GEMINI_API_KEY=your-private-key
STOA_PROVIDER=gemini
STOA_MODEL=gemini-4-carbon
STOA_MAX_MODEL_CALLS=50
```

Store these in a private `.env`, exported environment, or `~/.config/stoa-junction-2026/gemini.env` with owner-only file permissions. Never put the key in chat, source control, browser JavaScript or a screenshot. An empty sidecar does not activate Gemini. Exported variables take precedence. `STOA_PROVIDER=openai` explicitly selects the existing provider.

Restart with `python ops/start_local.py`. `/api/health` reports the provider, model and whether a key is present; key presence alone does not establish successful authentication or model access. A read-only model availability check and a real structured image request are required before calling the integration live-tested.

For the existing Verda deployment, `python ops/deploy_verda.py sync` transfers only the selected runtime provider key over encrypted SSH stdin. `start` rebuilds and restarts the app. The existing SQLite database, saved answers, review history and total model-attempt ledger are preserved. The request cap is an application setting, separate from credits, billing and provider rate limits. Do not reset the ledger to conceal failed attempts.

Provider and model identity are part of answer and inventory cache keys. Output usage includes Gemini reasoning tokens. Dollar estimates remain unknown until the configured model's rates are supplied. Provider failures are sanitized; automatic inference retries are disabled.

Cost estimates additionally require `STOA_PRICE_MODEL=gemini/gemini-4-carbon` to match the active provider/model exactly. This prevents old OpenAI prices from being applied after a provider switch. Obtain current rates from the provider before setting the three `STOA_*_USD_PER_MILLION` values.

Current Google documentation, checked 14 November 2026:

- [Gemini 4 Carbon](https://aistudio.google.com/docs/models/gemini-4-carbon), text/image/PDF input and structured output.
- [Structured output](https://aistudio.google.com/docs/structured-output) and [image understanding](https://aistudio.google.com/docs/image-understanding).
- The adapter uses Google's Interactions API with `store: false`. Account access must still be checked with the actual key.

Before comparing providers, freeze the code, prompts, model and analysis settings, run development questions first, and then release the reserved unseen-file evaluation once. Count abstentions on answerable questions as failures; report unsupported controls separately. A model change is not evidence of 99.9% accuracy.

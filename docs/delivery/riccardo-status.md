# Riccardo delivery status

14 November 2026. Trace is the single application. Product quality and unknown uploads take priority over preparing or sending a scoreboard.

| Assigned work | Status and evidence |
| --- | --- |
| Integrate teammate changes | Native normalizer and visual inventory integrated, with filename-independent scope, constraint checks and provider-aware caches. Team deletion of the separate prototype retained. |
| Baseline and evaluation | Full pre-freeze native baseline recorded. Latest completed 7,066-question development run: 2,929/6,801 numeric correct, 3,026 answered, no old-correct regressions, zero errors/model calls. Six-format visual development run: six exact door counts, 12 real model calls. Summaries under `stoa-trace/ops/reports/riccardo-delivery/`. No team message sent. |
| Freeze about 15% of groups | 48 of 317 preview groups reserved prospectively, 924 questions. Already exposed preview data is explicitly distinguished from the separate frozen unseen-file corpus. |
| Stoa and licence questions | Questions prepared in `sponsor-questions.md`; no response invented, no message sent. Requires an actual organizer/sponsor conversation. |
| Existing Verda deployment | Existing VM and database retained. See `deployment-verification.md` for the last actual deployment. Scheduled merge checks are configured. |
| Batch answers | `stoa-trace/ops/batch_answers.py` accepts label-free JSONL/CSV requests, uploads unmatched files and writes evidence-bearing answers. Native default; model requests require explicit opt-in and obey the runtime cap. |
| Demo and submission | Script, runbook and form draft prepared. No encoded two-minute video or final submission is claimed. User redirected work to product quality. |
| Unknown files and Gemini | New raster formats, explicit calibration, dimension calculations, visual recount and a selectable Gemini adapter. Gemini is live on the existing VM, with a successful production image request, cached follow-up and session-cost verification. Medium reasoning and a larger output budget prevent the initial high-reasoning truncation failure. Visual rechecks are optional pending measured benefit. Full development and independent-file results are recorded in the Gemini release reports when complete. |

The quality target is 99.9% on questions supported by the input. Abstentions on answerable questions are failures. This target has not been achieved or established by the current tests. Reserved reference values never enter application prompts, extraction, caches or normalizer tables.

The user requested committing and pushing the current changes, then waiting and staying within Riccardo's assigned work. Competitor monitoring is paused. Scheduled deployment tasks remain within the existing Riccardo assignment. No further unsolicited product or competitor work should start after this delivery.

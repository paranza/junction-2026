# Riccardo delivery status

14 November 2026. Trace is the single application. Product quality and unknown uploads take priority over preparing or sending a scoreboard.

| Assigned work | Status and evidence |
| --- | --- |
| Integrate teammate changes | Native normalizer and visual inventory integrated, with filename-independent scope, constraint checks and provider-aware caches. Team deletion of the separate prototype retained. |
| Baseline and evaluation | Full pre-freeze native baseline recorded. Saturday 13:00 gate: 3,234/6,801 numeric correct across the same 7,066 development questions, 3,237 answered, all prior 2,929 correct retained, zero source changes/errors/model calls. Six-format visual development run: six exact door counts, 12 real model calls. Summaries under `stoa-trace/ops/reports/riccardo-delivery/`. No team message sent. |
| Freeze about 15% of groups | 48 of 317 preview groups reserved prospectively, 924 questions. Already exposed preview data is explicitly distinguished from the separate frozen unseen-file corpus. |
| Stoa and licence questions | Questions prepared in `sponsor-questions.md`; no response invented, no message sent. Requires an actual organizer/sponsor conversation. |
| Existing Verda deployment | Saturday 13:00 deployment completed at 13:06 Europe/Helsinki from reviewed main `8d4b822`. 301 backend and 34 frontend tests/build passed; protected API, preview, review/export and restart verified. All prior answers/uploads/event history retained, model ledger unchanged at 17/1,000. See `deployment-verification.md` and `stoa-trace/ops/reports/saturday-1300/`. |
| Batch answers | `stoa-trace/ops/batch_answers.py` accepts label-free JSONL/CSV requests, uploads unmatched files and writes evidence-bearing answers. Native default; model requests require explicit opt-in and obey the runtime cap. |
| Cloudinary evidence inspection | User-authorized free workspace created; actual authenticated source-region crop and protected delivery verified. Original answers and coordinates retained, zero additional model calls. Separate award form remains unsubmitted; owner claim flow pending. |
| Demo and submission | Script, runbook and form draft prepared. No encoded two-minute video or final submission is claimed. User redirected work to product quality. |
| Unknown files and Gemini | New raster formats, explicit calibration, dimension calculations, visual recount and a selectable Gemini adapter. Gemini is live on the existing VM, with a successful production image request, cached follow-up and session-cost verification. Medium reasoning and a larger output budget prevent the initial high-reasoning truncation failure. Visual rechecks are optional pending measured benefit. The full Gemini CubiCasa development run completed at 2,760/3,534 exact answers (78.1%), zero request errors, 198 inventory calls. Frozen independent uploads scored 18/20 answerable numeric questions, plus three successful missing-information controls. Neither result establishes 99.9% accuracy. Reports are under `stoa-trace/ops/reports/gemini-release/`. |

The quality target is 99.9% on questions supported by the input. Abstentions on answerable questions are failures. This target has not been achieved or established by the current tests. Reserved reference values never enter application prompts, extraction, caches or normalizer tables.

The user requested committing and pushing the current changes, then waiting and staying within Riccardo's assigned work. Competitor monitoring is paused. Scheduled deployment tasks remain within the existing Riccardo assignment. No further unsolicited product or competitor work should start after this delivery.

## Local chat-history recovery, 14 November

The workspace client now uses `/api/workspace/chats` and `/api/workspace/projects`; existing API paths remain compatible. Refresh reads existing threads without creating new ones. A local metadata index preserves previously loaded navigation during temporary connection failures. History recovery no longer blocks other pages. Explicit preview cache policies remain intact; mutable JSON defaults to `no-store`.

Removed the two large sidebar upload/new-chat controls. New conversations use the small Chats heading control; attachment remains available in the composer and empty drawing view.

Verification: 326 Python tests, 41 frontend tests and the production frontend build passed. The live local service returned the existing one project and three threads. An in-app browser control tab restored the saved drawing conversation after refresh and local server restart, with no console errors. The user's older tab could not be claimed by the browser controller, so its reported failure was not reproduced or directly verified. The original cause of that tab's failed request remains unconfirmed. No model requests, data resets or production deployment were performed.

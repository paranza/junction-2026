# Chat, UI and selected-region recovery

14 November 2026. Local application changes only. No Verda deployment or Junction submission was performed.

## Root cause and persistence

Two local Python backends were serving the same frontend build. The process on port 8798 still had older application code loaded: new chat and usage routes returned HTTP 404, although the updated frontend was visible. Earlier successful checks against port 8791 did not verify that process. Both local processes now run the updated code. Their distinct runtimes, existing provider policies, credentials, uploads, answers, reviews and cumulative model counters were preserved. They were backed up through SQLite's backup API before restart.

The 8791 workspace retains Gemini Argon and its existing policy. The 8798 workspace retains Gemini Carbon and its existing policy. These are separate local workspaces; neither is the production VM. The verification JSON records each workspace's actual model and counter rather than presenting one as the other.

Attachment selection is now resolved transactionally on the server. Stale client indexes no longer decide which chat to overwrite. Retries reuse identities, including project creation through the compatibility API. Successful mutations update the client from their returned saved record, without depending on a second history request. Network failures, timeouts, HTTP errors and non-JSON responses are distinguishable. A corrupted local index cannot crash navigation.

## Current interface

- Chats has a nearby plus button and its existing threads nested directly below. Projects, Recent and Settings are absent from navigation. Existing project metadata is retained through the compatibility API.
- Removed the duplicate top bar, coordinate HUD, zoom footer, upload licence strip, repeated filename/value summaries and the composer's scope selector.
- A chat without a drawing has no right-hand conversation pane. Cached drawing loads no longer get stuck behind the loading overlay.
- The drawing toolbar contains pan, region selection and evidence visibility. Region selection and evidence overlays remain functional.
- BoardUI's free MIT Agent Thinking dot-grid implementation follows real pending requests, with no elapsed timer or simulated steps. Reduced-motion preferences are respected. No Pro source is included.
- Evidence uses a controlled, accessible disclosure. Source selection opens it deliberately; ordinary renders do not reopen a closed panel. Count review remains available inside the evidence panel.
- Automatic evidence focus preserves surrounding context and is capped using preview resolution and device pixel density. It no longer magnifies a tiny door up to eight times.
- Clicking free drawing space, pressing Escape or clicking the selected object again clears its selection and popup. Hovering a shape does not open a persistent popup. Direct SVG clicks are separated from the canvas pan gesture.
- Spending reads recorded attempts and token usage across chats. Earlier reservations without correlation IDs are counted, while their unrecorded token usage and costs remain unknown. Known costs are labelled as tracked cost, with pricing coverage shown explicitly.

## General question handling and region geometry

Native CAD area comparisons now support maximum and minimum over resolved source quantities. Unknown wording can also use a model-planned native query: Gemini selects object types, exact source property paths, filters and a count/value/sum/min/max/mean aggregate; Python executes the query over the source records. The model does not supply the answer number. Unknown fields, missing operands, invalid IDs and unsupported filters are refused. Plans and results are cached with source and provider signatures.

Standalone DXF previews and overlays now share the renderer's actual WCS-to-page placement matrix. Registration was checked against the generated PDF's vector vertices, including its fitted page layout. Independent raster companions and degenerate PDF fits do not receive assumed registration.

Registered native room queries can be restricted to a selected page region before interpretation and calculation. Membership uses a room's registered label anchor when available, otherwise its bounding-box center. The region restricts rooms; it does not turn this query into a calculation of the clipped selection rectangle's area.

## Verification

- 338 Python tests, 54 frontend tests and the production frontend build passed.
- All 7,066 development cases were compared with the previous run: 3,234/6,801 numeric questions correct, zero changed outcomes, zero previously correct regressions, zero request errors and zero model calls. These are native-mode development results, not a new visual accuracy estimate. The reserved set and independent released evaluation were not rerun.
- The user's uploaded DXF returned 20.28 m² for the largest labelled room, 1.01, using native data without model requests.
- The user's exact selected rectangle and question returned 19.06 m² for room 1.49, with a registered polygon inside that selection.
- Live model-planned paraphrases returned the native maximum, the count of rooms above a natural-language threshold and the mean area of rooms named Cuisine. Four actual planning requests were made, one per question, in the Carbon workspace. These procedural checks are not an independent accuracy sample.
- Browser checks covered new chat, persisted drawing restoration, a real upload and native answer, nested navigation, usage periods/refresh, evidence opening and closing, reduced automatic focus and popup dismissal. The image-cache loading race was reproduced and corrected.
- All answers and event rows present at the final restart remained byte-for-byte identical. New answers, usage events and one empty chat were added during verification; no saved data was deleted.

Arbitrary questions, all drawing formats and 99.9% accuracy are not established by these checks. The typed query language has explicit limits; missing source measurements, unresolved spatial relationships, image interpretation and model-selected semantics remain possible failure points.

[Machine-readable verification](../../stoa-trace/ops/reports/chat-region-recovery/verification.json). Raw development labels and case-level reports remain local and ignored.

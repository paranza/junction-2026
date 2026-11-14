# Trace: Cloudinary entry draft

**Status checked 14 November 2026, approximately 12:25 Europe/Helsinki:** prepared text only. No Cloudinary award form or Junction challenge selection has been submitted by this work. The close-up interface is implemented at `6405c97`; backend integration and live end-to-end verification are pending at this draft's cutoff. Use the submission copy below only after the acceptance checks pass and its revision and demo links are filled in accurately.

## Checked challenge requirements

The authenticated [Cloudinary technical challenge brief](https://hackjunction.app/participate/45/tech-challenges/41), read on 14 November, requires a meaningful Cloudinary contribution beyond ordinary CDN delivery and use of at least one of its listed development tools. Trace uses the **official Cloudinary Skills Pack**, rather than migrating its working React/Vite application to a new starter. The pack is [cloudinary-devs/skills](https://github.com/cloudinary-devs/skills), checked at commit `c41e79f4b5e350fb994c541f6190538e838660b8`; upload and transformation guidance inform the protected source-region workflow.

The brief also requires a separate [Cloudinary hackathon survey](https://cld.media/hackathon-survey). Preparing this document does not satisfy that submission requirement. The observed judging weights are **30% innovation, 20% technical execution, 30% user experience and 20% impact**. The listed reward is a **USD 500 Amazon gift card per winning team member**, separate from cash prizes. The sponsor determines qualification and winners; using the Skills Pack or creating a workspace alone does not establish either.

## Proposed submission copy

### Project and problem

**Trace, by MUSTA HELMI.** Construction engineers need to inspect the source behind a quantity, especially when an AI count may contain a missed door or an extra window. A number in a chat response is difficult to verify against a dense plan.

### Cloudinary's contribution

Trace connects each located answer candidate to an evidence close-up. The engineer selects a candidate on the original drawing and explicitly opens its close-up. The server renders the source page, stores that rendered page as authenticated Cloudinary media, and asks Cloudinary to crop the selected coordinates with a small amount of surrounding context and enlarge the result. A protected application endpoint returns the image to the same answer inspector.

This is a source inspection feature driven by the drawing's evidence coordinates. It makes the engineer's selected object easier to inspect without losing its page and answer context. Cloudinary performs the image transformation; the existing drawing viewer, model recognition and quantity calculations remain responsible for their original roles. The feature adds neither a generated object nor an answer inferred from Cloudinary output. Ordinary enlargement does not recover detail absent from the source image.

### How we built it

We used the official Cloudinary Skills Pack's upload and transformation guidance to design authenticated source assets, explicit coordinate crops, eager derived images and server-side signing. The existing FastAPI backend keeps credentials and signed Cloudinary delivery URLs away from browser JavaScript. The frontend requests the selected evidence item's close-up through the application, receives a protected image route and opens an accessible dialog. The canonical source and saved answer remain unchanged. Repeated close-ups reuse the cached page or derived image where available.

The AI part of Trace is the source-grounded recognition and answer pipeline. Cloudinary contributes the subsequent visual verification step, rather than serving as a new detector or a substitute for the original drawing. A failed close-up leaves the source viewer available for inspection.

### Relation to the Stoa challenge

Stoa assigns a quarter of its score to visualization that enables human verification. Trace's close-up action supports that same engineer workflow: ask a quantity question, inspect numbered evidence, open the selected source region and correct a candidate when necessary. We will demonstrate the working request, returned close-up and retained original evidence, rather than claim an accuracy improvement from image resizing.

## Demonstration to record after live verification

1. Open a verified development drawing and a saved door or window answer. Identify a cached replay accurately.
2. Select one evidence item and show its location in the canonical drawing.
3. Click **Open evidence close-up** and show the actual Cloudinary-generated crop, its source page and label.
4. Close the dialog and show that the source, count, evidence coordinates and review state are retained.
5. Repeat the same action and verify the cache path without implying a new recognition or model request.

Do not use an invented missed object as a real recognition success. This feature can assist review, but it does not establish that every object has been detected or that the quantity is correct.

## Verification record to complete

| Item | Current evidence or remaining action |
| --- | --- |
| Tool used | Official Cloudinary Skills Pack, upstream commit above. No framework migration. |
| Frontend | Implemented at `6405c97`; a completed frontend build is separate from a successful Cloudinary request. |
| Backend and upload preset | Integration in progress. Record final code revision and successful authenticated preset check. |
| Live transformation | Pending. Record a real selected-evidence crop, returned dimensions and source alignment. A mock test is insufficient. |
| Protected delivery | Pending live check that the browser receives the workspace route, and unauthenticated users cannot retrieve the image. Keep signed URLs and credentials out of screenshots and reports. |
| Source and quantity preservation | Pending end-to-end check that opening a close-up changes no source, evidence coordinates, count or saved review. |
| Cache and failure behavior | Pending live cache check; record missing-configuration, invalid-evidence and provider-failure tests separately. |
| Demo | Existing protected workspace: `https://stoa-86-38-182-146.sslip.io`. Deployment of this feature and organizer access are unverified at this cutoff. |
| Source | `https://github.com/paranza/junction-2026`. Confirm the final integrated revision and organizer access before submitting. |
| Video or screenshot evidence | Pending final live proof. Use source images whose terms permit the demonstration. |
| Separate survey and challenge selection | Not submitted by this work. Save actual confirmation privately after an authorized submission. |

## Workspace handoff

A new free claimable Cloudinary workspace was provisioned with the user's authorization. Its claim deadline is **15 November 2026, 10:20:57 UTC (12:20:57 Europe/Helsinki)**. The user must complete the private browser claim flow, including email and acceptance of terms, to retain the workspace. The claim URL is a private capability and is intentionally absent from this repository. Obtain it through the owner's existing private handoff, not a public issue or submission description.

Keep API credentials in private server configuration. The free workspace's quotas and future terms remain separate from Gemini credits and from the application's LLM inference-cost estimate. Creating the workspace is not an award entry, a paid-plan authorization or proof that the feature has been deployed.

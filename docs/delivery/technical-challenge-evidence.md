# Metria technical challenge evidence

Checked 15 November 2026 against the authenticated Junction briefs and the
current application. This is a submission preparation record, not a saved
challenge selection, submitted form or sponsor eligibility decision.

## Gemini: core application capability

[Best Use of Gemini API](https://hackjunction.app/participate/45/tech-challenges/48)
asks for meaningful, innovative and technically impressive use, with an
explanation of the problem, integration and why Gemini matters.

Metria uses Gemini as a source-inspection agent for construction drawings. It
selects original-resolution views, locates individual objects, reads source
annotations and requests bounded OCR/calibration/geometry tools. Python checks
units and executes expressions over located source operands instead of trusting
the model's asserted arithmetic. Saved evidence supports review, corrections
and exports. Provider usage and each actual HTTP attempt are recorded, including
bounded continuation requests. Native extraction can answer supported structured
questions without a model request.

Submission wording: **Metria turns a blueprint question into a source inspection
and a checked quantity. Gemini chooses what to inspect and which local tools to
use; the engineer can inspect the returned locations and calculation.**

Demonstrate a real uploaded complex drawing, an original-resolution detail, a
quantity with evidence, and the actual request/cost record. Report failures and
latency alongside successful checks. The newly tested Discord examples include
unanswered quantities and count omissions; the older 17 correct development
checks are not a claim that all sponsor questions work. We did not fine-tune
Gemini. Model outputs and geometric interpretation remain fallible.

## Cloudinary: evidence inspection

[Best Use of Cloudinary](https://hackjunction.app/participate/45/tech-challenges/41)
and the [official hackathon page](https://cloudinary.com/pages/hackathons/)
require substantive media use and one of the listed development tools. The
Skills Pack remains an accepted tool for an existing application. Entry also
requires the separate [survey](https://cld.media/hackathon-survey).

Metria uploads a rendered source page as authenticated Cloudinary media only
when an engineer requests an evidence close-up. Source coordinates select a
contextual crop; Cloudinary performs the image transformation and enlargement.
The backend signs delivery, protects the local image route and caches repeated
close-ups. Browser code receives neither credentials nor the signed delivery
capability. The original source, answer, evidence coordinates and review remain
unchanged. This is more than static CDN hosting, but it does not detect objects,
recover absent detail or improve the answer's numeric accuracy.

The official [Cloudinary Skills Pack](https://github.com/cloudinary-devs/skills),
previously checked at `c41e79f4b5e350fb994c541f6190538e838660b8`, informed the
upload/transformation implementation. See [the original entry draft and live
proof](cloudinary-entry-draft.md).

Current UI verification found a regression: the global outside-click handler
cleared the selected evidence before its close-up button could run. The fix
keeps evidence-detail/dialog interactions selected while retaining outside
selection dismissal. An isolated browser check displayed an actual 396 by 284
Cloudinary crop from a saved source item, with unchanged answer rows and zero
extra model calls. This is real provider output, not a mock or a generated
replacement for the drawing. The release record must identify when the fix is
loaded by the main app.

Submission wording: **Cloudinary turns each selected evidence item into a
protected, coordinate-driven source close-up, helping engineers inspect the
object behind an AI quantity without losing its answer context.**

Show the Evidence artifact, select a source object, open its close-up and return
to the unchanged answer. The separate survey has not been submitted by this
work. Workspace ownership/claim completion was not reverified in this check.

## Verda: deployed agentic application and GPU experiment

The current [Verda Compute Track](https://hackjunction.app/participate/45/tech-challenges/56)
explicitly lists CPU instances for hosting agentic applications, GPU instances
for training and inference/batch services. Its minimum requirements now shown
are to document the process and submit through Junction Platform. This checked
brief does not list a Discord process post as a minimum requirement. Earlier
research that described such a requirement must not be treated as current.

The live application runs on the existing protected Verda CPU VM. FastAPI,
native parsers, local source tools, SQLite persistence and the React frontend
run there. Google hosts Gemini inference; the Verda VM does not run Gemini's
weights. The deployment retains uploads, answers, reviews, credentials and the
cumulative 1,000-attempt ceiling, with build-before-replacement, SQLite backups,
retained Docker images and restart verification.

A separate completed research experiment used a Verda V100 to fine-tune
pretrained YOLO11s on 1,024 external CubiCasa training drawings, with 128
validation drawings and a separate 32-drawing confirmation. Training used
1,280-pixel RGB inputs, batch 8 and 130 epochs. The GPU and its disk were removed
after artifact retrieval; no new GPU is needed for the deployed app.

The detector-guided pipeline scored 29/64 exact confirmation counts versus
28/64 for the Gemini baseline, with two gains and one regression. It failed
its promotion gate and remains disabled. Present it as a substantive documented
compute experiment, not a production accuracy improvement. See [training,
comparison, notices and cleanup](../evaluation/specialist-fine-tuning.md).

Submission wording: **Verda hosts our persistent blueprint-inspection agent and
supported a GPU experiment adapting a pretrained drawing-symbol detector. We
measured the result, rejected an insufficient improvement and retained the
more reliable application path.**

The brief weighs ambition, service fit, working prototype and path to scale at
25% each. Hosting is a real integration, but hosting alone is a weaker story
against the challenge's serious-compute ambition. Include the training evidence,
working endpoint and credible scaling explanation. Do not claim GPU inference
is active, sensitive drawings remain entirely in Europe, or that Gemini runs
on Verda.

## Entry checklist

- Confirm intended challenge selections in Junction Platform.
- Supply organizer access to the working demo without publishing secrets.
- Explain each sponsor's actual contribution in the description/video.
- Submit Cloudinary's separate survey and retain its confirmation privately.
- Use measured, scoped outcomes rather than general accuracy or prize promises.

No platform submission, survey submission, Discord post or teammate message was
made during these checks. Gemini prizes are cash plus the separately listed
credits; Cloudinary lists Amazon gift cards; Verda lists cloud credits and
hoodies. These reward types are not interchangeable or guaranteed cumulative.

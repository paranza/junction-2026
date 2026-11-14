# Unknown-upload checks and current limits

14 November 2026. Trace processes source files and question wording; there is no file-to-answer lookup or reserved-label path in inference. The deterministic normalizer maps question wording with variable labels and identifiers. Recognized native exporters still have specialized parsing, which does not establish performance on every exporter or image.

## Actual live upload checks

Four hosted requests were run against the existing protected Verda app at code `9486581`, before the later visual recount and Gemini integration:

| Input and question | Observed result | Reference |
| --- | --- | --- |
| Newly created labelled schematic PNG, doors | Four located door candidates | Four deliberately drawn assemblies |
| Same PNG, sum printed areas | 48 m², needs review | 10 + 12 + 10 + 16 m² |
| External simple-house drawing, doorways | Seven located candidates | Informal inspection of seven visible symbols |
| Same external drawing, floor area | No numerical answer | Missing scale or printed dimensions |

These are four spot checks, including one synthetic layout and one external style, not a 99.9% result or blind benchmark. The external source is [Simple house floor plan](https://commons.wikimedia.org/wiki/File:Simple_house_floor_plan.gif), public domain, Shamilton77. Exact file and raster hashes did not match the preview. Foundation-model pretraining overlap is unknown.

## Improvements implemented after those checks

- Shared upload-batch names preserve PDF/DXF pairing while keeping separate uploads isolated.
- GIF, WebP, BMP and multipage TIFF rendering, explicit first-frame warnings, pixel/file limits and content validation.
- Two quoted compatible dimensions can support a rectangular area; calculations and unit conversions are performed in code.
- User calibration binds an explicit known length and selected geometry to the actual page, aspect ratio and source fingerprint. Browser verification produced 48 m² and preserved the result after reload, with zero model calls.
- Visual counts use a second search against unannotated source images by default. It is a same-model check, not independent ground truth.
- Visual inventory scope comes from the question and selected pixels, never a filename or dataset directory. Mixed category counts retain component classes for review.
- Gemini can replace the hosted provider while retaining extraction, measurement and review behavior. No live Gemini success is claimed until key validation and inference succeed.

The [independent frozen corpus](../evaluation/unseen-generalization.md) separates development from reserved inputs, with labels outside the repository and inference. Its reserved split has not yet been released for scoring. The preview quarantine is a separate, prospective split. Report exact count accuracy and supported-question coverage, with unsupported controls separate; answered-only precision cannot substitute for those measures.

DWG still needs a paired supported export or a converter. General automatic polygon segmentation, every drawing convention and arbitrary question coverage remain incomplete. These gaps must be measured and improved; they are not hidden behind an accuracy claim.

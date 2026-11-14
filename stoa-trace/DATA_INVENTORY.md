# Metria dataset inventory

Verified on 14 November 2026 against the local files and the running `/api/documents` endpoint.

**All 913 drawing/model files in the preview are registered in the library.** This includes floor plans, elevations, sections, construction details, schedules, historic scans, CAD files, and BIM models. Extraction and page rendering happen when a document is opened or queried; registration does not mean every page has already been rendered or every question can be answered.

## Loaded dataset

- Source directory: `/Users/mazz/Downloads/junction-dataset-preview/data`.
- Drawing/model files: **913**, totaling **724,961,931 bytes** (about 725 MB).
- The separate advertised **10 GB full dataset is not loaded**. These counts describe the preview only.
- README, licence files, `questions.jsonl`, and `.Rhistory` are excluded from the document count.
- Files exported in several formats count separately. For example, the 65 Swiss floor drawings each have PDF, DXF, and PNG exports, accounting for 195 files. **913 files does not mean 913 distinct plans or buildings.** Multi-page PDFs also count as one file each.

| Format | Registered files | Preview and analysis support |
|---|---:|---|
| JPG | 374 | Image preview; visual analysis when a model is configured. No native semantic object inventory is assumed. |
| PNG | 306 | Image preview; visual analysis when configured. Includes CubiCasa images and rendered drawing exports. |
| PDF | 123 | Page previews, text/vector extraction, and supported schedules. Linked CAD/BIM can provide additional native evidence. |
| DXF | 66 | Native entities and supported semantic layers; paired PDF preview when present, otherwise DXF rendering. General CAD entities are not automatically complete semantic inventories. |
| DWG | 20 | Listed and original file accessible. Native DWG extraction/conversion is not implemented; preview requires a usable counterpart/export. |
| IFC | 14 | Native entities, properties, and supported quantity queries. Two-dimensional preview requires supplied linked views; there is no general 3D viewer. |
| SVG | 10 | Preview and supported vector extraction; IFC-generated views retain semantic classes and GUIDs. Arbitrary SVGs need not contain those semantics. |
| **Total** | **913** | Registered format support is broader than deterministic question-answering coverage. |

## Sources included

| Source folder | Files |
|---|---:|
| `cubicasa5k` | 241 |
| `swiss_dwellings` | 195 |
| `wikimedia` | 132 |
| `finna` | 96 |
| `habs` | 92 |
| `opening_design` | 81 |
| `europeana` | 61 |
| `ifc_models` | 10 |
| `ifc_bench` | 5 |

## Examples beyond floor plans

These files are present under the loaded source directory:

- Elevations: `opening_design/Crema_Cafe/Models/pdfs/A-101 - Elevations v2.pdf`.
- Wall sections: `opening_design/Sports_Complex/Sheets - Current Set/A-402 - Wall Sections.pdf`.
- Exterior-envelope details: `A-602 - Section Details - Exterior Envelope.pdf` and `A-603 - Section Details - Exterior Envelope.pdf` in that same current set.
- Foundation details: `opening_design/Sports_Complex/Sheets - Current Set/Sheet - S-300 - FOUNDATION DETAILS.pdf`.
- Door/finish schedules: `opening_design/Sports_Complex/Sheets - Current Set/A-801 - Door and Finish Schedules & Wall Types.pdf`.
- Schedules: `opening_design/CTR/Most Current Set/Full size sheets/A700 - SCHEDULES.pdf`.
- Plumbing BIM: `ifc_models/bsc-clinic_clinic-plumbing.ifc`.

The source tree also retains archived revisions. A similarly named sheet in an archive must not be assumed to be the current revision or an equivalent export.

## Loading and verification limits

The library scans supported files at startup. Document content is extracted and cached on demand; page images are rendered on demand. The library count is a file count, not a total page count or a completion indicator for preprocessing. Unsupported questions can abstain; visual candidates and derived quantities still require source review.

The preview's 7,990 example questions reference 320 file paths. Documents without example questions remain in the library. Evaluation labels belong to the benchmark and are not source facts supplied to answer generation. Preserve each source's credit and licence when displaying or sharing drawings, as specified in the dataset README and per-source `LICENSE.md` files.

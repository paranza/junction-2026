# Third-party notices

Team-authored Trace code is covered by `LICENSE` (MIT). Third-party datasets, source-derived questions/evidence, drawing imagery and dependencies retain their own licences. The MIT licence does not relicense those materials.

## Challenge dataset and diagnostic artifacts

The original Stoa preview dataset is downloaded separately. No original PDF/DXF/DWG/IFC/image asset collection, runtime database or extracted-document cache is bundled in this repository.

`ops/benchmark-config.json` contains a small frozen evaluation selection from the supplied questions. `ops/reports/` contains diagnostic answers, source facts and evidence derived from those files. These are evaluation artifacts, and their third-party contents retain the terms and credits of their source. Each report case identifies its source path, and answer records preserve source attribution. Gold labels must never enter inference, retrieval or training.

The unchanged source-provided licence and attribution notices for all nine collections are retained in `third_party/dataset_licenses/`. Consult the per-file tables when reusing or distributing material:

- **Swiss Dwellings v3.0.0:** Matthias Standfest, Michael Franzen, Yvonne Schroeder, Luis Gonzalez Medina, Yarilo Villanueva Hernandez, Jan Hendrik Buck, Yen-Ling Tan, Milena Niedzwiecka and Rachele Colmegna (Archilyse AG), [doi:10.5281/zenodo.7788422](https://doi.org/10.5281/zenodo.7788422), CC BY 4.0. The challenge drawings were rendered from published geometry with labels, numbering and styling added by the dataset preparers. The screenshot `frontend/qa/reviewed-history.jpg` includes such a drawing with Trace's evidence/review interface overlaid. That underlying drawing remains CC BY 4.0; no endorsement is implied.
- **CubiCasa5K:** Copyright 2019 CubiCasa; Kalervo, Ylioinas, Haikio, Karhu and Kannala, SCIA 2019. The source notice applies CC BY-NC-SA 4.0, including its questions. The relevant benchmark questions and source-derived portions retain those terms.
- **OpeningDesign:** credit OpeningDesign and the project team named in each drawing's title block. Sports Complex and most supplied projects use CC BY-SA 4.0; the source table identifies MIT exceptions. Source-derived portions of those examples retain their respective terms.
- **IFC models and IFC-Bench:** model-specific CC BY 4.0, CC BY-ND 3.0, MIT, KIT unrestricted-use and GPL terms are identified in the supplied notices. IFC-Bench questions are credited to Sylvain Hellin (2025), CC BY 4.0. Original model files are not distributed here.
- **Wikimedia, Finna, HABS and Europeana:** per-file licences and source credits are in the retained notices and in the separately downloaded dataset.

`server/question_templates.json` and the plan question routing in `server/inventory.py` hold sentence templates derived from the wording of the preview questions (no answers and no drawing labels). Those templates retain the terms of their source collections.

## Software dependencies

Dependencies are installed from their package registries and are not vendored into this source repository. Preserve their included notices when distributing an installed application or container. The pinned Python packages include FastAPI (MIT), Uvicorn (BSD-3-Clause), python-multipart (Apache-2.0), PyMuPDF (GNU AGPL 3.0 or an Artifex commercial licence), Pillow (MIT-CMU), ezdxf, IfcOpenShell (LGPL-3.0-or-later), Shapely (BSD-3-Clause), httpx (BSD-3-Clause) and python-dotenv (BSD-3-Clause). Consult the installed distributions for complete notices and transitive dependencies.

React, React DOM, Vite and their frontend dependencies retain their package licences. Lucide icons retain the licence included with `lucide-react`. No pretrained detection/segmentation weights are included.

## BoardUI interface primitives

`frontend/src/boardui/` adapts the free MIT-licensed Button and Divider components from [BoardUI](https://github.com/BoardUI/boardui), upstream commit `ec5c5eb3e29c2441be63b9422cd54f411ef23466`. Copyright (c) 2026 Mertcan Dundar Esmergul (BoardUI). The MIT licence is retained in `frontend/src/boardui/LICENSE`, and the adaptation is described in its README. No BoardUI Pro component source or paid template is included. Trace's session inference-cost section is original team code.

## Hosted model services and pricing facts

OpenAI, Gemini and optional Gemma requests use hosted APIs under their provider terms. Selecting a hosted open model does not turn this implementation into offline inference. No Gemini or Gemma weights are redistributed or trained by these adapters. `store: false` is an API setting, not a replacement for provider data-use or retention terms. See [Google's hosted Gemma documentation](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api).

The token-rate facts in `server/costs.py` are derived from [Google's published API pricing](https://aistudio.google.com/docs/pricing), checked 14 November 2026 and date-bounded in code. They support estimated provider token costs before credits, not invoices, account balances, or a promise of future pricing or access. Unknown or expired prices remain unknown unless an operator supplies an explicit exact-model override.

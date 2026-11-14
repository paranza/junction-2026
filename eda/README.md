# EDA scripts

Exploratory analysis of the Stoa preview dataset, run on 13 and 14 November 2026, and the checks behind the reading list in `docs/saturday-plan.md`. These scripts measured what each source needs. They are not part of Trace: port the rules into `stoa-trace/server/` (section 8 of the plan says where).

## Answer labels

Most scripts read the answers in `questions.jsonl` to score themselves. That is fine for analysis, but never port the label reading into Trace: answer labels must not reach extraction, prompts, indexes or training (see `stoa-trace/HANDOFF.md`). Port the rules only.

## Run

```sh
python3 -m venv .venv-eda
.venv-eda/bin/python -m pip install -r eda/requirements.txt
export STOA_DATA_ROOT=~/stoa-data/junction-dataset-preview   # folder with data/ and questions.jsonl (this is the default)
```

The scripts originally used absolute paths on one laptop. Those were replaced when the files were copied here: the dataset comes from `STOA_DATA_ROOT`, and other paths are relative to the repository. Scripts write their outputs (CSVs, renders, crops) next to themselves; `eda/.gitignore` keeps those out of Git because they are derived from the partner data.

Run each script from its own folder and read its header first: some take paths as arguments, and some need a CSV that an earlier script writes.

## Layout

| Folder | What it holds |
| --- | --- |
| `swiss_dwellings/` | PDF-only solver (`pdf_solver.py`), DXF experiments, evidence overlay |
| `ifc_models/` | IFC solver (`final_solver.py`, `final_eval.py`), SVG and PDF twins |
| `ifc_bench/` | Reproductions of the free-text IFC-Bench answers (`reproduce.py`, `sweep.py`) |
| `opening_design/` | Revit sheet schedules (`tables_auto.py`, `reproduce.py`), view locator |
| `cubicasa5k/` | Image properties, templates, priors and blind counting samples |
| `questions/` | Question-set analysis: languages, templates, translation twins |
| `scans/` | Historic scans: noise and legibility checks |
| `*/verify/` | Independent re-checks of each analysis |
| `results/` | The analysis reports (`explore__*.json`) and the independent checks (`verify__*.json`) |
| `research/` | Checks of the code snippets in the reading list (Gemini client and cache, tile merge, IFC, PDF, SVG and DXF snippets) |

## Not included

Dataset files, rendered images and crops, generated CSVs (they contain question text and answer labels), caches, logs, and downloaded third-party code and documentation.

## Licences

Team-written code is MIT, like the rest of the repository. PyMuPDF, which many scripts use, is AGPL-3.0: the same open question as for Trace. The dataset keeps its per-source terms; see `stoa-trace/THIRD_PARTY_NOTICES.md` and `stoa-trace/third_party/dataset_licenses/`.

# Blueprint Takeoff (Michele-testing)

Upload a floor plan (PNG, JPG, PDF or DXF). Our own PyTorch models find walls, rooms,
doors, windows and sanitary fixtures, read the printed room labels and areas, and the UI
shows every room as a clickable coloured polygon with its area in the middle. Ask
questions in English, German, French, Italian or Finnish; answers point at the drawing.
A material takeoff tab turns the geometry into what a crew orders (flooring, skirting,
paint, wet-room tiles).

Runs on a laptop CPU. No YOLO, no pretrained detector, no image sent to any API.

## Run

```sh
cd Michele-testing
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # Windows; use .venv/bin/python on macOS/Linux
cp .env.example .env                                         # add GEMINI_API_KEY (optional, only for free-form questions)
cd backend
../.venv/Scripts/python app.py                               # http://127.0.0.1:9999
```

Trained weights live in `backend/weights/` (`plannet_swiss.pt`, `plannet_cc.pt`, `glyphnet_swiss.pt`).
Without weights, DXF uploads still work (exact vector path).

Demo samples: put the Stoa preview next to the repo (`HACK-JUNCTION/preview_dataset`) or set
`STOA_DATA` in `.env`; the start screen then lists Swiss drawings to try.

## Train (CPU, a few hours total)

From `backend/`:

```sh
# 1. Swiss Dwellings: labels from DXF projected onto PNG (65 drawings, ~1 min)
python -m stoa.labels ../../../preview_dataset ../../../work/labels_swiss
THREADS=6 python -m train.train_plannet --labels ../../../work/labels_swiss --minutes 150
THREADS=4 python -m train.train_glyph   --labels ../../../work/labels_swiss --minutes 40

# 2. CubiCasa5K (download 5.5 GB from zenodo.org/records/2613548, unzip to HACK-JUNCTION/datasets)
python -m train.build_cubicasa --cc ../../../datasets/cubicasa5k --out ../../../work/labels_cc --exclude ../../../preview_dataset
THREADS=6 python -m train.train_plannet --dataset cc --labels ../../../work/labels_cc --out weights/plannet_cc.pt --minutes 180
```

`THREADS=6` matched the 6 performance cores of our laptop; more threads were slower.

## Evaluate

```sh
python tools/eval_dxf.py        # exact DXF path vs swiss questions
python tools/eval_raster.py     # PlanNet + GlyphNet on PNGs vs questions (holdout drawings only)
```

Results and their caveats: [docs/evaluation.md](docs/evaluation.md).

## Docs

- [Architecture and decisions](docs/architecture.md)
- [Models](docs/models.md)
- [Evaluation](docs/evaluation.md)
- [Publications and repositories](docs/references.md)
- [Overnight progress log](docs/PROGRESS.md)

## Data licences

Swiss Dwellings: CC BY 4.0 (credit Archilyse AG, doi:10.5281/zenodo.7788422).
CubiCasa5K: CC BY-NC 4.0, non-commercial only; weights trained on it inherit that restriction.
Datasets and trained label caches are not committed.

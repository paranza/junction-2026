# Architecture and decisions

## One sentence

Our own small PyTorch models turn a floor plan into a structured list of rooms,
walls and objects with coordinates; every number shown or answered is computed
from that list, and an LLM is only used to phrase answers to unusual questions.

## Flow

```
upload (PNG/JPG | PDF | DXF)
   │
   ├─ DXF ──► vector_dxf.parse_dxf ─────────────────────────────┐   exact, no ML
   ├─ PDF ──► render 150 dpi + text layer words ──► PlanNet ────┤
   └─ image ─► PlanNet (walls, rooms, edges, text, objects) ────┤
               GlyphNet reads every text blob ──────────────────┤
                                                                ▼
                         facts.json (rooms, polygons, areas, objects, units, scale)
                                  │                 │                 │
                     questions.answer()     takeoff.compute()   frontend overlays
                     (deterministic,        (floor, skirting,   (click a room or
                      multilingual)          paint, tiles)       object = evidence)
                                  │
                         no template matched
                                  ▼
                     llm.ask(): Gemini flash-lite over a compact text table of facts
```

## Decisions and why

| Decision | Why | Alternative rejected |
| --- | --- | --- |
| Train our own small models (PlanNet 2.9M params, GlyphNet ~1M) in plain PyTorch | Team requirement: no YOLO, no off-the-shelf detectors. Small models run on a laptop CPU in seconds, so inference cost is near zero. | YOLO / SAM 2 / hosted vision for every image: heavier, costs per call, and harder to explain. |
| Heatmap peaks for counting (CenterNet idea) | A count becomes a set of clickable points; the user can see each counted door. Exact counts are what the scoring needs. | Count regression: a number with no evidence. |
| Room = connected component of `room` minus `room_edge` and `wall` | Gives closed polygons for the UI and pixel areas, no box post-processing. | Instance segmentation heads: more parameters and training time on CPU. |
| Read the printed area, check it against geometry | Drawings print the official net area (e.g. `15.61 m²`). Reading it gives exact answers; the segmented polygon times the calibrated scale is an independent check, and the UI shows both. | Geometry only: always a few percent off because of wall lines and symbols. |
| Self-calibrating scale | Median ratio of printed area to pixel area over all rooms gives metres per pixel without trusting a scale bar or DPI. Falls back to 1:200 at 150 dpi. | Detecting and reading the scale bar: more fragile. |
| Labels generated from the Swiss DXF, not hand annotation | DXF geometry projected onto the PNG with a least-squares fit on room-number anchors (max error 0.34 px). Free pixel-perfect labels for 65 drawings. | Manual labelling: impossible overnight. |
| CubiCasa5K as a second training set | The preview's `cubicasa5k` images come from CubiCasa5K, which ships SVG annotations for ~5000 plans. Our SVG parser reproduces the question answers at 97 to 100 % per question type. Preview plans are held out as the test set. | Training only on 241 preview images with count labels. |
| Deterministic question templates before any LLM | Exact, free, repeatable, works offline, and multilingual (en/de/fr/it/fi patterns from the dataset). | LLM for every question: costs tokens and can hallucinate arithmetic. |
| Gemini sees facts, never the image | ~1-3k text tokens per question instead of an image call; answers must cite room/object ids that the UI highlights. Cheapest available model (`gemini-3.5-flash-lite`). | Multimodal call per question. |
| FastAPI + static vanilla JS frontend, one process on port 9999 | Simple to run on any teammate laptop: `python app.py`. No Node build. | React/Vite (the teammate's `stoa-trace` already covers that stack). |
| Analyses cached by file SHA-1 under `runtime/` | Re-uploading a file is instant and free. | Database: unnecessary for a demo. |

## Relationship to `stoa-trace`

The teammate's app (`stoa-trace/`, branch `codex/stoa-competitive-upgrade`) uses native PDF/DXF/IFC
records plus OpenAI vision. Its own report shows 0 % coverage on CubiCasa raster plans and no trained
model. This app is the raster specialist. Integration path: `stoa-trace` can POST an image to
`/api/analyze` here and use `facts.json` as another evidence source.

## Known limits

- PlanNet is trained on two drawing styles (Swiss Dwellings renderer, CubiCasa). Other styles (historic scans, US CAD sheets) are out of distribution; results there are not validated.
- GlyphNet is trained on Swiss Dwellings fonts. Finnish CubiCasa labels are not read; room types there come from the segmentation head.
- Apartment membership relies on the red dash-dot apartment boundary line of the Swiss style.
- The takeoff uses typical door/window opening sizes and a user-set ceiling height; it is an estimate, shown with its formula.

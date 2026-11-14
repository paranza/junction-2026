# Progress log (overnight build)

Branch: `feat/blueprint-analyzer`. App folder: `junction-testing/`. Port: 9999.
Teammate's separate app: `stoa-trace/` on `origin/codex/stoa-competitive-upgrade` (native PDF/DXF/IFC + OpenAI vision, 0% CubiCasa coverage, no trained model). Our work fills the raster gap with our own PyTorch models.

## Done

- [x] `backend/stoa/vector_dxf.py`: exact DXF parser (rooms, units, doors with double-door merge, windows, typed fixtures).
- [x] `backend/stoa/questions.py`: multilingual (en/de/fr/it/fi) template answering over a shared `facts` dict.
- [x] `backend/tools/eval_dxf.py`: swiss DXF path scores **1614/1614 counts, 732/744 areas** (98.4%).

## In progress / TODO (in order)

1. [ ] `labels.py`: align DXF to PNG (room-number anchors in PDF words) and rasterise training targets.
2. [ ] `models.py`: small multi-head U-Net (segmentation + CenterNet-style heatmaps) and CRNN text reader, plain PyTorch.
3. [ ] `train_seg.py`, `train_ocr.py`: CPU training on swiss_dwellings PNGs, group hold-out by site.
4. [ ] `pipeline.py`: image -> facts (rooms polygons, areas, objects, units) for raster; DXF and PDF fast paths.
5. [ ] `llm.py`: Gemini fallback over facts only (key from `.env`, never committed).
6. [ ] `app.py` FastAPI on 9999 + `frontend/` (vanilla JS, SVG overlays, click rooms/objects, chat).
7. [ ] CubiCasa5k: full annotated dataset downloading to `HACK-JUNCTION/datasets/cubicasa5k.zip`; add loader + train second model for Finnish raster plans.
8. [ ] Eval raster path on swiss PNG + cubicasa questions; docs (decisions, models, references).

## Notes

- Swiss PNG = A3 PDF rendered at 150 dpi (2480x1753), 1:200 -> 0.03387 m/px. DXF units metres; text inserts are centre-aligned.
- Counting rules were calibrated on questions.jsonl (drawing conventions, not answers memorised). Hold out sites when reporting raster accuracy.

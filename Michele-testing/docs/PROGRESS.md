# Progress log (overnight build)

Branch: `feat/blueprint-analyzer`. App folder: `Michele-testing/`. Port: 9999.

## Teammate work (merged from origin/main, 2026-11-14 ~08:00)

`stoa-trace/` (Trace): FastAPI + React, native PDF/DXF/IFC extraction, OpenAI vision fallback, evidence review UI, SQLite, deployed on a Verda VM. Its own benchmark: 55/97 numeric correct on a 100-question grouped sample, **0 % coverage on CubiCasa**, no trained model.

Insights to integrate:
- Keep scoring honest: their rule "answer labels never enter extraction or prompts". Our counting rules were calibrated on swiss questions; report raster accuracy only on held-out drawings (done in `tools/eval_raster.py`).
- Integration path: Trace can call our `/api/analyze` for raster plans and show our `facts.json` rooms/objects as evidence. Their IFC and PDF-schedule support covers what we skip.
- Their UI ideas worth copying if time: "Add missed object" / exclude candidate review, JSON export of an answer with evidence.

## Done

- [x] Exact DXF parser `stoa/vector_dxf.py` (rooms, units, double doors, windows, typed fixtures). Eval: **1614/1614 counts, 732/744 areas** on swiss questions.
- [x] Multilingual question templates `stoa/questions.py` (en/de/fr/it/fi).
- [x] `stoa/labels.py`: DXF -> PNG alignment (max 0.34 px error) and label rasterisation, 65 sheets.
- [x] `stoa/models.py`: PlanNet (U-Net + CenterNet heads, 2.9M params, stride-2 stem for CPU) and GlyphNet (CRNN + CTC).
- [x] `stoa/cubicasa.py`: CubiCasa5K SVG parser. Ground-truth counts match questions 97-100 % per type; question routing upper bound 4210/4270.
- [x] `train/build_cubicasa.py`: 4759 training + 241 held-out preview label files (balcony channel repaired by `train/fix_cc_balcony.py`).
- [x] `stoa/pipeline.py` (DXF / PDF / raster swiss / raster CubiCasa), `stoa/takeoff.py`, `stoa/llm.py` (gemini-3.5-flash-lite, facts only), `app.py`, frontend.
- [x] Docs: architecture, models, references, README.

## Running / TODO (in order)

1. [ ] PlanNet swiss training (started 07:32, 150 min, log `work/logs/plannet.log`). CPU-starved early by label builds.
2. [ ] GlyphNet: round 1 reached 37.6 % word accuracy; round 2 (60 min, resume) running, log `work/logs/glyph2.log`.
3. [ ] PlanNet CubiCasa: start after swiss finishes: `THREADS=6 python -m train.train_plannet --dataset cc --labels ../../../work/labels_cc --out weights/plannet_cc.pt --minutes 180`.
4. [ ] `python tools/eval_raster.py --set swiss` and `--set cc`; write `docs/evaluation.md` with real numbers.
5. [ ] Browser test of the full UI flow on PNG, PDF, DXF; fix visual issues.
6. [ ] Commit weights (small, ~12 MB each) so teammates can run without training.

## Notes

- Laptop: 6 P-cores + 8 E-cores, no GPU. `THREADS=6` is fastest for PlanNet; more threads are slower.
- Swiss PNG = A3 at 150 dpi, 1:200 -> 0.03387 m/px.
- RAM is tight (16 GB): the CubiCasa trainer streams samples from disk.

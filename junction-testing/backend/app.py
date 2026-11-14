"""FastAPI server: upload a drawing, get analysed facts, ask questions. Port 9999.

Run from junction-testing/backend:  python app.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
RUNTIME = os.environ.get("STOA_RUNTIME", os.path.join(ROOT, "runtime"))
FRONTEND = os.path.join(ROOT, "frontend")
os.makedirs(RUNTIME, exist_ok=True)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

from stoa import llm, pipeline, questions, takeoff  # noqa: E402

app = FastAPI(title="Blueprint analyzer")
PIPELINE_VERSION = "4"  # bump when analysis output changes; part of the cache key


def _weights_stamp() -> str:
    """Cache key part: retrained weights must not reuse old analyses."""
    w = os.path.join(HERE, "weights")
    return ",".join(f"{f}:{int(os.path.getmtime(os.path.join(w, f)))}" for f in sorted(os.listdir(w))) if os.path.isdir(w) else ""


ALLOWED = {".png", ".jpg", ".jpeg", ".pdf", ".dxf", ".bmp", ".tif", ".tiff", ".webp"}
MAX_BYTES = 40 * 1024 * 1024


def _dir(aid: str) -> str:
    if not aid.isalnum():
        raise HTTPException(400, "bad id")
    d = os.path.join(RUNTIME, aid)
    if not os.path.isdir(d):
        raise HTTPException(404, "analysis not found")
    return d


def _load(aid: str) -> dict:
    with open(os.path.join(_dir(aid), "facts.json"), encoding="utf8") as f:
        return json.load(f)


@app.on_event("startup")
def _preload():
    pipeline.Models.get()  # load weights once at boot, not on the first user's upload


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"unsupported file type {ext}; use PNG, JPG, PDF or DXF")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "file too large (40 MB max)")
    aid = hashlib.sha1(data + PIPELINE_VERSION.encode() + _weights_stamp().encode()).hexdigest()[:16]
    d = os.path.join(RUNTIME, aid)
    if os.path.exists(os.path.join(d, "facts.json")):  # same file analysed before: free
        facts = _load(aid)
        facts["cached"] = True
        return facts
    os.makedirs(d, exist_ok=True)
    src = os.path.join(d, "source" + ext)
    with open(src, "wb") as f:
        f.write(data)
    t0 = time.time()
    try:
        img, facts = pipeline.analyze_file(src)
    except Exception as e:
        shutil.rmtree(d, ignore_errors=True)
        raise HTTPException(422, f"analysis failed: {e}")
    cv2.imwrite(os.path.join(d, "image.png"), img)
    wall = facts.pop("wall_mask", None)
    if wall is not None:  # transparent wall overlay
        rgba = np.zeros((*wall.shape, 4), np.uint8)
        rgba[wall] = (40, 40, 220, 150)
        cv2.imwrite(os.path.join(d, "walls.png"), rgba)
    facts.update({"id": aid, "filename": file.filename, "seconds": round(time.time() - t0, 2),
                  "takeoff": takeoff.compute(facts), "has_walls": wall is not None})
    with open(os.path.join(d, "facts.json"), "w", encoding="utf8") as f:
        json.dump(facts, f, ensure_ascii=False)
    return facts


@app.get("/api/analysis/{aid}")
def get_analysis(aid: str):
    return _load(aid)


@app.get("/api/analysis/{aid}/image")
def image(aid: str):
    return FileResponse(os.path.join(_dir(aid), "image.png"), media_type="image/png")


@app.get("/api/analysis/{aid}/walls")
def walls(aid: str):
    p = os.path.join(_dir(aid), "walls.png")
    if not os.path.exists(p):
        raise HTTPException(404)
    return FileResponse(p, media_type="image/png")


@app.get("/api/analysis/{aid}/takeoff")
def get_takeoff(aid: str, ceiling_h: float = 2.5, waste: float = 0.10):
    if not (1.8 <= ceiling_h <= 6 and 0 <= waste <= 0.5):
        raise HTTPException(400, "ceiling 1.8-6 m, waste 0-50%")
    return takeoff.compute(_load(aid), ceiling_h, waste)


class Scale(BaseModel):
    px_length: float
    meters: float


@app.post("/api/analysis/{aid}/scale")
def set_scale(aid: str, body: Scale):
    """User calibration: a known dimension clicked on the drawing."""
    if not (body.px_length > 2 and 0.05 <= body.meters <= 1000):
        raise HTTPException(400, "measure at least a few pixels and a length between 0.05 and 1000 m")
    facts = _load(aid)
    facts = pipeline.apply_scale(facts, body.meters / body.px_length, f"calibrated by user ({body.meters} m)")
    facts["takeoff"] = takeoff.compute(facts)
    with open(os.path.join(_dir(aid), "facts.json"), "w", encoding="utf8") as f:
        json.dump(facts, f, ensure_ascii=False)
    return facts


class Ask(BaseModel):
    question: str
    history: list = []


@app.post("/api/analysis/{aid}/ask")
def ask(aid: str, body: Ask):
    q = body.question.strip()[:500]
    if not q:
        raise HTTPException(400, "empty question")
    facts = _load(aid)
    r = questions.answer(q, facts)
    if r is not None:
        v = r["value"]
        unit = {"m2": "m²", "count": ""}.get(r["unit"], r["unit"])
        return {"answer": f"{v} {unit}".strip(), "value": v, "unit": r["unit"], "evidence": r["evidence"],
                "explanation": r["explanation"], "method": "deterministic rule over model outputs (no LLM)",
                "tokens": {"in": 0, "out": 0}}
    return llm.ask(q, facts, facts.get("takeoff"), body.history)


@app.get("/api/samples")
def samples():
    """Demo files from the preview dataset, if present locally."""
    root = os.environ.get("STOA_DATA", os.path.join(ROOT, "..", "..", "preview_dataset"))
    sw = os.path.join(root, "data", "swiss_dwellings")
    out = []
    if os.path.isdir(sw):
        for f in sorted(os.listdir(sw))[:400]:
            if f.endswith((".png", ".dxf", ".pdf")):
                out.append({"name": f, "path": f"swiss_dwellings/{f}"})
    return out


@app.get("/api/samples/{src}/{name}")
def sample_file(src: str, name: str):
    root = os.environ.get("STOA_DATA", os.path.join(ROOT, "..", "..", "preview_dataset"))
    if src not in {"swiss_dwellings", "cubicasa5k"} or "/" in name or "\\" in name or ".." in name:
        raise HTTPException(400)
    p = os.path.join(root, "data", src, name)
    if not os.path.isfile(p):
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/api/health")
def health():
    m = pipeline.Models.get()
    return {"plannet": m.plan is not None, "glyphnet": m.glyph is not None,
            "plannet_eval": getattr(m, "plan_eval", None), "gemini": bool(os.environ.get("GEMINI_API_KEY"))}


app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", 9999)))

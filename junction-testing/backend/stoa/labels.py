"""Build pixel-perfect training targets for the raster models from paired DXF/PDF/PNG.

Swiss Dwellings ships each drawing three ways. The PNG is what users upload, the
DXF holds exact geometry, the PDF holds the text layer. We fit the DXF->PNG
transform from room-number anchors (DXF text insert vs PDF word centre), then
rasterise the DXF into label channels at PNG resolution.

Saved per drawing (npz): gray image, seg bitmask (SEG_CHANNELS bits), object
centres per class, word boxes + strings (for the OCR model), transform.
"""
from __future__ import annotations

import glob
import os
import re

import cv2
import fitz  # PyMuPDF
import numpy as np

from .vector_dxf import NUMBER_RE, parse_dxf

SEG_CHANNELS = ["wall", "room", "room_edge", "outdoor", "unit_edge", "text"]
OBJ_CLASSES = ["door", "window", "wc", "washbasin", "bathtub", "shower", "stove"]
PNG_DPI = 150


def fit_transform(plan, pdf_path: str):
    """Least squares for px = s*X + tx, py = -s*Y + ty (uniform scale, y flipped)."""
    page = fitz.open(pdf_path)[0]
    k = PNG_DPI / 72.0
    words = {}
    for w in page.get_text("words"):
        if NUMBER_RE.match(w[4]):
            words.setdefault(w[4], []).append(((w[0] + w[2]) / 2 * k, (w[1] + w[3]) / 2 * k))
    A, b = [], []
    for t in plan.texts:
        s = t["text"].strip()
        if t["layer"] == "ROOM_TEXT" and NUMBER_RE.match(s) and len(words.get(s, [])) == 1:
            (X, Y), (px, py) = t["xy"], words[s][0]
            A.append([X, 1, 0]); b.append(px)
            A.append([-Y, 0, 1]); b.append(py)
    if len(A) < 6:
        raise ValueError(f"not enough anchors in {pdf_path}")
    sol, res, *_ = np.linalg.lstsq(np.array(A), np.array(b), rcond=None)
    s, tx, ty = sol
    err = np.abs(np.array(A) @ sol - np.array(b)).max()
    return float(s), float(tx), float(ty), float(err)


def to_px(pts, T):
    s, tx, ty = T[:3]
    pts = np.asarray(pts, dtype=float)
    return np.stack([pts[..., 0] * s + tx, -pts[..., 1] * s + ty], -1)


def pdf_words(pdf_path: str):
    page = fitz.open(pdf_path)[0]
    k = PNG_DPI / 72.0
    return [(w[0] * k, w[1] * k, w[2] * k, w[3] * k, w[4]) for w in page.get_text("words")]


def build_sample(stem: str):
    plan = parse_dxf(stem + ".dxf")
    T = fit_transform(plan, stem + ".pdf")
    img = cv2.imread(stem + ".png", cv2.IMREAD_UNCHANGED)
    if img.ndim == 3 and img.shape[2] == 4:  # composite RGBA on white
        a = img[..., 3:4].astype(np.float32) / 255
        img = (img[..., :3] * a + 255 * (1 - a)).astype(np.uint8)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    H, W = gray.shape
    seg = np.zeros((len(SEG_CHANNELS), H, W), np.uint8)

    def fill(ch, poly):
        cv2.fillPoly(seg[ch], [np.round(to_px(poly, T)).astype(np.int32)], 1)

    def line(ch, poly, closed=True, th=3):
        cv2.polylines(seg[ch], [np.round(to_px(poly, T)).astype(np.int32)], closed, 1, th)

    for w in plan.walls + plan.wall_hatches:
        fill(0, w)
    for r in plan.rooms:
        if r["polygon"] is not None:
            fill(1, r["polygon"])
            line(2, r["polygon"])
            if r["outdoor"]:
                fill(3, r["polygon"])
    for u in plan.units:
        line(4, u["polygon"], closed=False, th=3)
    words = pdf_words(stem + ".pdf")
    for x0, y0, x1, y1, _ in words:
        cv2.rectangle(seg[5], (int(x0), int(y0)), (int(np.ceil(x1)), int(np.ceil(y1))), 1, -1)

    centres = {c: [] for c in OBJ_CLASSES}
    boxes = {c: [] for c in OBJ_CLASSES}
    for d in plan.doors:
        c = np.array(d["center"])
        if d.get("double"):
            c = (c + np.array(d["partner"]["center"])) / 2
            r = d["radius"] + d["partner"]["radius"]
        else:
            # centre of the swing quadrant: hinge + r/2 along the bisector
            a = np.radians(d["start"] + ((d["end"] - d["start"]) % 360) / 2)
            r = d["radius"]
            c = c + 0.5 * r * np.array([np.cos(a), np.sin(a)])
        p = to_px(c, T)
        centres["door"].append(p.tolist())
        half = r * T[0] / 2
        boxes["door"].append([p[0] - half, p[1] - half, p[0] + half, p[1] + half])
    for w in plan.windows:
        q = to_px(w["polygon"], T)
        centres["window"].append(q.mean(0).tolist())
        boxes["window"].append([*q.min(0), *q.max(0)])
    for f in plan.fixtures:
        if f["type"] in centres:
            x0, y0, x1, y1 = f["bbox"]
            q = to_px(np.array([[x0, y0], [x1, y1]]), T)
            centres[f["type"]].append(((q[0] + q[1]) / 2).tolist())
            boxes[f["type"]].append([q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()])

    packed = np.packbits(seg, axis=0)[0]  # 6 channels -> 1 byte per pixel
    return {
        "gray": gray, "seg": packed, "transform": np.array(T),
        "centres": {k: np.array(v, np.float32).reshape(-1, 2) for k, v in centres.items()},
        "boxes": {k: np.array(v, np.float32).reshape(-1, 4) for k, v in boxes.items()},
        "words": words,
    }


def unpack_seg(packed: np.ndarray) -> np.ndarray:
    return np.unpackbits(packed[None], axis=0)[: len(SEG_CHANNELS)]


def build_all(data_root: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    stems = sorted(p[:-4] for p in glob.glob(os.path.join(data_root, "data", "swiss_dwellings", "*.dxf")))
    report = []
    for stem in stems:
        name = os.path.basename(stem)
        try:
            s = build_sample(stem)
        except Exception as e:  # keep going; report the failure
            report.append((name, f"FAIL {e}"))
            continue
        np.savez_compressed(
            os.path.join(out_dir, name + ".npz"), gray=s["gray"], seg=s["seg"], transform=s["transform"],
            words=np.array([w[4] for w in s["words"]], dtype=object),
            word_boxes=np.array([w[:4] for w in s["words"]], np.float32).reshape(-1, 4),
            **{f"c_{k}": v for k, v in s["centres"].items()},
            **{f"b_{k}": v for k, v in s["boxes"].items()},
        )
        report.append((name, f"ok fit_err={s['transform'][3]:.2f}px"))
    return report


if __name__ == "__main__":
    import sys
    for r in build_all(sys.argv[1], sys.argv[2]):
        print(*r)

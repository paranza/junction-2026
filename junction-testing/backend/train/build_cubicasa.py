"""Rasterise CubiCasa5k SVG annotations into PlanNet training targets.

python -m train.build_cubicasa --cc ../../../datasets/cubicasa5k --out ../../../work/labels_cc --exclude ../../../preview_dataset
Images: F1_scaled.png resized by SCALE (0.5) to keep CPU training affordable.
Plans that appear in the Stoa preview are excluded (they are our test set).
"""
from __future__ import annotations

import argparse
import glob
import os
from multiprocessing import Pool

import cv2
import numpy as np

from stoa.cubicasa import ROOM_TYPES, furniture_kind, parse_svg, refine_wet_rooms

SCALE = 0.5
CC_SEG = ["wall", "room", "room_edge"] + ROOM_TYPES
CC_OBJ = ["door", "window", "wc", "sink", "bathtub", "shower", "stove", "sauna_stove"]


def wall_thickness(gray: np.ndarray) -> float:
    """Typical wall stroke thickness in px (used to normalise drawing scale at inference)."""
    dark = (gray < 110).astype(np.uint8)
    dt = cv2.distanceTransform(dark, cv2.DIST_L2, 3)
    ridge = (dt == cv2.dilate(dt, np.ones((3, 3), np.uint8))) & (dt >= 1.5)
    v = dt[ridge]
    if len(v) < 50:
        return 0.0
    return float(2 * np.median(v[v >= np.percentile(v, 70)]))


def build(args):
    d, out = args
    name = d.replace("\\", "/").strip("/").split("/")[-2] + "-" + d.replace("\\", "/").strip("/").split("/")[-1]
    dst = os.path.join(out, name + ".npz")
    if os.path.exists(dst):
        return name, "skip"
    try:
        a = refine_wet_rooms(parse_svg(os.path.join(d, "model.svg")))
        img = cv2.imread(os.path.join(d, "F1_scaled.png"), cv2.IMREAD_GRAYSCALE)
        H, W = int(img.shape[0] * SCALE), int(img.shape[1] * SCALE)
        gray = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
        seg = np.zeros((len(CC_SEG), H, W), np.uint8)
        P = lambda p: np.round(np.asarray(p) * SCALE).astype(np.int32)
        for w in a["walls"]:
            cv2.fillPoly(seg[0], [P(w)], 1)
        for s in a["spaces"]:
            if s["category"] == "garage":
                continue
            cv2.fillPoly(seg[1], [P(s["polygon"])], 1)
            cv2.polylines(seg[2], [P(s["polygon"])], True, 1, 2)
            if s["category"] in ROOM_TYPES:
                cv2.fillPoly(seg[3 + ROOM_TYPES.index(s["category"])], [P(s["polygon"])], 1)
        centres = {c: [] for c in CC_OBJ}
        boxes = {c: [] for c in CC_OBJ}
        for w in a["windows"]:
            q = np.asarray(w["polygon"]) * SCALE
            centres["window"].append(q.mean(0)); boxes["window"].append([*q.min(0), *q.max(0)])
        for dr in a["doors"]:
            if dr["type"].startswith("Door None"):
                continue
            q = np.asarray(dr["extent"]) * SCALE  # threshold + swing panel
            centres["door"].append(q.mean(0)); boxes["door"].append([*q.min(0), *q.max(0)])
        for f in a["furniture"]:
            k = furniture_kind(f["type"])
            if k in centres:
                b = np.array(f["bbox"]) * SCALE
                centres[k].append([(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]); boxes[k].append(b.tolist())
        packed = np.packbits(seg, axis=0)  # 12 channels -> 2 bytes
        np.savez_compressed(dst, gray=gray, seg=packed, n_seg=len(CC_SEG), floors=a["floors"],
                            wall_px=wall_thickness(gray),
                            **{f"c_{k}": np.array(v, np.float32).reshape(-1, 2) for k, v in centres.items()},
                            **{f"b_{k}": np.array(v, np.float32).reshape(-1, 4) for k, v in boxes.items()})
        return name, "ok"
    except Exception as e:
        return name, f"FAIL {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cc", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--exclude", default=None)
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--only_preview", action="store_true", help="build only the preview plans (test set)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    dirs = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(a.cc, "*", "*", "model.svg")))
    prev = set()
    if a.exclude:
        prev = {os.path.basename(p)[:-4] for p in glob.glob(os.path.join(a.exclude, "data", "cubicasa5k", "*.png"))}
    key = lambda d: d.replace("\\", "/").split("/")[-2] + "-" + d.replace("\\", "/").split("/")[-1]
    dirs = [d for d in dirs if (key(d) in prev) == a.only_preview]
    print(len(dirs), "plans", flush=True)
    with Pool(a.procs) as pool:
        for i, (n, r) in enumerate(pool.imap_unordered(build, [(d, a.out) for d in dirs], chunksize=8)):
            if r.startswith("FAIL") or i % 250 == 0:
                print(i, n, r, flush=True)


if __name__ == "__main__":
    main()

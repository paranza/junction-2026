"""Train PlanNet (segmentation + object-centre heatmaps) on CPU.

python -m train.train_plannet --labels ../../../work/labels_swiss --minutes 90
Holdout: every 8th drawing (sorted by name) is never trained on; the script reports
exact-count accuracy per class on those full drawings and keeps the best checkpoint.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import time

import cv2
import numpy as np
import torch

from stoa.labels import OBJ_CLASSES, SEG_CHANNELS
from stoa.models import PlanNet, dice_bce, focal_heat_loss, heat_peaks

# Active label set; main() switches it for --dataset cc (CubiCasa5k).
CFG = {"seg": SEG_CHANNELS, "obj": OBJ_CLASSES}

torch.set_num_threads(int(os.environ.get("THREADS", max(1, (os.cpu_count() or 4) - 2))))


def load(path):
    z = np.load(path, allow_pickle=True)
    f = CFG.get("scale", 1.0)
    if f != 1.0:  # train at reduced resolution: 4x cheaper per step at 0.5
        g = z["gray"]
        W, H = int(g.shape[1] * f), int(g.shape[0] * f)
        seg = np.unpackbits(z["seg"] if z["seg"].ndim == 3 else z["seg"][None], axis=0)[: len(CFG["seg"])]
        # keep thin lines (edges, text) alive when shrinking: max-pool style via INTER_AREA + threshold
        seg = np.stack([(cv2.resize(c.astype(np.float32), (W, H), interpolation=cv2.INTER_AREA) > 0.25).astype(np.uint8) for c in seg])
        return {"name": os.path.basename(path)[:-4], "gray": cv2.resize(g, (W, H), interpolation=cv2.INTER_AREA), "seg": seg,
                "centres": [z[f"c_{c}"] * f for c in CFG["obj"]], "boxes": [z[f"b_{c}"] * f for c in CFG["obj"]]}
    return {
        "name": os.path.basename(path)[:-4],
        "gray": z["gray"],
        "seg": np.unpackbits(z["seg"] if z["seg"].ndim == 3 else z["seg"][None], axis=0)[: len(CFG["seg"])],
        "centres": [z[f"c_{c}"] for c in CFG["obj"]],
        "boxes": [z[f"b_{c}"] for c in CFG["obj"]],
    }


def sigma_for(box):
    w, h = box[2] - box[0], box[3] - box[1]
    return float(np.clip(0.12 * min(w, h) + 1.0, 1.5, 4.0))


def render_heat(centres, boxes, H, W, M=None):
    heat = np.zeros((len(CFG["obj"]), H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    for c, (pts, bxs) in enumerate(zip(centres, boxes)):
        for (x, y), b in zip(pts, bxs):
            if M is not None:
                x, y = M @ np.array([x, y, 1.0])
            if not (-8 <= x < W + 8 and -8 <= y < H + 8):
                continue
            s = sigma_for(b) * (np.sqrt(abs(np.linalg.det(M[:, :2]))) if M is not None else 1)
            r = int(3 * s) + 1
            x0, x1 = max(0, int(x) - r), min(W, int(x) + r + 1)
            y0, y1 = max(0, int(y) - r), min(H, int(y) + r + 1)
            if x0 >= x1 or y0 >= y1:
                continue
            g = np.exp(-((xx[y0:y1, x0:x1] - x) ** 2 + (yy[y0:y1, x0:x1] - y) ** 2) / (2 * s * s))
            heat[c, y0:y1, x0:x1] = np.maximum(heat[c, y0:y1, x0:x1], g)
            ix, iy = int(round(x)), int(round(y))
            if 0 <= ix < W and 0 <= iy < H:
                heat[c, iy, ix] = 1.0
    return heat


def photometric(img):
    img = img.astype(np.float32)
    if random.random() < 0.5:
        img = (img - 128) * random.uniform(0.7, 1.3) + 128 + random.uniform(-25, 25)
    if random.random() < 0.3:
        img = cv2.GaussianBlur(img, (3, 3), random.uniform(0.3, 1.0))
    if random.random() < 0.3:
        img = img + np.random.normal(0, random.uniform(2, 10), img.shape)
    img = np.clip(img, 0, 255).astype(np.uint8)
    if random.random() < 0.3:
        ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, random.randint(40, 90)])
        img = cv2.imdecode(enc, cv2.IMREAD_GRAYSCALE)
    return img


def sample_crop(s, size):
    H, W = s["gray"].shape
    fg = s["seg"][0]
    # bias crop centres toward the drawing (walls), but sometimes anywhere (legend, title block)
    if random.random() < 0.85:
        ys, xs = np.nonzero(fg[::8, ::8])
        i = random.randrange(len(ys))
        cx, cy = xs[i] * 8, ys[i] * 8
    else:
        cx, cy = random.randrange(W), random.randrange(H)
    scale = random.uniform(0.8, 1.25)
    k = random.randrange(4)
    flip = random.random() < 0.5
    ang = 90 * k
    M = cv2.getRotationMatrix2D((float(cx), float(cy)), ang, scale)
    M[0, 2] += size / 2 - cx
    M[1, 2] += size / 2 - cy
    if flip:
        M = np.array([[-1, 0, size - 1], [0, 1, 0]]) @ np.vstack([M, [0, 0, 1]])
    img = cv2.warpAffine(s["gray"], M, (size, size), flags=cv2.INTER_LINEAR, borderValue=255)
    seg = np.stack([cv2.warpAffine(ch, M, (size, size), flags=cv2.INTER_NEAREST, borderValue=0) for ch in s["seg"]])
    heat = render_heat(s["centres"], s["boxes"], size, size, M)
    return photometric(img), seg, heat


def batch(samples, bs, size):
    X, S, Hm = [], [], []
    for _ in range(bs):
        smp = random.choice(samples)
        if isinstance(smp, str):  # streamed from disk (large datasets)
            smp = load(smp)
        img, seg, heat = sample_crop(smp, size)
        X.append(img); S.append(seg); Hm.append(heat)
    X = torch.from_numpy(np.stack(X)[:, None]).float() / 255.0
    return 1 - X, torch.from_numpy(np.stack(S)).float(), torch.from_numpy(np.stack(Hm))


@torch.no_grad()
def predict_full(model, gray, tile=1024, pad=64):
    """Tiled full-image inference -> (seg probs, heat probs)."""
    H, W = gray.shape
    x = 1 - torch.from_numpy(gray).float()[None, None] / 255.0
    seg = torch.zeros(model.n_seg, H, W)
    heat = torch.zeros(model.n_heat, H, W)
    for y0 in range(0, H, tile):
        for x0 in range(0, W, tile):
            ya, xa = max(0, y0 - pad), max(0, x0 - pad)
            yb, xb = min(H, y0 + tile + pad), min(W, x0 + tile + pad)
            crop = x[..., ya:yb, xa:xb]
            ph, pw = (-crop.shape[-2]) % 16, (-crop.shape[-1]) % 16
            crop = torch.nn.functional.pad(crop, (0, pw, 0, ph))
            s, h = model(crop)
            s, h = torch.sigmoid(s[0]), torch.sigmoid(h[0])
            ye, xe = min(H, y0 + tile), min(W, x0 + tile)
            seg[:, y0:ye, x0:xe] = s[:, y0 - ya:ye - ya, x0 - xa:xe - xa]
            heat[:, y0:ye, x0:xe] = h[:, y0 - ya:ye - ya, x0 - xa:xe - xa]
    return seg, heat


def evaluate(model, samples):
    model.eval()
    OBJ = CFG["obj"]
    exact = np.zeros(len(OBJ)); err = np.zeros(len(OBJ)); ious = []
    for s in samples:
        seg, heat = predict_full(model, s["gray"])
        peaks = heat_peaks(heat)
        for c in range(len(OBJ)):
            d = len(peaks[c]) - len(s["centres"][c])
            exact[c] += d == 0
            err[c] += abs(d)
        p, t = seg[1] > 0.5, torch.from_numpy(s["seg"][1]).bool()
        ious.append(float((p & t).sum() / ((p | t).sum() + 1)))
    model.train()
    n = len(samples)
    return {"exact": {c: float(exact[i] / n) for i, c in enumerate(OBJ)},
            "abs_err": {c: float(err[i] / n) for i, c in enumerate(OBJ)}, "room_iou": float(np.mean(ious))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", default="weights/plannet_swiss.pt")
    ap.add_argument("--minutes", type=float, default=90)
    ap.add_argument("--size", type=int, default=320)
    ap.add_argument("--bs", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--eval_every", type=int, default=400)
    ap.add_argument("--resume", default=None)
    ap.add_argument("--dataset", default="swiss", choices=["swiss", "cc"])
    ap.add_argument("--max_train", type=int, default=100000)
    ap.add_argument("--input_scale", type=float, default=1.0, help="resize sheets before training/inference")
    a = ap.parse_args()
    CFG["scale"] = a.input_scale
    if a.dataset == "cc":
        from train.build_cubicasa import CC_OBJ, CC_SEG
        CFG["seg"], CFG["obj"] = CC_SEG, CC_OBJ
    paths = sorted(glob.glob(os.path.join(a.labels, "*.npz")))
    hold = [p for i, p in enumerate(paths) if i % 8 == 0] if a.dataset == "swiss" else paths[::120][:40]
    rest = [p for p in paths if p not in hold]
    random.Random(0).shuffle(rest)
    train = [load(p) for p in rest[: a.max_train]] if a.dataset == "swiss" else rest[: a.max_train]
    if a.dataset == "cc":
        CFG["wall_px"] = float(np.median([float(np.load(p)["wall_px"]) for p in rest[:300]]))
        print("median wall thickness px", CFG["wall_px"], flush=True)
    val = [load(p) for p in hold]
    print(f"train {len(train)}  holdout {len(val)}: {[v['name'] for v in val]}", flush=True)
    model = PlanNet(len(CFG["seg"]), len(CFG["obj"]))
    if a.resume:
        model.load_state_dict(torch.load(a.resume, weights_only=False)["model"])
    print("params", sum(p.numel() for p in model.parameters()) / 1e6, "M", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
    t0, it, best = time.time(), 0, -1
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    total_s = a.minutes * 60
    seg_w = torch.tensor([1.0, 1.0, 1.0, 0.5, 1.0, 1.0]) if a.dataset == "swiss" else torch.ones(len(CFG["seg"]))
    while time.time() - t0 < total_s:
        frac = (time.time() - t0) / total_s
        for g in opt.param_groups:
            g["lr"] = a.lr * (0.02 + 0.98 * 0.5 * (1 + np.cos(np.pi * frac)))
        X, S, Hm = batch(train, a.bs, a.size)
        ps, ph = model(X)
        l_seg = sum(seg_w[c] * dice_bce(ps[:, c:c + 1], S[:, c:c + 1]) for c in range(S.shape[1])) / seg_w.sum()
        l_heat = focal_heat_loss(ph, Hm)
        loss = l_seg + l_heat
        opt.zero_grad(); loss.backward(); opt.step()
        it += 1
        if it % 25 == 0:
            print(f"it {it} t {time.time() - t0:.0f}s loss {loss.item():.3f} seg {l_seg.item():.3f} heat {l_heat.item():.3f}", flush=True)
        if it % a.eval_every == 0:
            r = evaluate(model, val)
            score = np.mean(list(r["exact"].values())) + r["room_iou"]
            print("EVAL", it, json.dumps(r), flush=True)
            torch.save({"model": model.state_dict(), "eval": r, "it": it}, a.out.replace(".pt", "_last.pt"))
            if score > best:
                best = score
                torch.save({"model": model.state_dict(), "eval": r, "it": it,
                            "seg_channels": CFG["seg"], "obj_classes": CFG["obj"], "wall_px": CFG.get("wall_px"), "input_scale": CFG["scale"]}, a.out)
                print("saved best", a.out, flush=True)
    r = evaluate(model, val)
    print("FINAL", json.dumps(r), flush=True)
    score = np.mean(list(r["exact"].values())) + r["room_iou"]
    if score > best:
        torch.save({"model": model.state_dict(), "eval": r, "it": it,
                    "seg_channels": CFG["seg"], "obj_classes": CFG["obj"], "wall_px": CFG.get("wall_px"), "input_scale": CFG["scale"]}, a.out)


if __name__ == "__main__":
    main()

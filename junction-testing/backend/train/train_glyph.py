"""Train GlyphNet (CRNN + CTC) to read words printed on raster plans.

Labels are free: the paired PDF text layer gives every word string and box, which
labels.py already projected to PNG pixels. Holdout = same drawings as PlanNet.

python -m train.train_glyph --labels ../../../work/labels_swiss --minutes 30
"""
from __future__ import annotations

import argparse
import glob
import os
import random
import time

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from stoa.models import CHAR2IDX, GlyphNet, ctc_decode

torch.set_num_threads(int(os.environ.get("THREADS", max(1, (os.cpu_count() or 4) - 2))))
H = 32


def crop_word(gray, box, jitter=False):
    x0, y0, x1, y1 = box
    p = 2 + (random.uniform(-1, 2) if jitter else 0)
    x0, y0, x1, y1 = int(max(0, x0 - p)), int(max(0, y0 - p)), int(min(gray.shape[1], x1 + p)), int(min(gray.shape[0], y1 + p))
    c = gray[y0:y1, x0:x1]
    if c.size == 0:
        return None
    w = max(8, int(round(c.shape[1] * H / max(1, c.shape[0]))))
    return cv2.resize(c, (w, H), interpolation=cv2.INTER_AREA)


def to_tensor(crops):
    W = max(c.shape[1] for c in crops)
    W += (-W) % 4
    X = np.full((len(crops), 1, H, W), 255, np.uint8)
    for i, c in enumerate(crops):
        X[i, 0, :, : c.shape[1]] = c
    return 1 - torch.from_numpy(X).float() / 255.0


def load_words(paths):
    items = []
    for p in paths:
        z = np.load(p, allow_pickle=True)
        g = z["gray"]
        for t, b in zip(z["words"], z["word_boxes"]):
            t = str(t)
            if t and all(ch in CHAR2IDX for ch in t) and (b[3] - b[1]) > 3:
                items.append((g, b, t))
    return items


def augment(c):
    c = c.astype(np.float32)
    if random.random() < 0.5:
        c = (c - 128) * random.uniform(0.7, 1.3) + 128 + random.uniform(-20, 20)
    if random.random() < 0.3:
        c = cv2.GaussianBlur(c, (3, 3), random.uniform(0.3, 0.9))
    if random.random() < 0.3:
        c = c + np.random.normal(0, random.uniform(2, 8), c.shape)
    if random.random() < 0.3:  # simulate other resolutions
        f = random.uniform(0.5, 1.0)
        small = cv2.resize(c, (max(4, int(c.shape[1] * f)), max(4, int(H * f))))
        c = cv2.resize(small, (c.shape[1], H))
    return np.clip(c, 0, 255).astype(np.uint8)


def accuracy(model, items, bs=64):
    model.eval()
    ok = 0
    with torch.no_grad():
        for i in range(0, len(items), bs):
            chunk = items[i:i + bs]
            crops = [crop_word(g, b) for g, b, _ in chunk]
            pred = ctc_decode(model(to_tensor(crops)))
            ok += sum(p[0] == t for p, (_, _, t) in zip(pred, chunk))
    model.train()
    return ok / max(1, len(items))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", default="weights/glyphnet_swiss.pt")
    ap.add_argument("--minutes", type=float, default=30)
    ap.add_argument("--bs", type=int, default=48)
    a = ap.parse_args()
    paths = sorted(glob.glob(os.path.join(a.labels, "*.npz")))
    hold = [p for i, p in enumerate(paths) if i % 8 == 0]
    train = load_words([p for p in paths if p not in hold])
    val = load_words(hold)
    print("train words", len(train), "val words", len(val), flush=True)
    model = GlyphNet()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    ctc = torch.nn.CTCLoss(blank=0, zero_infinity=True)
    t0, it, best = time.time(), 0, -1
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    while time.time() - t0 < a.minutes * 60:
        frac = (time.time() - t0) / (a.minutes * 60)
        for g in opt.param_groups:
            g["lr"] = 1e-3 * (0.05 + 0.95 * 0.5 * (1 + np.cos(np.pi * frac)))
        chunk = random.sample(train, a.bs)
        crops = [augment(crop_word(g, b, jitter=True)) for g, b, _ in chunk]
        X = to_tensor(crops)
        logp = model(X)
        tgt = torch.tensor([CHAR2IDX[ch] for _, _, t in chunk for ch in t])
        tl = torch.tensor([len(t) for _, _, t in chunk])
        il = torch.full((len(chunk),), logp.shape[0], dtype=torch.long)
        loss = ctc(logp, tgt, il, tl)
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5)
        opt.step(); it += 1
        if it % 100 == 0:
            print(f"it {it} t {time.time() - t0:.0f}s loss {loss.item():.3f}", flush=True)
        if it % 500 == 0:
            acc = accuracy(model, val)
            print(f"EVAL it {it} word_acc {acc:.4f}", flush=True)
            if acc > best:
                best = acc
                torch.save({"model": model.state_dict(), "word_acc": acc, "it": it}, a.out)
    acc = accuracy(model, val)
    print(f"FINAL word_acc {acc:.4f}", flush=True)
    if acc > best:
        torch.save({"model": model.state_dict(), "word_acc": acc, "it": it}, a.out)


if __name__ == "__main__":
    main()

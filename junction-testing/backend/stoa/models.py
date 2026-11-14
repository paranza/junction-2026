"""Our own small PyTorch models. No YOLO, no pretrained backbones, CPU friendly.

PlanNet  : U-Net with two heads.
           seg  -> per-pixel sigmoid channels (wall, room, room_edge, outdoor, unit_edge, text)
           heat -> CenterNet-style object-centre heatmaps (door, window, wc, washbasin, ...)
           Counting = number of heatmap peaks, so every count is backed by clickable points.
GlyphNet : CRNN (conv + BiGRU + CTC) that reads one cropped word (room names, numbers, areas).

References: Ronneberger et al. 2015 (U-Net), Zhou et al. 2019 "Objects as Points" (CenterNet),
Shi et al. 2015 (CRNN + CTC). See docs/references.md.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


def block(cin, cout):
    return nn.Sequential(
        nn.Conv2d(cin, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
        nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
    )


class PlanNet(nn.Module):
    """Stride-2 stem keeps CPU cost low: the U-Net runs at half resolution and a light
    full-resolution head (with a skip from the stem) restores thin lines and centres."""

    def __init__(self, n_seg=6, n_heat=7, widths=(32, 64, 112, 160, 224), stem=16):
        super().__init__()
        self.n_seg, self.n_heat = n_seg, n_heat
        self.stem = nn.Sequential(nn.Conv2d(1, stem, 3, padding=1, bias=False), nn.BatchNorm2d(stem), nn.ReLU(inplace=True))
        self.down = nn.Sequential(nn.Conv2d(stem, widths[0], 3, stride=2, padding=1, bias=False),
                                  nn.BatchNorm2d(widths[0]), nn.ReLU(inplace=True))
        self.enc = nn.ModuleList()
        cin = widths[0]
        for w in widths:
            self.enc.append(block(cin, w))
            cin = w
        self.up = nn.ModuleList()
        self.dec = nn.ModuleList()
        for i in range(len(widths) - 1, 0, -1):
            self.up.append(nn.ConvTranspose2d(widths[i], widths[i - 1], 2, stride=2))
            self.dec.append(block(widths[i - 1] * 2, widths[i - 1]))
        self.up0 = nn.ConvTranspose2d(widths[0], stem, 2, stride=2)
        self.head = nn.Sequential(nn.Conv2d(stem * 2, 24, 3, padding=1, bias=False), nn.BatchNorm2d(24), nn.ReLU(inplace=True))
        self.seg = nn.Conv2d(24, n_seg, 1)
        self.heat = nn.Sequential(nn.Conv2d(24, 24, 3, padding=1), nn.ReLU(inplace=True), nn.Conv2d(24, n_heat, 1))
        self.heat[-1].bias.data.fill_(-2.19)  # CenterNet prior: sigmoid -> 0.1

    def forward(self, x):
        s0 = self.stem(x)
        x = self.down(s0)
        skips = []
        for i, e in enumerate(self.enc):
            x = e(x)
            if i < len(self.enc) - 1:
                skips.append(x)
                x = F.max_pool2d(x, 2)
        for up, dec in zip(self.up, self.dec):
            x = up(x)
            s = skips.pop()
            if x.shape[-2:] != s.shape[-2:]:
                x = F.interpolate(x, size=s.shape[-2:])
            x = dec(torch.cat([x, s], 1))
        x = self.up0(x)
        if x.shape[-2:] != s0.shape[-2:]:
            x = F.interpolate(x, size=s0.shape[-2:])
        x = self.head(torch.cat([x, s0], 1))
        return self.seg(x), self.heat(x)


def focal_heat_loss(logits, target, alpha=2, beta=4):
    """CenterNet penalty-reduced focal loss on gaussian targets."""
    p = torch.sigmoid(logits).clamp(1e-4, 1 - 1e-4)
    pos = target.eq(1).float()
    neg = 1 - pos
    pos_loss = torch.log(p) * (1 - p) ** alpha * pos
    neg_loss = torch.log(1 - p) * p ** alpha * (1 - target) ** beta * neg
    n = pos.sum().clamp(min=1)
    return -(pos_loss.sum() + neg_loss.sum()) / n


def dice_bce(logits, target):
    bce = F.binary_cross_entropy_with_logits(logits, target)
    p = torch.sigmoid(logits)
    inter = (p * target).sum((0, 2, 3))
    dice = 1 - (2 * inter + 1) / (p.sum((0, 2, 3)) + target.sum((0, 2, 3)) + 1)
    return bce + dice.mean()


def heat_peaks(heat: torch.Tensor, thresh=0.35, k=7):
    """heat: (C,H,W) probabilities -> list per class of (x, y, score)."""
    hmax = F.max_pool2d(heat[None], k, stride=1, padding=k // 2)[0]
    keep = (heat == hmax) & (heat > thresh)
    out = []
    for c in range(heat.shape[0]):
        ys, xs = torch.nonzero(keep[c], as_tuple=True)
        out.append([(int(x), int(y), float(heat[c, y, x])) for y, x in zip(ys, xs)])
    return out


# ---------------------------------------------------------------- text reader
CHARSET = (" 0123456789.,:/-+()'%" "abcdefghijklmnopqrstuvwxyz" "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
           "äöüàâçéèêëîïôùûÄÖÜÉÈ²·«»")
CHAR2IDX = {c: i + 1 for i, c in enumerate(CHARSET)}  # 0 = CTC blank


class GlyphNet(nn.Module):
    """Input (B,1,32,W). Output (T,B,C) log-probs for CTC, T = W/4."""

    def __init__(self, n_classes=len(CHARSET) + 1):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(True), nn.MaxPool2d(2),          # 16
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(True), nn.MaxPool2d(2),         # 8
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(True), nn.MaxPool2d((2, 1)),  # 4
            nn.Conv2d(128, 160, 3, padding=1), nn.BatchNorm2d(160), nn.ReLU(True), nn.MaxPool2d((4, 1)), # 1
        )
        self.rnn = nn.GRU(160, 128, num_layers=2, bidirectional=True, batch_first=False, dropout=0.1)
        self.fc = nn.Linear(256, n_classes)

    def forward(self, x):
        f = self.cnn(x).squeeze(2).permute(2, 0, 1)  # (T,B,C)
        f, _ = self.rnn(f)
        return self.fc(f).log_softmax(-1)


def ctc_decode(logp: torch.Tensor):
    """Greedy CTC decode of (T,B,C) -> list of (text, confidence)."""
    best = logp.argmax(-1).T  # (B,T)
    probs = logp.exp().max(-1).values.T
    out = []
    for seq, pr in zip(best.tolist(), probs.tolist()):
        s, prev, conf = [], 0, []
        for i, c in enumerate(seq):
            if c != prev and c != 0:
                s.append(CHARSET[c - 1])
                conf.append(pr[i])
            prev = c
        out.append(("".join(s), min(conf) if conf else 0.0))
    return out

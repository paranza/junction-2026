"""Team-authored PlanNet architecture recovered from the earlier Michele prototype.
Used only for ONNX export; production inference uses ONNX Runtime.
"""
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



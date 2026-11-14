"""Small source-image network, trained on annotated opening instances.

No language model, file identifiers, annotation lookup, or expected counts are
inputs. The three heads predict centers, opening extents, and semantic pixels.
"""
import torch
from torch import nn
from torch.nn import functional as F


def block(cin, cout):
    return nn.Sequential(nn.Conv2d(cin, cout, 3, padding=1, bias=False),
                         nn.GroupNorm(8, cout), nn.SiLU(),
                         nn.Conv2d(cout, cout, 3, padding=1, bias=False),
                         nn.GroupNorm(8, cout), nn.SiLU())


class SymbolNet(nn.Module):
    def __init__(self):
        super().__init__()
        widths = (24, 48, 96, 160, 224)
        self.enc = nn.ModuleList([block(1, widths[0])] + [block(a, b) for a, b in zip(widths, widths[1:])])
        self.dec = nn.ModuleList([block(a+b, b) for a, b in zip(widths[:0:-1], widths[-2::-1])])
        self.centers = nn.Conv2d(24, 2, 1)
        self.extents = nn.Conv2d(24, 4, 1)
        self.semantic = nn.Conv2d(24, 3, 1)
        nn.init.constant_(self.centers.bias, -2.19)

    def forward(self, x):
        skips = []
        for index, layer in enumerate(self.enc):
            if index: x = F.avg_pool2d(x, 2)
            x = layer(x)
            skips.append(x)
        for layer, skip in zip(self.dec, reversed(skips[:-1])):
            x = F.interpolate(x, size=skip.shape[-2:], mode='bilinear', align_corners=False)
            x = layer(torch.cat([x, skip], 1))
        return self.centers(x), self.extents(x), self.semantic(x)


class ExportNet(nn.Module):
    def __init__(self, network):
        super().__init__()
        self.network = network

    def forward(self, image):
        centers, extents, _ = self.network(image)
        return centers.sigmoid(), extents.clamp(0, 7).exp()

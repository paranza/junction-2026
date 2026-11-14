# Models

All code in `backend/stoa/models.py`, written from scratch in PyTorch. No pretrained weights.

## PlanNet (one network per drawing style)

```
input  1 x H x W  grayscale, inverted (ink = 1)
stem   3x3 conv, 16 ch, full resolution ───────────────┐ skip
down   3x3 conv stride 2 -> 32 ch (half resolution)    │
U-Net  widths 32-64-112-160-224, 4 poolings, skips     │
up0    transpose conv back to full resolution ─────────┘ concat
head   3x3 conv 24 ch
 ├─ seg : 1x1 conv -> sigmoid per channel
 └─ heat: 3x3 conv + 1x1 conv -> sigmoid per object class (bias init -2.19, CenterNet prior)
```

2.9 M parameters. The stride-2 stem was added after profiling: the first version ran all
convolutions at full resolution and took 14 s per training step on CPU; this one takes 3.7 s
(6 threads), and full-sheet inference (2480 x 1753) takes a few seconds.

| Style | Seg channels | Heat classes | Training data |
| --- | --- | --- | --- |
| Swiss (`plannet_swiss.pt`) | wall, room, room_edge, outdoor, unit_edge (apartment line), text | door, window, wc, washbasin, bathtub, shower, stove | 56 Swiss Dwellings sheets, labels from DXF |
| CubiCasa (`plannet_cc.pt`) | wall, room, room_edge, bedroom, kitchen, living, bathroom, wc_room, sauna, balcony, corridor, storage | door, window, wc, sink, bathtub, shower, stove, sauna_stove | ~4,700 CubiCasa5K plans (preview plans excluded) |

**Losses.** Segmentation: BCE + soft Dice per channel. Heatmaps: CenterNet penalty-reduced focal
loss on Gaussian targets whose sigma scales with object size (1.5 to 4 px).

**Augmentation.** Random 320 px crops biased to the drawing, 90 degree rotations, flips,
0.8 to 1.25 scale, contrast/brightness, blur, Gaussian noise and JPEG compression (uploads are
often phone photos or re-saved screenshots).

**Decoding.**
- Objects: 7x7 max-pool non-maximum suppression on each heatmap, threshold 0.35. One peak = one object.
- Rooms: `room AND NOT room_edge AND NOT wall`, 3x3 opening, 4-connected components, regrown over the
  removed edge band, outer contour simplified with Douglas-Peucker (1.5 px).
- Apartments (Swiss): closed loops of the `unit_edge` channel, named by the `Whg. X` / `App. X` tag inside.
- Storeys (CubiCasa): building footprints from the wall channel; a footprint at least 25 % of the
  largest counts as a separate floor drawing.
- Scale normalisation (CubiCasa): uploads are resized so the measured wall stroke thickness matches the
  training median before inference.

## GlyphNet (word reader)

CRNN: 4 conv blocks (32-64-128-160) collapse height 32 to 1, 2-layer bidirectional GRU (128),
linear to 108 symbols + CTC blank. Greedy CTC decoding; the minimum per-character probability is
the word confidence.

Training words come for free from the PDF text layer projected to PNG pixels (7,287 training
words, 1,403 holdout words). Augmentation: contrast, blur, noise, down-up resampling.

At inference, PlanNet's `text` channel gives word blobs (closed horizontally with a 5x1 kernel),
each blob is read by GlyphNet, and label stacks (name / number / area) are assembled by geometry:
the name is the line just above a room number, the area the line just below.

## Why not bigger or pretrained

- The judging weights low inference cost and visible evidence; a 3 M parameter CPU model costs nothing per upload.
- The drawing styles are clean and consistent, so small models trained on exact labels reach high accuracy.
- Pretrained ImageNet features do not help much on line drawings; our labels are pixel-perfect, which matters more.

## Files

| File | Content |
| --- | --- |
| `weights/plannet_swiss.pt` | state dict + holdout metrics + channel names |
| `weights/plannet_cc.pt` | same, plus `wall_px` (training wall thickness) |
| `weights/glyphnet_swiss.pt` | state dict + holdout word accuracy |

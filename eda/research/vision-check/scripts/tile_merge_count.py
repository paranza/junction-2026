"""Tiling, box_2d conversion, cross-tile merge and per-family count accuracy.

numpy + pandas only. Run: python tile_merge_count.py  (runs the self-check at the bottom)
"""
import numpy as np
import pandas as pd


def to_pixels(box_2d, tile_w, tile_h, x0=0, y0=0):
    """Gemini box_2d [ymin, xmin, ymax, xmax] in 0-1000 of the image SENT -> full-image xyxy pixels."""
    ymin, xmin, ymax, xmax = box_2d
    return (x0 + xmin / 1000 * tile_w, y0 + ymin / 1000 * tile_h,
            x0 + xmax / 1000 * tile_w, y0 + ymax / 1000 * tile_h)


def tiles(w, h, size=768, overlap=0.25):
    """Overlapping (x0, y0, x1, y1) crops covering the image; the last row/column is snapped to the border."""
    step = max(1, int(size * (1 - overlap)))
    def starts(n):
        s = list(range(0, max(n - size, 0) + 1, step))
        if s[-1] + size < n:
            s.append(n - size)
        return s
    return [(x, y, min(x + size, w), min(y + size, h)) for y in starts(h) for x in starts(w)]


def nms(boxes, scores, thr=0.5, metric="ios"):
    """Greedy NMS. metric='ios' (intersection over smaller box, SAHI's default for slices) or 'iou'."""
    b = np.asarray(boxes, float).reshape(-1, 4)
    order = np.argsort(-np.asarray(scores, float))
    area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    keep = []
    while order.size:
        i, rest = order[0], order[1:]
        keep.append(int(i))
        w = np.clip(np.minimum(b[i, 2], b[rest, 2]) - np.maximum(b[i, 0], b[rest, 0]), 0, None)
        h = np.clip(np.minimum(b[i, 3], b[rest, 3]) - np.maximum(b[i, 1], b[rest, 1]), 0, None)
        inter = w * h
        denom = np.minimum(area[i], area[rest]) if metric == "ios" else area[i] + area[rest] - inter
        order = rest[inter / np.maximum(denom, 1e-9) <= thr]
    return keep


def family_accuracy(df, train=None):
    """df columns: family, truth, pred. Baseline = most common truth per family (from `train` if given)."""
    ref = df if train is None else train  # shortcut: mode taken on the eval set is optimistic; pass a train split
    mode = ref.groupby("family")["truth"].agg(lambda s: s.mode().iloc[0])
    out = df.assign(ok=df["pred"] == df["truth"], base_ok=df["truth"] == df["family"].map(mode))
    return out.groupby("family").agg(n=("ok", "size"), accuracy=("ok", "mean"), baseline=("base_ok", "mean"))


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    W, H, N = 2400, 1700, 40
    # N non-overlapping 30x30 "symbols" on a grid, so the true count is known
    cells = rng.choice(np.arange((W // 60) * (H // 60)), N, replace=False)
    gt = np.array([[c % (W // 60) * 60 + 10, c // (W // 60) * 60 + 10] for c in cells], float)
    gt = np.hstack([gt, gt + 30])

    merged_ios, merged_iou = [], []
    raw = []
    for (x0, y0, x1, y1) in tiles(W, H, size=768, overlap=0.25):
        tw, th = x1 - x0, y1 - y0
        for g in gt:  # simulate a VLM: returns the visible part of any symbol at least 30% inside the tile
            cx0, cy0, cx1, cy1 = max(g[0], x0), max(g[1], y0), min(g[2], x1), min(g[3], y1)
            if cx1 <= cx0 or cy1 <= cy0 or (cx1 - cx0) * (cy1 - cy0) < 0.3 * 900:
                continue
            box_2d = [round((cy0 - y0) / th * 1000), round((cx0 - x0) / tw * 1000),
                      round((cy1 - y0) / th * 1000), round((cx1 - x0) / tw * 1000)]
            raw.append(to_pixels(box_2d, tw, th, x0, y0))
    raw = np.array(raw)
    score = (raw[:, 2] - raw[:, 0]) * (raw[:, 3] - raw[:, 1])  # no VLM confidence: prefer the most complete box
    n_ios = len(nms(raw, score, 0.5, "ios"))
    n_iou = len(nms(raw, score, 0.5, "iou"))
    print(f"raw tile detections={len(raw)}  merged IOS={n_ios}  merged IoU={n_iou}  truth={N}")
    assert n_ios == N, "IOS merge must recover the true count"
    assert len(raw) > N, "test must contain cross-tile duplicates"

    # round-trip check of the conversion on one box
    assert np.allclose(to_pixels([250, 500, 750, 1000], 200, 100, 10, 20), (110, 45, 210, 95))

    df = pd.DataFrame({"family": ["windows"] * 4 + ["doors"] * 3,
                       "truth": [3, 5, 5, 8, 2, 2, 4],
                       "pred":  [3, 5, 4, 8, 2, 3, 4]})
    table = family_accuracy(df)
    print(table)
    assert table.loc["windows", "accuracy"] == 0.75 and table.loc["windows", "baseline"] == 0.5
    assert abs(table.loc["doors", "baseline"] - 2 / 3) < 1e-9
    print("all checks passed")

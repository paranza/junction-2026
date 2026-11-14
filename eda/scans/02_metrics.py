"""Per-file image statistics and quality metrics for the four scan sources (JPG only; SVGs handled in 05_svg.py).
Read-only on the dataset. Output: metrics.csv in the work dir.
Metric definitions (all on 8-bit grayscale unless noted):
  lap_var        variance of Laplacian at native resolution (content and resolution dependent)
  lap_var_1500   same after INTER_AREA resize to long side 1500 px (comparable across files)
  acutance       median Sobel magnitude on Canny edges / (p98-p2 intensity range); contrast-normalised edge steepness
  noise_sigma    Immerkaer (1996) noise sigma, computed only on pixels away from edges (flat paper)
  bg_resid_std   std of (gray - 7x7 median) on flat paper pixels: paper grain + sensor noise
  speckle_per_mp connected components of 1..6 px in an adaptive-threshold binarisation, per megapixel
  rms_contrast   gray std / 255;  range_contrast (p98-p2)/255
  otsu_eta       Otsu between-class variance / total variance (1 = perfectly bimodal ink/paper)
  fisher         (paper mean - ink mean) / pooled std of Otsu classes
  midtone_frac   share of pixels between 25% and 75% of the ink-paper range (photos and washes are high)
  skew_hough     length-weighted median angle of long near-axis Hough segments (deg, + = counter-clockwise)
  skew_support   share of that segment length within +-0.5 deg of the estimate
  skew_proj      projection-profile skew (deg) on a 1000 px binarised copy, search +-5 deg step 0.1
  bg_uneven      (p95-p5)/median of the estimated paper background map, inside the paper region
  dark_border    share of the image that is dark surround (scanner bed, book gutter) connected to the image edge
  chroma_*       per-pixel max(RGB)-min(RGB); colour_std = Hasler-Suesstrunk std term, tint = its mean term
"""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import sys, pathlib, json, math, warnings
import numpy as np, pandas as pd, cv2
from PIL import Image
from multiprocessing import Pool

warnings.filterwarnings("ignore")
Image.MAX_IMAGE_PIXELS = None
DS = pathlib.Path(_DATA + "")
OUT = pathlib.Path(__file__).parent
SOURCES = ["europeana", "finna", "habs", "wikimedia"]

STD_LUMA = np.array([16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56,
                     14, 17, 22, 29, 51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
                     49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99], float)


def jpeg_quality(im):
    """IJG quality whose scaled standard luminance table has the closest sum (order independent)."""
    q = getattr(im, "quantization", None)
    if not q:
        return np.nan
    actual = np.array(q[0], float).sum()
    best, bq = 1e18, np.nan
    for Q in range(1, 101):
        s = 5000 / Q if Q < 50 else 200 - 2 * Q
        t = np.clip(np.floor((STD_LUMA * s + 50) / 100), 1, 255).sum()
        if abs(t - actual) < best:
            best, bq = abs(t - actual), Q
    return bq


def resize_long(img, n):
    h, w = img.shape[:2]
    s = n / max(h, w)
    if s >= 1:
        return img
    return cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)


def skew_hough(gray):
    g = resize_long(gray, 2000)
    e = cv2.Canny(g, 50, 150)
    mn = int(0.08 * min(g.shape))
    lines = cv2.HoughLinesP(e, 1, np.pi / 1800, threshold=80, minLineLength=mn, maxLineGap=4)
    if lines is None:
        return np.nan, np.nan, 0
    x1, y1, x2, y2 = lines.reshape(-1, 4).T.astype(float)  # OpenCV 4 gives (N,1,4), OpenCV 5 gives (N,4)
    ang = np.degrees(np.arctan2(-(y2 - y1), x2 - x1))  # image y points down; + = counter-clockwise
    ang = (ang + 45) % 90 - 45  # deviation from nearest axis
    ln = np.hypot(x2 - x1, y2 - y1)
    keep = np.abs(ang) <= 10
    if keep.sum() < 5:
        return np.nan, np.nan, int(keep.sum())
    a, l = ang[keep], ln[keep]
    o = np.argsort(a)
    cw = np.cumsum(l[o])
    med = a[o][np.searchsorted(cw, cw[-1] / 2)]
    support = l[np.abs(a - med) <= 0.5].sum() / l.sum()
    return float(med), float(support), int(keep.sum())


def skew_proj(binary_ink):
    """binary_ink: uint8 0/1 ink mask at ~1000 px. Max of summed squared row+column projections."""
    h, w = binary_ink.shape
    c = (w / 2, h / 2)
    best, ba = -1, 0.0
    for a in np.arange(-5, 5.0001, 0.1):
        M = cv2.getRotationMatrix2D(c, a, 1.0)
        r = cv2.warpAffine(binary_ink, M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0).astype(np.float64)
        sc = (r.sum(1) ** 2).sum() + (r.sum(0) ** 2).sum()
        if sc > best:
            best, ba = sc, a
    return float(round(ba, 1))  # warpAffine positive angle = counter-clockwise rotation; skew estimate is -ba


def word_groups(st, shape):
    """Lettering proxy: character-like components (from connectedComponentsWithStats `st`) that sit in a
    horizontal run of >=3 similar-height neighbours (a "word"). Returns (DataFrame per word with size = chars,
    median/std height, cx/cy centre; number of char-like components).
    shortcut: horizontal text only, rotated or vertical labels are missed."""
    areas, hh, ww = st[1:, cv2.CC_STAT_AREA], st[1:, cv2.CC_STAT_HEIGHT], st[1:, cv2.CC_STAT_WIDTH]
    fill = areas / np.maximum(hh * ww, 1)
    charlike = (hh >= 4) & (hh <= 80) & (ww >= 1) & (ww <= 1.5 * hh) & (fill > 0.12) & (fill < 0.9) & (areas >= 6)
    idx = np.nonzero(charlike)[0]
    empty = pd.DataFrame(columns=["size", "median", "std", "cx", "cy"])
    if len(idx) < 10:
        return empty, int(len(idx))
    boxes = np.zeros(shape, np.uint8)
    x0, y0 = st[1:, cv2.CC_STAT_LEFT][idx], st[1:, cv2.CC_STAT_TOP][idx]
    for x, y, ww_, hh_ in zip(x0, y0, ww[idx], hh[idx]):
        boxes[y + hh_ // 3: y + hh_ - hh_ // 3 + 1, x: x + ww_] = 255  # middle band only, so lines do not merge vertically
    nw, wl = cv2.connectedComponents(cv2.dilate(boxes, np.ones((1, 7), np.uint8)))
    cy = (y0 + hh[idx] // 2).clip(0, shape[0] - 1)
    cx = (x0 + ww[idx] // 2).clip(0, shape[1] - 1)
    dfc = pd.DataFrame({"w": wl[cy, cx], "h": hh[idx], "cx": cx, "cy": cy})
    dfc = dfc[dfc.w > 0]
    agg = dfc.groupby("w").agg(size=("h", "size"), median=("h", "median"), std=("h", "std"), cx=("cx", "mean"), cy=("cy", "mean"))
    return agg[(agg["size"] >= 3) & (agg["std"].fillna(0) <= 0.25 * agg["median"])], int(len(idx))


def analyze(rel):
    p = DS / rel
    d = {"path": rel, "source": rel.split("/")[1], "file": p.name, "bytes": p.stat().st_size}
    try:
        im = Image.open(p)
        d.update(mode=im.mode, width=im.width, height=im.height, fmt=im.format,
                 dpi=str(im.info.get("dpi", "")), progressive=bool(im.info.get("progressive", False)),
                 icc=bool(im.info.get("icc_profile")), jpeg_q=jpeg_quality(im))
        im.load()
        if im.mode in ("L", "1", "I;16", "I"):
            gray = np.asarray(im.convert("L"))
            rgb = None
        else:
            rgb = np.asarray(im.convert("RGB"))
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    except Exception as ex:  # keep going, record the failure
        d["error"] = repr(ex)
        return d
    h, w = gray.shape
    d["mp"] = h * w / 1e6
    d["aspect"] = max(h, w) / min(h, w)
    d["orientation"] = "landscape" if w > h else ("portrait" if h > w else "square")
    d["bytes_per_px"] = d["bytes"] / (h * w)

    # colour
    if rgb is not None:
        r, g, b = [rgb[..., i].astype(np.float32) for i in range(3)]
        chroma = rgb.max(2).astype(np.int16) - rgb.min(2).astype(np.int16)
        d["chroma_p50"], d["chroma_p99"] = np.percentile(chroma, [50, 99])
        d["chroma_frac_gt30"] = float((chroma > 30).mean())
        rg, yb = r - g, 0.5 * (r + g) - b
        d["colour_std"] = float(np.sqrt(rg.std() ** 2 + yb.std() ** 2))
        d["tint"] = float(np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))
        hsv = cv2.cvtColor(resize_long(rgb, 1000), cv2.COLOR_RGB2HSV)
        d["sat_frac_gt100"] = float(((hsv[..., 1] > 100) & (hsv[..., 2] > 60)).mean())
    else:
        for k in ["chroma_p50", "chroma_p99", "chroma_frac_gt30", "colour_std", "tint", "sat_frac_gt100"]:
            d[k] = 0.0

    # polarity: blueprints and negatives have light lines on dark paper; normalise so ink is dark
    t0, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    d["inverted"] = bool(np.median(gray) <= t0)
    g8 = 255 - gray if d["inverted"] else gray
    gf = g8.astype(np.float64)
    # sharpness
    d["lap_var"] = float(cv2.Laplacian(g8, cv2.CV_64F).var())
    d["lap_var_1500"] = float(cv2.Laplacian(resize_long(g8, 1500), cv2.CV_64F).var())
    p2, p5, p50, p95, p98 = np.percentile(g8, [2, 5, 50, 95, 98])
    rng = max(p98 - p2, 1.0)
    edges = cv2.Canny(g8, 50, 150)
    gx = cv2.Sobel(gf, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gf, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    d["edge_density"] = float((edges > 0).mean())
    d["acutance"] = float(np.median(mag[edges > 0]) / rng) if (edges > 0).any() else np.nan

    # noise on flat pixels (away from dilated edges)
    flat = cv2.dilate(edges, np.ones((7, 7), np.uint8)) == 0
    flat[:2, :] = flat[-2:, :] = False
    flat[:, :2] = flat[:, -2:] = False
    M = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], float)
    conv = np.abs(cv2.filter2D(gf, cv2.CV_64F, M))
    d["flat_frac"] = float(flat.mean())
    d["noise_sigma"] = float(np.sqrt(np.pi / 2) * conv[flat].mean() / 6) if flat.any() else np.nan
    resid = gf - cv2.medianBlur(g8, 7).astype(np.float64)
    d["bg_resid_std"] = float(resid[flat].std()) if flat.any() else np.nan

    # contrast and bimodality
    d["rms_contrast"] = float(gf.std() / 255)
    d["range_contrast"] = float(rng / 255)
    d["p2"], d["p50"], d["p98"] = float(p2), float(p50), float(p98)
    t, _ = cv2.threshold(g8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    fg, bg = gf[g8 <= t], gf[g8 > t]
    if len(fg) and len(bg):
        w0, w1 = len(fg) / gf.size, len(bg) / gf.size
        between = w0 * w1 * (bg.mean() - fg.mean()) ** 2
        d["otsu_t"] = float(t)
        d["otsu_eta"] = float(between / max(gf.var(), 1e-9))
        d["fisher"] = float((bg.mean() - fg.mean()) / np.sqrt((fg.var() + bg.var()) / 2 + 1e-9))
        d["ink_frac_otsu"] = float(w0)
        lo, hi = fg.mean(), bg.mean()
        d["midtone_frac"] = float(((gf > lo + 0.25 * (hi - lo)) & (gf < lo + 0.75 * (hi - lo))).mean())
        d["paper_level"], d["ink_level"] = float(np.median(bg)), float(np.median(fg))

    # adaptive binarisation for speckle count (block ~ 1/60 of long side, odd)
    blk = max(15, int(max(h, w) / 60) | 1)
    ink = cv2.adaptiveThreshold(g8, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, blk, 15)
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    areas = st[1:, cv2.CC_STAT_AREA]
    d["cc_per_mp"] = float(len(areas) / d["mp"])
    d["speckle_per_mp"] = float(((areas >= 1) & (areas <= 6)).sum() / d["mp"])
    d["ink_frac_adapt"] = float((ink > 0).mean())
    good, d["n_charlike"] = word_groups(st, g8.shape)
    d["n_words"] = int(len(good))
    if len(good) >= 5:
        wh = np.repeat(good["median"].values, good["size"].values.astype(int))  # weight by characters
        d["text_h_p25"], d["text_h_p50"], d["text_h_p75"] = [float(x) for x in np.percentile(wh, [25, 50, 75])]

    # skew
    d["skew_hough"], d["skew_support"], d["skew_nseg"] = skew_hough(g8)
    small = resize_long(g8, 1000)
    tb, _ = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    sink = (small <= tb).astype(np.uint8)
    d["skew_proj"] = -skew_proj(sink)

    # background map and unevenness
    s5 = resize_long(g8, 500)
    k = max(5, int(max(s5.shape) / 33) | 1)
    bgm = cv2.medianBlur(cv2.morphologyEx(s5, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8)), 2 * (k // 2) + 1)
    med = np.median(bgm)
    dark = (bgm < 0.6 * np.percentile(bgm, 90)).astype(np.uint8)
    # dark surround = dark components touching the border
    nd, labd = cv2.connectedComponents(dark)
    border_labels = set(np.unique(np.concatenate([labd[0], labd[-1], labd[:, 0], labd[:, -1]]))) - {0}
    surround = np.isin(labd, list(border_labels)) if border_labels else np.zeros_like(dark, bool)
    d["dark_border"] = float(surround.mean())
    paper = ~surround
    pv = bgm[paper] if paper.any() else bgm.ravel()
    q5, q50, q95 = np.percentile(pv, [5, 50, 95])
    d["bg_uneven"] = float((q95 - q5) / max(q50, 1))
    d["bg_level"] = float(q50)
    if rgb is not None:
        c5 = resize_long(rgb, 500)
        cm = cv2.medianBlur(cv2.morphologyEx(c5, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8)), 2 * (k // 2) + 1)
        cch = cm.max(2).astype(float) - cm.min(2).astype(float)
        d["bg_chroma_p50"], d["bg_chroma_spread"] = float(np.median(cch[paper])), float(np.subtract(*np.percentile(cch[paper], [95, 5])))
    return d


if __name__ == "__main__":
    rels = []
    for s in SOURCES:
        for f in sorted((DS / "data" / s).iterdir()):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                rels.append(f"data/{s}/{f.name}")
    if len(sys.argv) > 1:
        rels = rels[: int(sys.argv[1])]
    with Pool(8) as pool:
        rows = pool.map(analyze, rels, chunksize=2)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "metrics.csv", index=False)
    print(len(df), "files;", df.get("error", pd.Series(dtype=str)).notna().sum(), "errors")

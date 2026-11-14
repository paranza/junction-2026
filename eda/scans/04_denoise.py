"""Cheap classical cleanup on noisy scans: compare crops side by side and measure simple proxies.
Usage: 04_denoise.py cases.json   where cases.json = [{"path": "data/...", "crop": [x, y, w, h] or "auto"}, ...]
"auto" picks the 560x340 window holding the most word-like text groups in the original (so crops show text).
Variants (all at native resolution, whole page, then cropped):
  orig      original (colour kept in the panel)
  flat      grayscale / estimated paper background (removes tint, stains, uneven light; keeps anti-aliasing)
  sauvola   Sauvola binarisation of flat (window ~ long side / 100, k=0.2)   [adaptive thresholding]
  open      sauvola + 2x2 morphological opening of the ink (classic speckle removal)
  nlm       OpenCV fastNlMeansDenoising(h=12) on flat
  deskew    flat rotated by the measured projection-profile skew (only differs when |skew| >= 0.2 deg)
Proxies per variant on the whole page, after binarising (Sauvola for grayscale variants):
  speckle_per_mp  ink blobs of 1-6 px per MP (noise)
  dots_per_mp     compact blobs of 7-40 px per MP (decimal points, dotted lines, i-dots: should survive)
  n_words, chars_in_words, text_h_p50   word-like groups from 02_metrics.word_groups (text that a reader could segment)
Outputs: denoise/<stem>_panel.png and denoise_proxies.csv"""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import sys, json, pathlib, importlib.util
import numpy as np, pandas as pd, cv2
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
HERE = pathlib.Path(__file__).parent
DS = pathlib.Path(_DATA + "")
OUT = HERE / "denoise"; OUT.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location("m", HERE / "02_metrics.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
CW, CH = 560, 340


def flatten(gray):
    k = max(15, int(max(gray.shape) / 100) | 1)  # wider than any stroke, narrower than paper variation
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    bg = cv2.GaussianBlur(bg, (0, 0), k / 2)
    return np.clip(gray.astype(np.float32) / np.maximum(bg.astype(np.float32), 1) * 255, 0, 255).astype(np.uint8)


def sauvola(gray, win, k=0.2, R=128):
    g = gray.astype(np.float64)
    mean = cv2.boxFilter(g, -1, (win, win), borderType=cv2.BORDER_REFLECT)
    sq = cv2.boxFilter(g * g, -1, (win, win), borderType=cv2.BORDER_REFLECT)
    std = np.sqrt(np.maximum(sq - mean * mean, 0))
    return (g <= mean * (1 + k * (std / R - 1))).astype(np.uint8)  # 1 = ink


def words(gray8):
    """Same binarisation and grouping as 02_metrics (adaptive Gaussian threshold, block ~ long side / 60)."""
    blk = max(15, int(max(gray8.shape) / 60) | 1)
    ink = cv2.adaptiveThreshold(gray8, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, blk, 15)
    _, _, st, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    good, _ = m.word_groups(st, gray8.shape)
    return good


def proxies(ink):
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    a, h, w = st[1:, cv2.CC_STAT_AREA], st[1:, cv2.CC_STAT_HEIGHT], st[1:, cv2.CC_STAT_WIDTH]
    mp = ink.size / 1e6
    compact = (np.maximum(h, w) <= 2 * np.minimum(h, w)) & (a >= 0.4 * h * w)
    return {"speckle_per_mp": ((a >= 1) & (a <= 6)).sum() / mp, "dots_per_mp": ((a >= 7) & (a <= 40) & compact).sum() / mp,
            "ink_frac": float(ink.mean())}


def auto_crop(gray):
    g = words(gray)
    H, W = gray.shape
    if not len(g):
        return [max(0, W // 2 - CW // 2), max(0, H // 2 - CH // 2), min(CW, W), min(CH, H)]
    cx, cy, n = g["cx"].values, g["cy"].values, g["size"].values
    best, bxy = -1, (0, 0)
    for x, y in zip(cx, cy):  # candidate windows centred on each word
        x0 = int(np.clip(x - CW / 2, 0, max(0, W - CW))); y0 = int(np.clip(y - CH / 2, 0, max(0, H - CH)))
        s = n[(cx >= x0) & (cx < x0 + CW) & (cy >= y0) & (cy < y0 + CH)].sum()
        if s > best:
            best, bxy = s, (x0, y0)
    return [bxy[0], bxy[1], min(CW, W), min(CH, H)]


if __name__ == "__main__":
    cases = json.loads(pathlib.Path(sys.argv[1]).read_text())
    rows = []
    for c in cases:
        p = HERE / "cache" / c["path"]  # local copy from 00_cache.py; fall back to the dataset
        p = p if p.exists() else DS / c["path"]; stem = p.stem
        rgb = np.asarray(Image.open(p).convert("RGB")); gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        t0, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        inverted = bool(np.median(gray) <= t0)
        if inverted:  # blueprint / negative: make ink dark, as in 02_metrics
            gray = 255 - gray
        win = max(15, int(max(gray.shape) / 100) | 1)
        flat = flatten(gray)
        sv = sauvola(flat, win)
        op = cv2.morphologyEx(sv, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        nlm = cv2.fastNlMeansDenoising(flat, None, h=12, templateWindowSize=7, searchWindowSize=21)
        small = m.resize_long(gray, 1000); t, _ = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        skew = -m.skew_proj((small <= t).astype(np.uint8))
        if abs(skew) >= 0.2:
            M = cv2.getRotationMatrix2D((gray.shape[1] / 2, gray.shape[0] / 2), -skew, 1.0)  # rotate back
            desk = cv2.warpAffine(flat, M, (gray.shape[1], gray.shape[0]), flags=cv2.INTER_CUBIC, borderValue=255)
        else:
            desk = flat
        s2 = m.resize_long(desk, 1000); t2, _ = cv2.threshold(s2, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        skew_after = -m.skew_proj((s2 <= t2).astype(np.uint8))
        variants = {"orig": gray, "flat": flat, "sauvola": (1 - sv) * 255, "open": (1 - op) * 255, "nlm": nlm, "deskew": desk}
        crop = auto_crop(gray) if c["crop"] == "auto" else c["crop"]
        for name, img in variants.items():
            if name == "flat":
                continue  # its binarised form is exactly the sauvola variant
            ink = sauvola(img, win) if name in ("orig", "nlm", "deskew") else (img < 128).astype(np.uint8)
            g = words(img.astype(np.uint8))
            wh = np.repeat(g["median"].values, g["size"].values.astype(int)) if len(g) else np.array([])
            r = {"file": c["path"], "variant": name, "inverted": inverted, **proxies(ink), "n_words": len(g),
                 "chars_in_words": int(g["size"].sum()) if len(g) else 0, "text_h_p50": float(np.median(wh)) if len(wh) else np.nan,
                 "crop": crop}
            if name == "deskew":
                r["skew_before"], r["skew_after"] = skew, skew_after
            rows.append(r)
        x, y, w, h = crop
        tiles = [("original", Image.fromarray(rgb[y:y + h, x:x + w]))]
        for name in ["flat", "sauvola", "open", "nlm", "deskew"]:
            tiles.append((name, Image.fromarray(variants[name][y:y + h, x:x + w]).convert("RGB")))
        W, H = w, h + 22
        panel = Image.new("RGB", (3 * W + 20, 2 * H + 10), (255, 0, 255))
        for i, (name, tile) in enumerate(tiles):
            px, py = (i % 3) * (W + 10), (i // 3) * (H + 10)
            panel.paste(Image.new("RGB", (W, 22), (255, 255, 255)), (px, py))
            ImageDraw.Draw(panel).text((px + 4, py + 4), f"{name}  ({stem[:28]} x{x} y{y}, native px)", fill=(0, 0, 0))
            panel.paste(tile, (px, py + 22))
        panel.save(OUT / f"{stem}_panel.png")
        print("panel", OUT / f"{stem}_panel.png", panel.size, "crop", crop, "inverted", inverted, "skew", skew, "->", skew_after, flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "denoise_proxies.csv", index=False)
    pd.set_option("display.width", 220)
    print(df.drop(columns=["crop"]).round(3).to_string(index=False))

import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Independent pixel pass over all scan JPGs: colour class, polarity, noise (Haar-HH MAD), contrast,
# ink retention under morphological opening, stroke width, text-height proxy, dHash.
import os, sys, csv, math
import numpy as np, cv2
from multiprocessing import Pool
D = _DATA + "/data"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v02_pixels.csv")

def text_heights(mask):
    n, lab, st, cen = cv2.connectedComponentsWithStats(mask, connectivity=8)
    x, y, w, h, a = st[1:, 0], st[1:, 1], st[1:, 2], st[1:, 3], st[1:, 4]
    ok = (h >= 4) & (h <= 80) & (w >= 1) & (w <= 2.5 * h) & (a >= 0.1 * w * h) & (a <= 0.95 * w * h) & ~((w <= 2) & (h <= 4))
    x, y, w, h = x[ok], y[ok], w[ok], h[ok]
    if len(h) < 3: return np.array([])
    yc = y + h / 2.0; xc = x + w / 2.0
    o = np.argsort(yc); x, y, w, h, yc, xc = x[o], y[o], w[o], h[o], yc[o], xc[o]
    nb = np.zeros(len(h), int)
    lo = np.searchsorted(yc, yc - 0.35 * h); hi = np.searchsorted(yc, yc + 0.35 * h, side='right')
    for i in range(len(h)):
        j = np.arange(lo[i], hi[i]); j = j[j != i]
        if len(j) == 0: continue
        sel = (np.abs(h[j] - h[i]) <= 0.35 * h[i]) & (np.abs(xc[j] - xc[i]) <= 1.6 * h[i])
        nb[i] = sel.sum()
    return h[nb >= 2]  # a char with at least two similar-height horizontal neighbours

def one(args):
    s, f = args
    p = os.path.join(D, s, f)
    try:
        bgr = cv2.imread(p, cv2.IMREAD_COLOR)
        H, W = bgr.shape[:2]; L = max(H, W)
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        # colour class on a 800 px copy
        k = 800 / L if L > 800 else 1.0
        sm = cv2.resize(bgr, (max(1, int(W * k)), max(1, int(H * k))), interpolation=cv2.INTER_AREA) if k < 1 else bgr
        lab = cv2.cvtColor(sm.astype(np.float32) / 255, cv2.COLOR_BGR2Lab).reshape(-1, 3)
        a, b = lab[:, 1], lab[:, 2]; c = np.hypot(a, b); hue = np.degrees(np.arctan2(b, a))
        chroma_p99 = float(np.percentile(c, 99)); hi_c = c > 15
        frac_c15 = float(hi_c.mean())
        if hi_c.sum() > 50:
            ang = np.radians(hue[hi_c]); wts = c[hi_c]
            dom = math.degrees(math.atan2((np.sin(ang) * wts).sum(), (np.cos(ang) * wts).sum()))
            d = np.abs((hue[hi_c] - dom + 180) % 360 - 180)
            off_frac = float((d > 60).sum() / len(c))  # share of ALL pixels that are colourful and off the dominant hue
        else:
            dom, off_frac = float('nan'), 0.0
        # polarity: mode of central region histogram
        gs = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY); hh, ww = gs.shape
        cen = gs[int(hh * .1):int(hh * .9), int(ww * .1):int(ww * .9)]
        hist = np.bincount((cen // 8).ravel(), minlength=32); mode = int(hist.argmax() * 8 + 4)
        inverted = mode < 110
        p2, p50, p98 = np.percentile(g, [2, 50, 98])
        # noise: Donoho MAD on Haar HH at native resolution
        gf = g.astype(np.float32); h2, w2 = (H // 2) * 2, (W // 2) * 2; q = gf[:h2, :w2]
        HH = (q[0::2, 0::2] - q[0::2, 1::2] - q[1::2, 0::2] + q[1::2, 1::2]) / 2
        sigma_mad = float(np.median(np.abs(HH)) / 0.6745)
        # flat-paper residual: 8x8 blocks whose range <= 12 grey levels, std of block minus block mean
        bh, bw = H // 8, W // 8; blk = gf[:bh * 8, :bw * 8].reshape(bh, 8, bw, 8).transpose(0, 2, 1, 3).reshape(bh, bw, 64)
        rng = blk.max(-1) - blk.min(-1); flat = rng <= 12
        flat_std = float(np.median(blk[flat].std(-1))) if flat.sum() > 20 else float('nan')
        # binarise at native resolution with polarity fixed
        gi = 255 - g if inverted else g
        ink = cv2.adaptiveThreshold(gi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 12)
        n_ink = int((ink > 0).sum())
        ret = {}
        for kk in (2, 3):
            op = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((kk, kk), np.uint8))
            ret[kk] = float((op > 0).sum() / max(1, n_ink))
        dt = cv2.distanceTransform(ink, cv2.DIST_L2, 3)
        ridge = (dt > 0) & (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8)))
        sw = float(np.median(2 * dt[ridge])) if ridge.sum() else float('nan')
        th = text_heights(ink)
        n_text = int(len(th)); th_med = float(np.median(th)) if n_text else float('nan')
        # text-component retention under 3x3 opening (pixels of text-like comps that survive)
        # dHash 64 bit
        tiny = cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA).astype(int)
        dh = ''.join('1' if v else '0' for v in (tiny[:, 1:] > tiny[:, :-1]).ravel())
        return dict(source=s, file=f, w=W, h=H, long=L, chroma_p99=chroma_p99, frac_c15=frac_c15, dom_hue=dom, off_frac=off_frac,
                    mode_central=mode, inverted=int(inverted), p2=p2, p50=p50, p98=p98, range_contrast=(p98 - p2) / 255,
                    sigma_mad=sigma_mad, flat_std=flat_std, ink_frac=n_ink / (H * W), retain_open2=ret[2], retain_open3=ret[3],
                    stroke_w=sw, n_text=n_text, text_h_med=th_med, text_h_med_1568=th_med * min(1.0, 1568 / L), dhash=dh, error='')
    except Exception as e:
        return dict(source=s, file=f, error=repr(e))

if __name__ == '__main__':
    # self-check of the text proxy on a synthetic line of 12 px text
    im = np.full((200, 600), 255, np.uint8); cv2.putText(im, 'KITCHEN 12 BATH 7', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 1)
    m = cv2.adaptiveThreshold(im, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 12)
    t = text_heights(m); assert len(t) >= 8 and 7 <= np.median(t) <= 14, (len(t), np.median(t) if len(t) else None)
    jobs = [(s, f) for s in ('europeana', 'finna', 'habs', 'wikimedia') for f in sorted(os.listdir(os.path.join(D, s))) if f.lower().endswith('.jpg')]
    with Pool(max(2, (os.cpu_count() or 4) - 1)) as pool:
        rows = pool.map(one, jobs, chunksize=2)
    keys = list(rows[0].keys()) if not rows[0]['error'] else sorted({k for r in rows for k in r})
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in rows[0], list(rows[0]).index(k) if k in rows[0] else 0))
    with open(OUT, 'w', newline='') as fh:
        wr = csv.DictWriter(fh, keys); wr.writeheader(); wr.writerows(rows)
    print('done', len(rows), 'errors', sum(1 for r in rows if r.get('error')))

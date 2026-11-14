"""Per-page profile of every opening_design PDF: size, vector/raster content, text layer, rotated text,
largest-font text in the title-block strip (sheet number candidates).
Usage: python -I pdf_profile.py <dataset_dir> <work_dir>"""
import sys, os, time, re, collections
import numpy as np
import pymupdf
import pandas as pd

D, W = sys.argv[1], sys.argv[2]
root = os.path.join(D, "data", "opening_design")

# (name, short, long) in inches
SIZES = [("Letter", 8.5, 11), ("Legal", 8.5, 14), ("ANSI B (11x17)", 11, 17), ("ARCH A", 9, 12),
         ("ARCH B", 12, 18), ("ARCH C", 18, 24), ("ANSI C", 17, 22), ("ANSI D (22x34)", 22, 34),
         ("ARCH D (24x36)", 24, 36), ("ARCH E1 (30x42)", 30, 42), ("ANSI E (34x44)", 34, 44), ("ARCH E (36x48)", 36, 48),
         ("A4", 8.27, 11.69), ("A3", 11.69, 16.54), ("A1", 23.39, 33.11), ("A0", 33.11, 46.81)]
SHEET_RE = re.compile(r"^[A-Z]{1,2}\d?-?\d{2,3}(?:[.-][A-Z0-9]{1,2})?$")


def sheet_size(w, h):
    s, l = sorted((w / 72, h / 72))
    for name, a, b in SIZES:
        if abs(s - a) <= 0.25 and abs(l - b) <= 0.25:
            return name
    return f"custom {s:.1f}x{l:.1f}"


rows = []
for dp, _, fs in sorted(os.walk(root)):
    for f in sorted(fs):
        if not f.lower().endswith(".pdf"):
            continue
        full = os.path.join(dp, f)
        rel = os.path.relpath(full, root)
        try:
            doc = pymupdf.open(full)
        except Exception as e:  # some files in this source are not valid PDFs
            print("OPEN FAILED", rel, type(e).__name__, e, flush=True)
            continue
        meta = doc.metadata or {}
        for pno, page in enumerate(doc):
            t0 = time.time()
            r = page.rect  # display (rotated) rect
            area = r.width * r.height
            m = page.rotation_matrix
            words = page.get_text("words")
            d = page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT)  # no image blocks: a page here has 273k image tiles
            n_lines = 0
            dirs = collections.Counter()
            spans = []
            for b in d["blocks"]:
                for ln in b.get("lines", []):
                    n_lines += 1
                    v = pymupdf.Point(ln["dir"]) * m - pymupdf.Point(0, 0) * m  # direction in display space
                    dirs[(round(v.x), round(v.y))] += 1
                    for s in ln["spans"]:
                        if s["text"].strip():
                            spans.append((s["size"], pymupdf.Rect(s["bbox"]) * m, s["text"].strip()))
            horiz = dirs.get((1, 0), 0)
            t1 = time.time()
            try:
                n_paths = len(page.get_cdrawings())
            except Exception:
                n_paths = -1
            t2 = time.time()
            imgs = page.get_image_info()
            # summed (not unioned) clipped image area; bbox rotation does not change area
            B = np.array([im["bbox"] for im in imgs]).reshape(-1, 4)
            ur = pymupdf.Rect(0, 0, page.cropbox.width, page.cropbox.height)  # unrotated page box
            w_ = np.clip(np.minimum(B[:, 2], ur.x1) - np.maximum(B[:, 0], ur.x0), 0, None)
            h_ = np.clip(np.minimum(B[:, 3], ur.y1) - np.maximum(B[:, 1], ur.y0), 0, None)
            img_cov = float((w_ * h_).sum())
            fonts = page.get_fonts()
            # title block candidates: biggest text in the right 20% or bottom 12% of the display page
            tb = [s for s in spans if s[1].x0 > r.width * 0.8 or s[1].y0 > r.height * 0.88]
            tb.sort(key=lambda s: -s[0])
            sheet_no = next((s[2] for s in tb if SHEET_RE.match(s[2].replace(" ", ""))), "")
            big = " | ".join(s[2] for s in tb[:4])
            rows.append(dict(rel=rel, page=pno + 1, n_pages=doc.page_count, w_in=round(r.width / 72, 2),
                             h_in=round(r.height / 72, 2), rotation=page.rotation, size=sheet_size(r.width, r.height),
                             n_words=len(words), n_lines=n_lines, n_nonhoriz_lines=n_lines - horiz,
                             dirs=dict(dirs), n_paths=n_paths, n_images=len(imgs), img_cov=round(min(img_cov / area, 9.99), 3),
                             n_fonts=len(fonts), n_type3=sum(1 for x in fonts if x[2] == "Type3"),
                             sheet_no=sheet_no, title_block_big_text=big[:160],
                             creator=meta.get("creator", ""), producer=meta.get("producer", ""), title=meta.get("title", "")[:120],
                             mod_date=meta.get("modDate", ""), t_text=round(t1 - t0, 2), t_paths=round(t2 - t1, 2)))
            print(f"{rel[:70]:70} p{pno+1} words={len(words)} paths={n_paths} t={t2-t0:.1f}s", flush=True)
        doc.close()

df = pd.DataFrame(rows)


def kind(r):
    if r.img_cov > 0.8 and r.n_paths < 200:
        return "raster (scan/image)"
    if r.img_cov > 0.25:
        return "mixed vector+raster"
    return "vector"


df["kind"] = df.apply(kind, axis=1)
df["text_layer"] = pd.cut(df.n_words, [-1, 0, 20, 10**9], labels=["none", "1-20 words", ">20 words"]).astype(str)
df.to_csv(os.path.join(W, "pdf_pages.csv"), index=False)

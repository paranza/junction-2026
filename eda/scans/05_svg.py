"""Inspect the wikimedia SVGs: element census, vector text, embedded rasters, size; render with PyMuPDF and
compare with the same-name JPG. Read-only on the dataset. Outputs: svg_summary.csv, svg_text.csv, svg_render/*.png"""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pathlib, re, collections, json
import xml.etree.ElementTree as ET
import numpy as np, pandas as pd, pymupdf, cv2
from PIL import Image

DS = pathlib.Path(_DATA + "/data/wikimedia")
OUT = pathlib.Path(__file__).parent
(OUT / "svg_render").mkdir(exist_ok=True)
rows, texts = [], []
for svg in sorted(DS.glob("*.svg")):
    root = ET.parse(svg).getroot()
    tags = collections.Counter(el.tag.split("}")[-1] for el in root.iter())
    imgs = [el for el in root.iter() if el.tag.split("}")[-1] == "image"]
    hrefs = [el.get("{http://www.w3.org/1999/xlink}href") or el.get("href") or "" for el in imgs]
    text_els = [el for el in root.iter() if el.tag.split("}")[-1] == "text"]
    strings = ["".join(el.itertext()).strip() for el in text_els]
    strings = [s for s in strings if s]
    raw = svg.read_text(encoding="utf-8", errors="replace")
    fonts = sorted(set(re.findall(r"font-family[:=]\s*['\"]?([^;'\"]+)", raw)))
    path_d = sum(len(el.get("d", "")) for el in root.iter() if el.tag.split("}")[-1] == "path")
    # render with MuPDF (it supports SVG) and get positioned text
    doc = pymupdf.open(svg)
    page = doc[0]
    words = page.get_text("words")
    zoom = 2000 / max(page.rect.width, page.rect.height)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    out_png = OUT / "svg_render" / (svg.stem + "_svg.png")
    pix.save(out_png)
    # compare with JPG twin: aspect ratio and a coarse structural similarity (edge overlap after resize)
    jpg = DS / (svg.stem + ".jpg")
    cmp = {}
    if jpg.exists():
        j = Image.open(jpg)
        cmp["jpg_w"], cmp["jpg_h"] = j.size
        cmp["jpg_aspect"] = round(j.width / j.height, 4)
        a = np.asarray(Image.open(out_png).convert("L").resize((400, round(400 * pix.height / pix.width))))
        b = np.asarray(j.convert("L").resize((a.shape[1], a.shape[0])))
        cmp["gray_corr_400px"] = round(float(np.corrcoef(a.ravel().astype(float), b.ravel().astype(float))[0, 1]), 3)
    rows.append({"file": svg.name, "bytes": svg.stat().st_size, "width_attr": root.get("width"), "height_attr": root.get("height"),
                 "viewBox": root.get("viewBox"), "render_aspect": round(page.rect.width / page.rect.height, 4),
                 "n_elements": sum(tags.values()), "n_path": tags.get("path", 0), "path_d_chars": path_d,
                 "n_line": tags.get("line", 0), "n_rect": tags.get("rect", 0), "n_polygon": tags.get("polygon", 0) + tags.get("polyline", 0),
                 "n_circle_ellipse": tags.get("circle", 0) + tags.get("ellipse", 0), "n_g": tags.get("g", 0), "n_use": tags.get("use", 0),
                 "n_text": len(text_els), "n_text_nonempty": len(strings), "mupdf_words": len(words),
                 "n_image": len(imgs), "image_hrefs": "; ".join(h[:40] for h in hrefs), "fonts": "; ".join(fonts)[:120],
                 "generator": (re.search(r"<!--\s*(Created with [^>]*?|Generator: [^>]*?)-->", raw) or [None, ""])[1].strip()[:60],
                 "top_tags": json.dumps(tags.most_common(8)), **cmp})
    for s in strings:
        texts.append({"file": svg.name, "text": s})
pd.DataFrame(rows).to_csv(OUT / "svg_summary.csv", index=False)
pd.DataFrame(texts).to_csv(OUT / "svg_text.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_colwidth", 60)
print(pd.DataFrame(rows).T)
print(pd.DataFrame(texts).groupby("file").text.apply(lambda s: " | ".join(s)[:600]).to_string())

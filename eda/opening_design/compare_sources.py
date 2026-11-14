"""Light comparison of PDF properties: opening_design (all pages) vs the other PDF sources (seeded sample).
Usage: python -I compare_sources.py <dataset_dir> <work_dir>"""
import sys, os, random
import pymupdf
import pandas as pd

D, W = sys.argv[1], sys.argv[2]
inv = pd.read_csv(os.path.join(W, "..", "inventory.csv"))
pdfs = inv[(inv.ext == "pdf") & (inv.source != "opening_design")]
rows = []
for src, g in pdfs.groupby("source"):
    paths = sorted(g.path)
    random.Random(0).shuffle(paths)
    for rel in paths[:15]:
        doc = pymupdf.open(os.path.join(D, rel))
        p = doc[0]
        rows.append(dict(source=src, rel=rel, pages=doc.page_count, w_in=round(p.rect.width / 72, 1),
                         h_in=round(p.rect.height / 72, 1), rotation=p.rotation, n_words=len(p.get_text("words")),
                         n_paths=len(p.get_cdrawings()), n_images=len(p.get_image_info()),
                         creator=(doc.metadata or {}).get("creator", ""), producer=(doc.metadata or {}).get("producer", "")))
o = pd.read_csv(os.path.join(W, "pdf_pages.csv"))
o["source"] = "opening_design"
cols = ["pages", "w_in", "h_in", "n_words", "n_paths", "n_images"]
df = pd.DataFrame(rows)
o2 = o.rename(columns={"n_pages": "pages"})
allp = pd.concat([df, o2[["source", "rel"] + cols + ["rotation", "creator", "producer"]]])
allp.to_csv(os.path.join(W, "compare_sources.csv"), index=False)
summ = allp.groupby("source").agg(files_or_pages=("rel", "size"), median_words=("n_words", "median"),
                                  median_paths=("n_paths", "median"), share_rotated=("rotation", lambda s: (s != 0).mean()),
                                  median_long_side_in=("w_in", lambda s: 0), distinct_sizes=("w_in", "nunique"))
summ["median_long_side_in"] = allp.assign(l=allp[["w_in", "h_in"]].max(axis=1)).groupby("source").l.median()
print(summ.to_string())
for src, g in df.groupby("source"):
    print(src, "creators:", g.creator.value_counts().to_dict(), "| producers:", g.producer.value_counts().to_dict())

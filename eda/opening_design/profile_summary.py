"""Summarize pdf_pages.csv: sizes, vector/raster, text layer, rotation, producers, title-block sheet ids,
and how often one sheet id appears in several files/pages of the same project (revision risk).
Usage: python -I profile_summary.py <work_dir>"""
import sys, os, re, collections
import pandas as pd

W = sys.argv[1]
df = pd.read_csv(os.path.join(W, "pdf_pages.csv"), keep_default_na=False)
df["project"] = df.rel.str.split("/").str[0]
files = df.drop_duplicates("rel")
print(f"PDF files {len(files)} | pages {len(df)} | multi-page files {(files.n_pages > 1).sum()} | max pages {files.n_pages.max()}")
print("pages per file:", files.n_pages.value_counts().sort_index().to_dict())
print("\nsheet size (pages):", df["size"].value_counts().to_dict())
print("page /Rotate (pages):", df.rotation.value_counts().to_dict())
print("\ncontent kind (pages):", df.kind.value_counts().to_dict())
print("text layer (pages):", df.text_layer.value_counts().to_dict())
print("words/page: median", df.n_words.median(), "| p10", df.n_words.quantile(0.1), "| p90", df.n_words.quantile(0.9))
print("paths/page: median", df.n_paths.median(), "| max", df.n_paths.max())
print("pages with >1000 image objects:", (df.n_images > 1000).sum(), "| max images on a page:", df.n_images.max())
nh = df.n_nonhoriz_lines.sum() / max(df.n_lines.sum(), 1)
print(f"text lines not horizontal after applying /Rotate: {df.n_nonhoriz_lines.sum()} of {df.n_lines.sum()} ({nh:.1%});"
      f" pages with any: {(df.n_nonhoriz_lines > 0).sum()}")
print("Type3-font pages:", (df.n_type3 > 0).sum())
print("\ncreator (files):", files.creator.value_counts().to_dict())
print("producer (files):", files.producer.value_counts().to_dict())
print("slowest pages (text+paths seconds):")
print(df.assign(t=df.t_text + df.t_paths).nlargest(5, "t")[["rel", "page", "t", "n_images", "n_paths"]].to_string())

# raster / no-text pages
print("\npages with no text layer:")
print(df[df.n_words == 0][["rel", "page", "size", "kind", "n_images", "img_cov"]].to_string())

# title-block sheet ids
df["sheet"] = df.sheet_no.str.replace(r"[\s.\-]", "", regex=True).str.upper()
has = df[df.sheet != ""]
print(f"\npages with a sheet number found in the title-block strip: {len(has)} of {len(df)}")
g = has.groupby(["project", "sheet"])
multi = {k: v for k, v in g if v.rel.nunique() > 1}
print(f"distinct (project, sheet) {g.ngroups}; sheets present in >1 file: {len(multi)}; "
      f"pages belonging to such sheets: {sum(len(v) for v in multi.values())} of {len(has)}")
for (p, s), v in sorted(multi.items()):
    print(f"   {p} {s}: " + " || ".join(f"{r.rel.split('/')[-2][:40]} p{r.page}" for r in v.itertuples()))
missing = df[df.sheet == ""][["rel", "page", "title_block_big_text"]]
print("\npages without a detected sheet number:", len(missing))
print(missing.to_string(max_colwidth=90))

"""Generalization probe: run the generic ruled-table finder (tables_auto) over every PDF page of the source
and record how many tables it finds and their titles. No per-sheet tuning.
Usage: python -I tables_scan.py <dataset_dir> <work_dir>"""
import sys, os, time
import pymupdf
import pandas as pd

D, W = sys.argv[1], sys.argv[2]
sys.path.insert(0, W)
import tables_auto  # noqa: E402

root = os.path.join(D, "data", "opening_design")
rows = []
for dp, _, fs in sorted(os.walk(root)):
    for f in sorted(fs):
        if not f.lower().endswith(".pdf"):
            continue
        rel = os.path.relpath(os.path.join(dp, f), root)
        doc = pymupdf.open(os.path.join(dp, f))
        for pno, page in enumerate(doc):
            t0 = time.time()
            if len(page.get_text("words")) < 20:
                rows.append(dict(rel=rel, page=pno + 1, n_tables=0, titles="(no text layer)", t=0))
                continue
            try:
                ts = tables_auto.find_tables(page)
            except Exception as e:
                rows.append(dict(rel=rel, page=pno + 1, n_tables=-1, titles=f"ERROR {type(e).__name__}", t=0))
                continue
            rows.append(dict(rel=rel, page=pno + 1, n_tables=len(ts), t=round(time.time() - t0, 1),
                             titles=" || ".join(f"{x['title'][:40]} [{len(x['rows'])}x{len(x['rows'][0])}]" for x in ts)))
            print(f"{rel[:60]:60} p{pno+1} tables={len(ts)} t={time.time()-t0:.1f}s", flush=True)
df = pd.DataFrame(rows)
df.to_csv(os.path.join(W, "tables_scan.csv"), index=False)
print("pages", len(df), "| pages with >=1 table", (df.n_tables > 0).sum(), "| tables", df.n_tables.clip(lower=0).sum())

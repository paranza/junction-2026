"""Is the text layer usable? Share of extracted characters that are control/private-use/replacement chars
(fonts without a ToUnicode map give such garbage), plus PDF annotations (markup text that lives outside page text).
Usage: python -I garble_check.py <dataset_dir> <work_dir>"""
import sys, os, unicodedata
import pymupdf
import pandas as pd

D, W = sys.argv[1], sys.argv[2]
root = os.path.join(D, "data", "opening_design")
rows = []
for dp, _, fs in sorted(os.walk(root)):
    for f in sorted(fs):
        if not f.lower().endswith(".pdf"):
            continue
        try:
            doc = pymupdf.open(os.path.join(dp, f))
        except Exception as e:  # some files in this source are not valid PDFs
            print("OPEN FAILED", f, type(e).__name__, flush=True)
            continue
        for pno, page in enumerate(doc):
            t = "".join(page.get_text().split())
            bad = sum(1 for ch in t if unicodedata.category(ch) in ("Cc", "Co", "Cn") or ch == "�")
            ann = [(a.type[1], (a.info.get("content") or "").strip()) for a in page.annots()]
            rows.append(dict(rel=os.path.relpath(os.path.join(dp, f), root), page=pno + 1, chars=len(t),
                             bad_share=round(bad / len(t), 3) if t else None, n_annots=len(ann),
                             n_annots_with_text=sum(1 for _, c in ann if c), annot_types=",".join(sorted({a for a, _ in ann}))))
df = pd.DataFrame(rows)
df.to_csv(os.path.join(W, "text_quality.csv"), index=False)
print("pages", len(df), "| pages with text", (df.chars > 0).sum(),
      "| pages whose text is >20% control/unmapped chars:", (df.bad_share > 0.2).sum())
print(df[df.bad_share > 0.2][["rel", "page", "chars", "bad_share"]].to_string())
print("\npages with annotations:", (df.n_annots > 0).sum(), "| total annots:", df.n_annots.sum(),
      "| annots carrying text:", df.n_annots_with_text.sum())
print(df[df.n_annots > 0][["rel", "page", "n_annots", "n_annots_with_text", "annot_types"]].to_string(max_colwidth=80))

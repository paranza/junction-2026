import sys, pymupdf
src, dst = sys.argv[1], sys.argv[2]
doc = pymupdf.open(src)
with open(dst, "w") as f:
    for i, p in enumerate(doc, 1):
        f.write(f"\n===== PAGE {i} =====\n")
        f.write(p.get_text())
print(src, doc.page_count)

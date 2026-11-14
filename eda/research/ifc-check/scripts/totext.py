# Convert downloaded html/pdf to plain text for grepping.
import sys, html, re, pathlib
from html.parser import HTMLParser
class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.out=[]; s.skip=0
    def handle_starttag(s,t,a):
        if t in ("script","style","svg","noscript"): s.skip+=1
        if t in ("p","div","br","li","tr","h1","h2","h3","h4","h5","dt","dd","pre","section","td","th"): s.out.append("\n")
    def handle_endtag(s,t):
        if t in ("script","style","svg","noscript"): s.skip=max(0,s.skip-1)
    def handle_data(s,d):
        if not s.skip: s.out.append(d)
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
dst.mkdir(exist_ok=True)
for f in src.iterdir():
    if f.suffix == ".pdf":
        import pymupdf
        doc = pymupdf.open(f)
        txt = "\n".join(f"=== PAGE {i+1} ===\n" + p.get_text() for i, p in enumerate(doc))
    else:
        p = P(); p.feed(f.read_text(errors="replace")); txt = "".join(p.out)
        txt = re.sub(r"\n\s*\n+", "\n\n", txt)
    (dst / (f.stem + ".txt")).write_text(txt)
    print(f.name, len(txt))

import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import pymupdf, collections, sys
D=_ROOT + "/eda/ifc_models/verify/files/"
for fn in ["bsc-esplanades_1807-ep-ar-v18_plan-04-4-korrus.pdf","bsc-molio_molio-with-uris_plan-02-klder.pdf","kit-fzk-haus_ac20-fzk-haus_plan-02-dachgeschoss.pdf"]:
    doc=pymupdf.open(D+fn); print("=====",fn,"pages",len(doc),"meta",doc.metadata)
    p=doc[0]; print("page size pt",p.rect, "mm", p.rect.width*25.4/72, p.rect.height*25.4/72)
    words=p.get_text("words"); print("n words",len(words))
    spans=[s for b in p.get_text("dict")["blocks"] if b["type"]==0 for l in b["lines"] for s in l["spans"]]
    print("font sizes",collections.Counter(round(s["size"],2) for s in spans).most_common(6))
    # title block: text with biggest y or font size not equal to label size
    lab=collections.Counter(round(s["size"],2) for s in spans).most_common(1)[0][0]
    other=[s["text"] for s in spans if round(s["size"],2)!=lab]
    print("non-label text:",other[:40])
    print("label sample:",[s["text"] for s in spans if round(s["size"],2)==lab][:30])
    dr=p.get_drawings(); print("n drawings",len(dr))
    fills=collections.Counter((tuple(round(c,3) for c in d["fill"]) if d.get("fill") else None, d["type"]) for d in dr)
    print("fill/type",fills.most_common(12))
    items=collections.Counter(it[0] for d in dr for it in d["items"]); print("item kinds",items)

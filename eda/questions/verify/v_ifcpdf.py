import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, os, re, collections
import pymupdf
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
for fn in ["bsc-esplanades_1807-ep-ar-v18_plan-04-4-korrus.pdf", "bsc-molio_molio-with-uris_plan-02-klder.pdf", "kit-fzk-haus_ac20-fzk-haus_plan-02-dachgeschoss.pdf"]:
    p = "data/ifc_models/" + fn
    d = pymupdf.open(os.path.join(DS, p)); pg = d[0]
    t = pg.get_text("text"); lines = [l.strip() for l in t.split("\n") if l.strip()]
    print("==", fn, "pages", len(d), "chars", len(t), "m² tokens", t.count("m²"), "m2 tokens", len(re.findall(r"\bm2\b", t)))
    print("   first lines:", lines[:25])
    # room names asked on this PDF (English)
    names = [re.match(r"What is the net floor area of the room '(.*)' on '(.*)', in m²\?$", rows[i]["question"]) for i in range(len(rows)) if rows[i]["path"] == p and langs[i] == "en"]
    names = [m.groups() for m in names if m]
    full = sum(1 for n, s in names if n in t); 
    # match name parts: LongName and (Name)
    parts = sum(1 for n, s in names if re.match(r"(.*) \((.*)\)$", n) and all(x in t for x in re.match(r"(.*) \((.*)\)$", n).groups()))
    st = sum(1 for n, s in names if s in t)
    print("   asked rooms", len(names), "full 'LongName (Name)' string in text", full, "both parts in text", parts, "storey name in text", st)
    pix = pg.get_pixmap(dpi=50); pix.save(os.path.join(OUT, fn.replace(".pdf", "_small.png"))); print("   rendered", pix.width, pix.height)

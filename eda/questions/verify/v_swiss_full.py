import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Whole-page exact label counts (no crop), only on files that are locally materialized (iCloud).
import json, os, re, collections, sys
import pymupdf
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
DATALESS = 0x40000000
files = sorted(set(r["path"] for r in rows if r["path"].startswith("data/swiss_dwellings/")))
local = [f for f in files if not (os.stat(os.path.join(DS, f)).st_flags & DATALESS)]
print("local swiss PDFs", len(local), "of", len(files))
tal = collections.Counter(); bad = []
for f in local:
    pg = pymupdf.open(os.path.join(DS, f))[0]
    spans = [s["text"].strip() for b in pg.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"] if s["text"].strip()]
    for i, r in enumerate(rows):
        if r["path"] != f or langs[i] != "en": continue
        m = re.match(r"How many rooms labelled '(.*)' are there on this floor\?$", r["question"])
        if m:
            n = spans.count(m.group(1)); tal["label ok" if n == r["answer"] else "label BAD"] += 1
            if n != r["answer"]: bad.append((f, m.group(1), n, r["answer"]))
        if r["question"].startswith("How many apartments"):
            n = sum(1 for s in spans if re.fullmatch(r"(Whg\.|App\.)\s*\S+", s)); tal["apt ok" if n == r["answer"] else "apt BAD"] += 1
print(dict(tal)); print(bad)

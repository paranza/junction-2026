import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Reproduce A-801 schedule answers from the PDF text layer (opening_design answerability).
import re, json, os
import pymupdf
DS = _DATA + ""
P = "data/opening_design/Sports_Complex/Sheets - Current Set/A-801 - Door and Finish Schedules & Wall Types.pdf"
pg = pymupdf.open(os.path.join(DS, P))[0]
words = pg.get_text("words")  # x0,y0,x1,y1,word,block,line,wordno (unrotated page coords)
lines = pg.get_text("text").split("\n")
# door schedule: rows start with a door number token; take tokens until next door number
s = lines.index("KEYNOTE - DOOR SCHEDULE") if "KEYNOTE - DOOR SCHEDULE" in lines else len(lines)
seg = lines[:s]
idx = [k for k, t in enumerate(seg) if re.fullmatch(r"1[0-3]\d\.[A-Z]\d?", t)]
rowsd = [seg[a:b] for a, b in zip(idx, idx[1:] + [s])]
def has(r, tok): return tok in r
doors = [r for r in rowsd]
pred = {
 "n_doors": len(doors),
 "A1": sum(r[5:].count("A1") > 0 for r in doors), "A2": sum("A2" in r[5:] for r in doors), "B1": sum("B1" in r[5:] for r in doors),
 "B2": sum("B2" in r[5:] for r in doors), "B3": sum("B3" in r[5:] for r in doors), "C1": sum("C1" in r[5:] for r in doors),
 "WD-1": sum("WD-1" in r for r in doors), "STL-1": sum("STL-1" in r for r in doors),
 "AL frame": sum(any(t in ("AL-1", "AL-2") for t in r[6:9]) for r in doors),
 "3'-0\" wide": sum(r[3] == "3' - 0\"" for r in doors), "7'-0\" high": sum(r[4] == "7' - 0\"" for r in doors),
 "room118": sum(r[2] == "118" for r in doors), "room128": sum(r[2] == "128" for r in doors),
}
for r in doors: print("|".join(r))
print(pred)

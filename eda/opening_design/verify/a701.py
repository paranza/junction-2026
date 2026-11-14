import sys, re; sys.path.insert(0,".")
from mytab import *
pg,W,V,H=load("A701")
txt=pg.get_text().upper()
print("WATER CLOSET occurrences (text):",txt.count("WATER CLOSET"), "search_for hits:",len(pg.search_for("WATER CLOSET")))
for k in ("LAVATORY","SHOWER","URINAL","FOUNTAIN","LAV"): print(k,txt.count(k))
# view titles: lines with a two-char tag like 6A next to a title
lines=pg.get_text("dict")["blocks"]
for w in W:
    if re.fullmatch(r"\d[A-F]",w[4]): print("tag",w[4],[round(v) for v in w[:4]])
for w in W:
    if w[4].upper() in ("RESTROOMS","RESTROOM","SHOWER"): print("title-word",w[4],[round(v) for v in w[:4]])

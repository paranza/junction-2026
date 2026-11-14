"""Drawing-type tags and years from catalogue titles (LICENSE.md), multilingual keyword match. Multi-label.
Titles are catalogue metadata, not the drawing's own text (a Finnish title can describe a Swedish-labelled sheet).
Output: titles_tagged.csv and printed per-source counts."""
import re, pathlib
import pandas as pd

OUT = pathlib.Path(__file__).parent
d = pd.read_csv(OUT / "meta.csv")
d["t"] = d["title"].astype(str).str.lower()
KW = {
    "site_plan": r"site plan|situations?plan|situasjonsplan|lageplan|asemapiir|situatie|situační|situacijos|location map|planting plan|übersicht|planimetria generale|garden|puutarha",
    "floor_plan": r"floor plan|ground ?plan|grundriss|grundriß|plattegrond|planta|pianta|pohjapiir|pohja[-, ]|pohjat|rzut|tlocrt|půdorys|pôdorys|alaprajz|osnova|plànol|grunntegning|grunnplan|grundbyggnad|floorplan|\bplan\b|plano|plan du|kellarikerros|kerros|vån|level|kátoψη|κάτοψη|uppdráttur|plaan|dispositions|planul|plan of|\bplans\b",
    "section": r"section|schnitt|doorsnede|sección|seccion|sezione|spaccato|leikkaus|skärning|genomskärning|przekr|presjek|coupe|ristlõige|τομή|profil|cross[- ]?section|lines\b",
    "elevation": r"elevation|aufriss|aufriß|ansicht|fassade|fasad|gevel|alzado|alçado|prospect|julkisivu|elewacja|pročelje|façade|élévation|homlokzat|όψη|άποψη|fațada|elevation",
    "detail": r"detail|detalj|jamb|newel|kalust|ovi\b|ikkunaluuk|kattoikkuna|chord|post configuration|panel|fountain|rustika|balkendecke|kalkki|kynttilänjalka|alttaritaulu|virsinumerot|sisäseinä|ashtray|table|altaar|autel|liekki|tuolit|baluster|railing",
    "non_drawing_suspect": r"brain|anatom|daguerreotyp|noodikogu|ludność|képei|photo|interior of|lärbok|black's guide|rambles|engetrim|esittelemässä|compositional analysis",
}
for k, rx in KW.items():
    d[k] = d["t"].str.contains(rx, regex=True)
d["untyped"] = ~d[list(KW)].any(axis=1)
yrs = d["title"].astype(str).str.findall(r"(?<!\d)(1[5-9]\d\d|20[0-2]\d)(?!\d)")
d["year"] = yrs.map(lambda v: int(v[0]) if v else None)
d.to_csv(OUT / "titles_tagged.csv", index=False)
print(d.groupby("source_name")[list(KW) + ["untyped"]].sum().to_string())
print("\nyears found per source:")
print(d.groupby("source_name").year.agg(["count", "min", "median", "max"]).to_string())
print("\nuntyped titles:")
for s, t in zip(d[d.untyped].source_name, d[d.untyped].title):
    print(" ", s, "|", str(t)[:110])
print("\nnon-drawing suspects:")
for s, f, t in zip(d[d.non_drawing_suspect].source_name, d[d.non_drawing_suspect].file, d[d.non_drawing_suspect].title):
    print(" ", s, f[:40], "|", str(t)[:100])

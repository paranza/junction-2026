import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Can the SVG twin of an IFC-rendered plan answer the storey questions without the IFC?
import json, os, re, sys, collections, statistics
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
svgp = sys.argv[1]; pdfp = svgp.replace(".svg", ".pdf")
root = ET.parse(os.path.join(DS, svgp)).getroot()
NS = "{http://www.w3.org/2000/svg}"
cls = collections.Counter(); spaces = {}
def parse_path(d):
    pts = [(float(x), float(y)) for x, y in re.findall(r"(-?[\d.]+)[ ,](-?[\d.]+)", d)]
    return pts
for g in root.iter(NS + "g"):
    c = g.get("class")
    if not c: continue
    cls[c] += 1
    if c == "IfcSpace":
        polys = [Polygon(parse_path(p.get("d"))) for p in g.iter(NS + "path")]
        spaces[g.get("data-name")] = sum(p.area for p in polys if p.is_valid) if polys else None
print("classes", dict(cls))
# compare with room-area answers asked on the PDF twin
qa = []
for i, r in enumerate(rows):
    if r["path"] == pdfp and langs[i] == "en":
        m = re.match(r"What is the net floor area of the room '(.*) \((.*)\)' on '(.*)', in m²\?$", r["question"])
        if m and m.group(2) in spaces: qa.append((m.group(2), spaces[m.group(2)], r["answer"]))
ratios = [a / s for _, s, a in qa if s]
k = statistics.median(ratios)
print("rooms matched", len(qa), "median answer/svg-area ratio", k, "-> implied scale 1:", round((k * 1e6) ** 0.5))
ok = sum(1 for _, s, a in qa if abs(s * k - a) <= 0.02 * a)
print("room areas within 2% using one fitted scale", ok, "/", len(qa))
sc = round((k * 1e6) ** 0.5)
ok2 = sum(1 for _, s, a in qa if abs(s * (sc / 1000) ** 2 - a) <= 0.02 * a)
print("room areas within 2% using nominal scale 1:%d" % sc, ok2, "/", len(qa))

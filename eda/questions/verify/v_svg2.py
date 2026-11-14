import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import json, os, re, sys, collections
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
svgp = sys.argv[1]; pdfp = svgp.replace(".svg", ".pdf"); scale = float(sys.argv[2])
root = ET.parse(os.path.join(DS, svgp)).getroot(); NS = "{http://www.w3.org/2000/svg}"
def signed(pts):
    return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))
def area_of_group(g):
    tot = 0.0; n = 0; subs = []
    for p in g.iter(NS + "path"):
        for sub in re.split(r"(?=M)", p.get("d")):
            pts = [(float(x), float(y)) for x, y in re.findall(r"(-?[\d.]+)[ ,](-?[\d.]+)", sub)]
            if len(pts) >= 3: subs.append(signed(pts)); n += 1
    # even-odd style: outer rings and holes have opposite orientation in most exporters
    return abs(sum(subs)), sum(abs(s) for s in subs), n
spaces = {g.get("data-name"): area_of_group(g) for g in root.iter(NS + "g") if g.get("class") == "IfcSpace"}
qa = []
for i, r in enumerate(rows):
    if r["path"] == pdfp and langs[i] == "en":
        m = re.match(r"What is the net floor area of the room '(.*) \((.*)\)' on '(.*)', in m²\?$", r["question"])
        if m and m.group(2) in spaces: qa.append((m.group(2), spaces[m.group(2)], r["answer"]))
k = (scale / 1000.0) ** 2
ok_signed = sum(1 for _, s, a in qa if abs(s[0] * k - a) <= 0.02 * a)
ok_abs = sum(1 for _, s, a in qa if abs(s[1] * k - a) <= 0.02 * a)
print("rooms", len(qa), "within 2% signed-sum", ok_signed, " abs-sum", ok_abs, " multi-subpath spaces", sum(1 for _, s, _ in qa if s[2] > 1))
for nm, s, a in qa:
    if abs(s[0] * k - a) > 0.02 * a: print("  miss", nm, round(s[0] * k, 2), round(s[1] * k, 2), a, "subpaths", s[2])

import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Count how many PDF-asked ifc_models questions are answerable from the SVG twin alone.
import json, os, re, sys, collections
import xml.etree.ElementTree as ET
DS = _DATA + ""
OUT = _ROOT + "/eda/questions/verify"
rows = [json.loads(l) for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf-8")]
langs = json.load(open(os.path.join(OUT, "langs.json")))
NS = "{http://www.w3.org/2000/svg}"
def signed(pts): return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))
tally = collections.Counter()
for stem in ["bsc-esplanades_1807-ep-ar-v18_plan-04-4-korrus", "bsc-molio_molio-with-uris_plan-02-klder", "kit-fzk-haus_ac20-fzk-haus_plan-02-dachgeschoss"]:
    root = ET.parse(os.path.join(DS, "data/ifc_models", stem + ".svg")).getroot()
    cls = collections.Counter(); area = {}
    for g in root.iter(NS + "g"):
        c = g.get("class")
        if not c: continue
        cls[c] += 1
        if c == "IfcSpace":
            a = 0.0
            for p in g.iter(NS + "path"):
                for sub in re.split(r"(?=M)", p.get("d")):
                    pts = [(float(x), float(y)) for x, y in re.findall(r"(-?[\d.]+)[ ,](-?[\d.]+)", sub)]
                    if len(pts) >= 3: a += signed(pts)
            area[g.get("data-name")] = abs(a) * 0.01  # 1:100 paper mm -> m2
    pdf = "data/ifc_models/" + stem + ".pdf"
    for i, r in enumerate(rows):
        if r["path"] != pdf or langs[i] != "en": continue
        q = r["question"]; a = r["answer"]; pred = None
        m = re.match(r"What is the net floor area of the room '(.*) \((.*)\)' on", q)
        if m: pred = area.get(m.group(2))
        elif "total net floor area of all rooms" in q: pred = sum(area.values())
        else:
            m = re.match(r"How many (doors|walls|columns|stairs|windows|rooms \(spaces\)) are shown on the floor plan", q)
            if m:
                k = m.group(1)
                pred = {"doors": cls["IfcDoor"], "walls": cls["IfcWall"] + cls["IfcWallStandardCase"], "columns": cls["IfcColumn"],
                        "stairs": cls["IfcStair"] or cls["IfcStairFlight"], "windows": cls["IfcWindow"], "rooms (spaces)": cls["IfcSpace"]}[k]
        if pred is None: tally[(stem[:12], "not answerable from SVG")] += 1; continue
        good = pred == a if r["type"] == "count" else abs(pred - a) <= 0.02 * a
        tally[(stem[:12], "SVG correct" if good else "SVG WRONG")] += 1
        if not good: print("WRONG", stem[:12], q[:80], pred, a)
for k, v in sorted(tally.items()): print(v, k)

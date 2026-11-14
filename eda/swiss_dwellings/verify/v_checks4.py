import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Generalization probes: (1) PDF style census across files (how many styles are rare -> unseen-style risk),
# (2) label / unit-tag vocabulary singletons, (3) which file extensions questions target, per source.
import sys, os, collections, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_pdf, v_local, v_eval
import pymupdf

stems = v_local.stems("pdf")
style_files = collections.defaultdict(set); style_n = collections.Counter()
labels_files = collections.defaultdict(set); tag_prefix = collections.Counter()
for s in stems:
    m = v_pdf.load(s)
    for d in pymupdf.open(f"{v_pdf.D}/{s}.pdf")[0].get_drawings():
        if d["rect"].y0 >= m["ycut"]: continue
        k = (d["type"], v_pdf.R3(d.get("color")), v_pdf.R3(d.get("fill")), round(d.get("width") or 0, 2))
        style_files[k].add(s); style_n[k] += 1
    for r in m["rooms"]:
        labels_files[r["label"]].add(s)
    for t in m["tags"]:
        tag_prefix[re.sub(r"\s*\S+$", "", t["t"]) or t["t"]] += 1
print("plan-area path styles:", len(style_files))
for k, fs in sorted(style_files.items(), key=lambda kv: -len(kv[1])):
    print("  files %2d paths %6d  %s" % (len(fs), style_n[k], k))
f1 = [k for k, fs in labels_files.items() if len(fs) == 1]
print("distinct labels", len(labels_files), "labels on exactly one floor", len(f1), f1[:15])
print("Good-Turing P(a new floor's room has an unseen label) ~", round(sum(1 for r in f1) / sum(len(v) for v in labels_files.values()), 3))
print("unit tag prefixes", tag_prefix)

qs = [json.loads(l) for l in open(_DATA + "/questions.jsonl", encoding="utf-8")]
ext = collections.Counter((q["path"].split("/")[1], q["path"].rsplit(".", 1)[1].lower()) for q in qs)
print("question targets by source/ext:", dict(sorted(ext.items())))

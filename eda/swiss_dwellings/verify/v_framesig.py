# For each white frame with black stroke in the PDF plan area, list the primitives inside it.
import sys, os, collections, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_pdf
from shapely.geometry import Polygon, box
R3 = v_pdf.R3
def sig_of(m):
    out = []
    frames = m["frames"]
    others = [d for d in m["blacks"]] + [d for d in frames]
    for f in frames:
        fr = f["rect"]
        fb = box(fr.x0 - 0.3, fr.y0 - 0.3, fr.x1 + 0.3, fr.y1 + 0.3)
        inside = []
        for d in others:
            if d is f: continue
            r = d["rect"]
            if fb.contains(box(r.x0, r.y0, max(r.x1, r.x0 + 1e-3), max(r.y1, r.y0 + 1e-3))):
                kinds = collections.Counter(it[0] for it in d["items"])
                inside.append("%s:%s:%s" % ("F" if d in frames else "s", round(d.get("width") or 0, 2), "".join(f"{k}{v}" for k, v in sorted(kinds.items()))))
        w, h = fr.width, fr.height
        out.append(dict(sig=tuple(sorted(inside)), w=round(max(w, h) * m["mpp"], 2), h=round(min(w, h) * m["mpp"], 2), rect=tuple(round(v, 1) for v in fr),
                        nitems=len(f["items"]), width=round(f.get("width") or 0, 2)))
    return out
if __name__ == "__main__":
    tot = collections.Counter()
    ex = {}
    import v_local
    for stem in (sys.argv[1:] or v_local.stems("pdf")):
        m = v_pdf.load(stem)
        for s in sig_of(m):
            k = (s["width"], s["nitems"], s["sig"])
            tot[k] += 1; ex.setdefault(k, (stem, s["rect"], s["w"], s["h"]))
    for k, v in tot.most_common(): print(v, k, ex[k])

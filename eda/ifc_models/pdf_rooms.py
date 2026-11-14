import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Measure room polygons in the PDF vector layer (space fill colour), attach text labels, convert with the printed 1:100 scale.
import sys, re, pymupdf, shapely.geometry as sg, pandas as pd
DS = _DATA + "/data/ifc_models/"
PT_TO_M_REAL = 25.4 / 72 / 1000 * 100  # 1 pt on paper -> metres in reality at 1:100
SPACE_FILL = (0.89, 0.929, 0.969)
def rings(items):
    out, cur = [], []
    for it in items:
        if it[0] == "l":
            a, b = (it[1].x, it[1].y), (it[2].x, it[2].y)
            if cur and (abs(cur[-1][0] - a[0]) > 1e-3 or abs(cur[-1][1] - a[1]) > 1e-3):
                out.append(cur); cur = []
            if not cur: cur = [a]
            cur.append(b)
        elif it[0] == "re":
            r = it[1]; out.append([(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)])
        elif it[0] == "qu":
            q = it[1]; out.append([(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)])
        else:
            raise ValueError(it[0])
    if cur: out.append(cur)
    return [r for r in out if len(r) >= 3]
def measure(fn):
    page = pymupdf.open(DS + fn)[0]
    polys = []
    for d in page.get_drawings():
        f = d.get("fill")
        if f and all(abs(a - b) < 0.005 for a, b in zip(f, SPACE_FILL)):
            g = None
            for r in rings(d["items"]):
                p = sg.Polygon(r).buffer(0)
                g = p if g is None else g.symmetric_difference(p)  # even-odd fill rule
            polys.append(g)
    lines = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            t = "".join(s["text"] for s in l["spans"]).strip()
            x0, y0, x1, y1 = l["bbox"]
            lines.append((t, sg.Point((x0 + x1) / 2, (y0 + y1) / 2), y0))
    rows = []
    # each text line belongs to the smallest space polygon that contains it (spaces can overlap, e.g. a shaft inside a room)
    owner = {}
    for j, (t, pt, y) in enumerate(lines):
        c = [(g.area, i) for i, g in enumerate(polys) if g.contains(pt)]
        if c: owner[j] = min(c)[1]
    for i, g in enumerate(polys):
        inside = sorted([(y, t) for j, (t, pt, y) in enumerate(lines) if owner.get(j) == i])
        txt = [t for y, t in inside]
        label = f"{txt[0]} ({txt[1]})" if len(txt) == 2 else " | ".join(txt)
        rows.append({"file": fn, "poly": i, "label": label, "n_text_lines": len(txt), "area_pt2": g.area, "area_m2": g.area * PT_TO_M_REAL ** 2})
    return pd.DataFrame(rows), page
if __name__ == "__main__":
    allr = []
    for fn in ["bsc-molio_molio-with-uris_plan-02-klder.pdf", "bsc-esplanades_1807-ep-ar-v18_plan-04-4-korrus.pdf", "kit-fzk-haus_ac20-fzk-haus_plan-02-dachgeschoss.pdf"]:
        df, page = measure(fn); allr.append(df)
        # scale-bar check: distance between the '0' and '5 m' labels' left edges should be about 50 mm on paper
        ws = page.get_text("words"); z = [w for w in ws if w[4] == "0"]; m5 = [w for w in ws if w[4] == "5"]
        if z and m5: print(fn, "scale bar 0..5 label distance (mm on paper):", round((m5[-1][0] - z[-1][0]) * 25.4 / 72, 1))
        print(fn, "space polygons:", len(df), "labels with 2 lines:", (df.n_text_lines == 2).sum())
    R = pd.concat(allr); R.to_csv("pdf_room_areas.csv", index=False)
    print(R.head(20).to_string())

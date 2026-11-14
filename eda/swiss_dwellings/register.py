"""Fit DXF->PDF transform from room-number positions; match DXF entities to PDF paths by bbox."""
import sys, os, re, collections, glob
import numpy as np, ezdxf, pymupdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_model as P
DS = P.DS

def fit(name):
    msp = ezdxf.readfile(f"{DS}/{name}.dxf").modelspace()
    page = pymupdf.open(f"{DS}/{name}.pdf")[0]
    dt = {e.dxf.text: (e.dxf.insert[0], e.dxf.insert[1]) for e in msp.query("TEXT[layer=='ROOM_TEXT']") if P.NUM.fullmatch(e.dxf.text)}
    spans = [sp for b in page.get_text("dict")["blocks"] for l in b.get("lines", []) for sp in l["spans"]]
    pt = {}
    for s in spans:
        if "Bold" in s["font"] and P.NUM.fullmatch(s["text"]):
            x0, y0, x1, y1 = s["bbox"]; pt[s["text"]] = ((x0 + x1) / 2, (y0 + y1) / 2)
    keys = [k for k in dt if k in pt]
    A = np.array([[dt[k][0], 1, 0] for k in keys] + [[-dt[k][1], 0, 1] for k in keys])
    b = np.array([pt[k][0] for k in keys] + [pt[k][1] for k in keys])
    (s, tx, ty), res, *_ = np.linalg.lstsq(A, b, rcond=None)
    resid = A @ np.array([s, tx, ty]) - b
    return msp, page, s, tx, ty, np.abs(resid).max(), len(keys)

if __name__ == "__main__":
    for name in sys.argv[1:]:
        msp, page, s, tx, ty, rmax, n = fit(name)
        print(name, "scale pt/m", round(s, 4), "-> m/pt", round(1 / s, 6), "max resid pt", round(rmax, 3), "n", n)
        def tb(bb):  # dxf bbox -> pdf bbox
            (x0, y0), (x1, y1) = bb
            return (s * x0 + tx, -s * y1 + ty, s * x1 + tx, -s * y0 + ty)
        paths = page.get_drawings()
        pb = [(d["rect"].x0, d["rect"].y0, d["rect"].x1, d["rect"].y1) for d in paths]
        mapping = collections.Counter(); unmatched = collections.Counter()
        for e in msp:
            if e.dxftype() == "TEXT": continue
            try:
                from ezdxf import bbox
                eb = bbox.extents([e])
                q = tb(((eb.extmin.x, eb.extmin.y), (eb.extmax.x, eb.extmax.y)))
            except Exception as ex:
                continue
            best = None
            for i, r in enumerate(pb):
                d = max(abs(r[0] - q[0]), abs(r[1] - q[1]), abs(r[2] - q[2]), abs(r[3] - q[3]))
                if d < 0.6 and (best is None or d < best[0]): best = (d, i)
            key = (e.dxf.layer, e.dxftype(), "closed" if getattr(e, "closed", False) else f"n{len(e) if e.dxftype()=='LWPOLYLINE' else ''}")
            if best:
                d = paths[best[1]]
                mapping[(key, (d["type"], P.RGB(d.get("color")), P.RGB(d.get("fill")), round(d["width"], 3) if d.get("width") else None, "".join(sorted(set(it[0] for it in d["items"])))))] += 1
            else:
                unmatched[key] += 1
        for k, v in sorted(mapping.items(), key=lambda kv: str(kv[0])): print("  ", v, k)
        print("  unmatched:", dict(unmatched))

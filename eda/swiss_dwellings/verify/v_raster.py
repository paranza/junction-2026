# Real raster test for F15: measure asked room areas from the 150-dpi PNG by flood fill, with oracle help
# (true scale, seed at the room-number position). Upper bound for a PNG-only pipeline. Local PNGs only.
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v_pdf, v_parse, v_local
import numpy as np, cv2
from PIL import Image

pngs = set(v_local.stems("png"))
qs = [q for q in v_parse.load() if q["lang"] == "en" and q["fam"] == "area_room" and q["stem"] in pngs]
res = []
for s in sorted({q["stem"] for q in qs}):
    m = v_pdf.load(s)
    im = np.asarray(Image.open(f"{v_pdf.D}/{s}.png").convert("L"))
    k = im.shape[1] / m["page"].width  # px per pt
    m_per_px = m["mpp"] / k
    for T in (200,):
        ink = (im < T).astype(np.uint8)
        for q in [q for q in qs if q["stem"] == s]:
            r = [r for r in m["rooms"] if r["num"] == q["param"][0]][0]
            x0, y0, x1, y1 = [int(v * k) for v in r["bbox"]]
            # seed: nearest background pixel to the left/right/above/below the number box
            seed = None
            for dx in range(2, 60):
                for (sx, sy) in ((x0 - dx, (y0 + y1) // 2), (x1 + dx, (y0 + y1) // 2), ((x0 + x1) // 2, y1 + dx), ((x0 + x1) // 2, y0 - dx)):
                    if 0 <= sx < im.shape[1] and 0 <= sy < im.shape[0] and not ink[sy, sx]: seed = (sx, sy); break
                if seed: break
            mask = np.zeros((im.shape[0] + 2, im.shape[1] + 2), np.uint8)
            cv2.floodFill(ink.copy(), mask, seed, 2, flags=4 | (1 << 8) | cv2.FLOODFILL_MASK_ONLY)
            reg = mask[1:-1, 1:-1]
            # fill holes (text, fixtures fully inside the region)
            cnts, _ = cv2.findContours(reg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            filled = np.zeros_like(reg); cv2.drawContours(filled, cnts, -1, 1, thickness=cv2.FILLED)
            a_fill = reg.sum() * m_per_px ** 2; a_holes = filled.sum() * m_per_px ** 2
            gold = q["ans"]
            res.append(dict(stem=s, num=r["num"], label=r["label"], scale=m["scale"], gold=gold,
                            raw_rel=(a_fill - gold) / gold, filled_rel=(a_holes - gold) / gold))
import pandas as pd
df = pd.DataFrame(res); df.to_csv("raster_floodfill.csv", index=False)
print("asked rooms on local PNGs:", len(df), "files", df.stem.nunique())
for c in ("raw_rel", "filled_rel"):
    print(c, "within 2%%: %d/%d" % ((df[c].abs() <= 0.02).sum(), len(df)), "median rel err %.3f" % df[c].median(),
          "| by scale:", {sc: "%d/%d" % ((g[c].abs() <= 0.02).sum(), len(g)) for sc, g in df.groupby("scale")})
print(df.sort_values("filled_rel").head(5)[["stem", "num", "label", "gold", "filled_rel"]].to_string())

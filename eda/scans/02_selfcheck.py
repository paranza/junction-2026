"""Self-check for 02_metrics.py: skew sign/size on a synthetic rotated drawing, JPEG quality estimate."""
import importlib.util, pathlib, io
import numpy as np, cv2
from PIL import Image

here = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("m", here / "02_metrics.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

img = np.full((1500, 2200), 245, np.uint8)
cv2.rectangle(img, (100, 100), (2100, 1400), 20, 4)
for y in range(200, 1300, 60):
    cv2.line(img, (200, y), (1900, y), 30, 2)
for x in range(300, 1900, 250):
    cv2.line(img, (x, 150), (x, 1350), 30, 3)
cv2.putText(img, "GROUND FLOOR PLAN 1:100", (300, 1380), cv2.FONT_HERSHEY_SIMPLEX, 1.2, 0, 2)
for true in (-2.0, 0.0, 1.5):
    M = cv2.getRotationMatrix2D((1100, 750), true, 1.0)  # + = counter-clockwise
    rot = cv2.warpAffine(img, M, (2200, 1500), borderValue=245)
    h = m.skew_hough(rot)[0]
    small = m.resize_long(rot, 1000)
    t, _ = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    p = -m.skew_proj((small <= t).astype(np.uint8))
    print(f"true {true:+.1f}  hough {h:+.2f}  proj {p:+.1f}")
    assert abs(h - true) < 0.3 and abs(p - true) < 0.25, (true, h, p)

for q in (50, 75, 90, 95):
    buf = io.BytesIO(); Image.fromarray(img).save(buf, "JPEG", quality=q); buf.seek(0)
    est = m.jpeg_quality(Image.open(buf))
    print("jpeg q", q, "est", est); assert abs(est - q) <= 2
# lettering-height proxy: uppercase lines of known cap height, plus an inverted (blueprint-like) copy
page = np.full((1600, 2400), 240, np.uint8)
cv2.rectangle(page, (50, 50), (2350, 1550), 0, 3)
for i, y in enumerate(range(150, 1450, 45)):
    cv2.putText(page, "LIVING ROOM 12.5 M2  KITCHEN  BEDROOM  HALL", (100 + (i % 3) * 20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 0, 1)
ink = (page[100:160, 90:1200] < 128)
rows = np.nonzero(ink.any(1))[0]
true_h = rows.max() - rows.min() + 1  # one text line inside the window
for name, arr in (("normal", page), ("inverted", 255 - page)):
    pth = here / f"_selfcheck_{name}.jpg"
    Image.fromarray(arr).save(pth, "JPEG", quality=92)
    d = m.analyze(str(pth))
    print(name, "inverted flag", d["inverted"], "true cap height", true_h, "text_h_p50", d.get("text_h_p50"), "n_words", d.get("n_words"))
    assert d["inverted"] == (name == "inverted")
    assert abs(d["text_h_p50"] - true_h) <= 2
    pth.unlink()
print("OK")

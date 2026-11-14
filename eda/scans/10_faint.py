"""Faint-scan test: original crop vs background-flattened + percentile stretch vs CLAHE (classical, deterministic).
Usage: 10_faint.py <rel path> x y w h. Output: denoise/<stem>_faint_panel.png. Read-only on the dataset."""
import sys, pathlib, importlib.util
import numpy as np, cv2
from PIL import Image, ImageDraw
HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("dn", HERE / "04_denoise.py"); dn = importlib.util.module_from_spec(spec); spec.loader.exec_module(dn)
rel, x, y, w, h = sys.argv[1], *map(int, sys.argv[2:6])
gray = np.asarray(Image.open(dn.DS / rel).convert("L"))
flat = dn.flatten(gray)
lo, hi = np.percentile(flat, [0.5, 99.5]); hi = max(hi, lo + 1)
stretch = np.clip((flat.astype(np.float32) - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16, 16)).apply(gray)
tiles = [("original", gray), ("flat + stretch", stretch), ("CLAHE", clahe)]
panel = Image.new("RGB", (3 * w + 20, h + 22), (255, 0, 255))
for i, (name, img) in enumerate(tiles):
    panel.paste(Image.new("RGB", (w, 22), (255, 255, 255)), (i * (w + 10), 0))
    ImageDraw.Draw(panel).text((i * (w + 10) + 4, 4), f"{name} ({pathlib.Path(rel).stem[:30]} x{x} y{y}, native px)", fill=(0, 0, 0))
    panel.paste(Image.fromarray(img[y:y + h, x:x + w]).convert("RGB"), (i * (w + 10), 22))
out = HERE / "denoise" / f"{pathlib.Path(rel).stem}_faint_panel.png"; panel.save(out); print(out, panel.size, "stretch lo/hi", lo, hi)

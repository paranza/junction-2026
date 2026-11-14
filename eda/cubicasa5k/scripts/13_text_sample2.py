"""Second text sample: seed 5, 8 images not viewed before and not in the seed-3 sample, as 2x2 grids."""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import os, random
import pandas as pd
from PIL import Image, ImageDraw
DS = _DATA + "/data/cubicasa5k"
OUT = _ROOT + "/eda/cubicasa5k"
seen = {v.split("_full")[0] + ".png" for v in os.listdir(os.path.join(OUT, "views")) if v.endswith("_full.png")}
seen |= set(pd.read_csv(os.path.join(OUT, "text_sample_answers.csv")).file)
W = pd.read_csv(os.path.join(OUT, "answers_wide.csv"), index_col=0)
pool = sorted(f for f in W.index if f not in seen)
pick = random.Random(5).sample(pool, 8)
cell = 1000
for g in range(2):
    sheet = Image.new("RGB", (2 * cell, 2 * cell + 40), "white"); d = ImageDraw.Draw(sheet)
    for i, f in enumerate(pick[g * 4:(g + 1) * 4]):
        im0 = Image.open(os.path.join(DS, f)).convert("RGB"); s = (cell - 10) / max(im0.size)
        im = im0.resize((round(im0.width * s), round(im0.height * s)), Image.LANCZOS)
        x, y = (i % 2) * cell, (i // 2) * (cell + 20)
        sheet.paste(im, (x + 5, y + 20)); d.text((x + 5, y + 4), f"{f} native {im0.size}", fill="red")
    p = os.path.join(OUT, "views", f"textsample2_grid{g}.png"); sheet.save(p); print(p)
pd.DataFrame({"file": pick}).join(W.loc[pick].reset_index(drop=True)).to_csv(os.path.join(OUT, "text_sample2_answers.csv"), index=False)
print(W.loc[pick][["bedrooms", "saunas", "kitchens", "balconies", "bathrooms", "wc_rooms", "floors", "windows", "doors", "w", "h"]].to_string())

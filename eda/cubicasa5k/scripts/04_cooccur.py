"""Which templates are asked together; does presence relate to style, size or other answers?"""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", ".."))  # repository root
import os
import pandas as pd
OUT = _ROOT + "/eda/cubicasa5k"
q = pd.read_csv(os.path.join(OUT, "questions_cubicasa5k.csv"))
props = pd.read_csv(os.path.join(OUT, "image_props.csv"))
en = q[q.lang == "en"]
W = en.pivot_table(index="file", columns="template", values="answer", aggfunc="first")
W = W.join(props.set_index("file")[["prefix", "w", "h", "megapixels"]])
W.to_csv(os.path.join(OUT, "answers_wide.csv"))
P = W.drop(columns=["prefix", "w", "h", "megapixels"]).notna().astype(int)
print("co-occurrence counts (rows asked AND cols asked):")
print((P.T @ P).to_string())
print("\nasked fraction by prefix:")
print(P.join(W.prefix).groupby("prefix").mean().round(2).T.to_string())
# is presence of doors question related to image size?
for t in ["doors", "saunas", "kitchens", "bedrooms", "wc_rooms", "bathrooms", "balconies", "shower_bath"]:
    a = W[W[t].notna()].megapixels.median(); b = W[W[t].isna()].megapixels.median()
    print(f"{t}: asked n={W[t].notna().sum()} median MP asked={a:.2f} not asked={b:.2f}")
# exact pattern frequency
pat = P.apply(lambda r: "".join(str(x) for x in r), axis=1)
print("\ncolumns:", list(P.columns))
print(pat.value_counts().head(20).to_string())

# pandas report line from the scorer snippet; scorer functions copied to avoid importing the SDK here
import hashlib, math, re
import pandas as pd

def to_number(x):
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(x))
    return float(m.group().replace(",", ".")) if m else math.nan

def is_correct(family, pred, gold):
    p, g = to_number(pred), to_number(gold)
    if family == "count":
        return p == g
    if family in ("area", "length", "volume"):
        return abs(p - g) <= 0.02 * abs(g)
    raise ValueError(family)

def is_heldout(drawing_id, pct=20):
    return int(hashlib.sha256(drawing_id.encode()).hexdigest(), 16) % 100 < pct

df = pd.DataFrame({"drawing_id": [f"d{i % 40}" for i in range(200)],
                   "source": ["a", "b"] * 100, "family": ["count", "area", "count", "length"] * 50,
                   "pred": [3, "10.1", 2, 5.2] * 50, "gold": [3, 10, 3, 5] * 50})
df["correct"] = [is_correct(f, p, g) for f, p, g in zip(df.family, df.pred, df.gold)]
dev = df[~df.drawing_id.map(is_heldout)]
print(dev.groupby(["source", "family"])["correct"].agg(["mean", "count"]))
assert set(dev.drawing_id).isdisjoint(set(df[df.drawing_id.map(is_heldout)].drawing_id))

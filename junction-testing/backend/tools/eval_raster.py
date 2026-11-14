"""Evaluate the raster path (PlanNet + GlyphNet) on images it never trained on.

python tools/eval_raster.py --set swiss   # 9 holdout Swiss PNGs (every 8th drawing)
python tools/eval_raster.py --set cc      # 241 preview CubiCasa PNGs (excluded from training)
Scoring follows the dataset README: counts exact, areas within 2 %.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stoa import pipeline, questions  # noqa: E402

DS = os.environ.get("STOA_DATA", "../../../preview_dataset/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["swiss", "cc"], default="swiss")
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    qs = collections.defaultdict(list)
    for l in open(os.path.join(DS, "questions.jsonl"), encoding="utf8"):
        x = json.loads(l)
        qs[x["path"]].append(x)
    if a.set == "swiss":
        stems = sorted(p[:-4] for p in glob.glob(os.path.join(DS, "data/swiss_dwellings/*.dxf")))
        files = [s + ".png" for i, s in enumerate(stems) if i % 8 == 0]
        key = lambda f: "data/swiss_dwellings/" + os.path.basename(f)[:-4] + ".pdf"
    else:
        files = sorted(glob.glob(os.path.join(DS, "data/cubicasa5k/*.png")))
        key = lambda f: "data/cubicasa5k/" + os.path.basename(f)
    files = files[: a.limit]
    ok, tot = collections.Counter(), collections.Counter()
    rows = []
    t0 = time.time()
    for f in files:
        _, facts = pipeline.analyze_file(f)
        for x in qs[key(f)]:
            if x["type"] not in ("count", "area"):
                continue
            r = questions.answer(x["question"], facts)
            v = r["value"] if r else None
            good = v is not None and (v == x["answer"] if x["type"] == "count" else abs(v - x["answer"]) <= 0.02 * abs(x["answer"]) + 1e-9)
            k = x["question"] if x["question"].isascii() else "(non-English) " + x["type"]
            k = k[:70]
            ok[k] += good; tot[k] += 1
            ok["ALL " + x["type"]] += good; tot["ALL " + x["type"]] += 1
            rows.append({"file": os.path.basename(f), "q": x["question"], "gold": x["answer"], "pred": v, "ok": good})
    print(f"{len(files)} images in {time.time() - t0:.0f}s")
    for k in sorted(tot, key=lambda k: (not k.startswith("ALL"), k)):
        print(f"{ok[k]:5d}/{tot[k]:<5d} {ok[k] / tot[k]:6.1%}  {k}")
    if a.out:
        json.dump(rows, open(a.out, "w", encoding="utf8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

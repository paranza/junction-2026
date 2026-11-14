"""Parse LICENSE.md tables for the four scan sources into one CSV (file, title, licence, credit, url).
Read-only on the dataset. Output: meta.csv in the work dir."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import sys, re, pathlib
import pandas as pd

DS = pathlib.Path(_DATA + "")
OUT = pathlib.Path(__file__).parent
rows = []
for src in ["europeana", "finna", "habs", "wikimedia"]:
    lic = (DS / "data" / src / "LICENSE.md").read_text(encoding="utf-8")
    header = None
    for line in lic.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if len(cells) != len(header):
            # titles may contain '|' ; keep first cell as file, last 3 as licence/credit/source, middle as title
            cells = [cells[0], " | ".join(cells[1:len(cells) - len(header) + 2])] + cells[-(len(header) - 2):]
        d = dict(zip(header, cells))
        d["source_name"] = src
        rows.append(d)
    files_on_disk = {p.name for p in (DS / "data" / src).iterdir() if p.name != "LICENSE.md"}
    listed = {r["file"] for r in rows if r["source_name"] == src}
    print(src, "header", header, "listed", len(listed), "on disk", len(files_on_disk),
          "missing from licence", sorted(files_on_disk - listed)[:5], "listed not on disk", sorted(listed - files_on_disk)[:5])

df = pd.DataFrame(rows)
df.to_csv(OUT / "meta.csv", index=False)
print(df.groupby("source_name")["licence"].value_counts().to_string())

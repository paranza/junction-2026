"""Re-run 02_metrics.analyze on rows of metrics.csv that failed (iCloud timeouts during the network outage),
then merge them back into metrics.csv. Read-only on the dataset."""
import importlib, pathlib, sys
import pandas as pd
from multiprocessing import Pool

here = pathlib.Path(__file__).parent
sys.path.insert(0, str(here))  # so worker processes can import 02_metrics by name (needed for pickling)
m = importlib.import_module("02_metrics")

if __name__ == "__main__":
    d = pd.read_csv(here / "metrics.csv")
    bad = d.loc[d["error"].notna(), "path"].tolist()
    print("re-running", len(bad), flush=True)
    with Pool(4) as pool:
        new = pd.DataFrame(pool.map(m.analyze, bad, chunksize=1))
    ok = d[d["error"].isna()]
    out = pd.concat([ok, new], ignore_index=True)
    assert len(out) == len(d) and out.path.is_unique
    out.to_csv(here / "metrics.csv", index=False)
    print("still failing", new.get("error", pd.Series(dtype=str)).notna().sum(), flush=True)

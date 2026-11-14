"""Copy the scan-source files into work dir/cache/data/<source>/ so repeated reads do not re-trigger iCloud
downloads (the dataset folder holds 'dataless' placeholders that macOS evicts again after reading).
Only reads the dataset. Skips files already cached with the right size. Order: wikimedia first (next in 02_metrics)."""
import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import pathlib, shutil, sys
from concurrent.futures import ThreadPoolExecutor

DS = pathlib.Path(_DATA + "")
CACHE = pathlib.Path(__file__).parent / "cache"
files = [f for s in ["wikimedia", "habs", "finna", "europeana"] for f in sorted((DS / "data" / s).iterdir()) if f.name != "LICENSE.md"]
if len(sys.argv) > 1:  # optional priority list: text file with one data/<source>/<file> per line
    files = [DS / ln.strip() for ln in pathlib.Path(sys.argv[1]).read_text().splitlines() if ln.strip()]


def copy(f):
    dst = CACHE / f.relative_to(DS)
    if dst.exists() and dst.stat().st_size == f.stat().st_size:
        return 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    shutil.copyfile(f, tmp)
    assert tmp.stat().st_size == f.stat().st_size, f
    tmp.rename(dst)
    print("cached", dst.relative_to(CACHE), flush=True)
    return 1


with ThreadPoolExecutor(6) as ex:
    n = sum(ex.map(copy, files))
print("done, newly cached", n, "of", len(files), flush=True)

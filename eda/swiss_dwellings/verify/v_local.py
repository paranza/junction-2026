import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Which dataset files are materialised locally (not iCloud 'dataless')? Reading a dataless file blocks on download.
import os, glob
D = _DATA + "/data/swiss_dwellings"
SF_DATALESS = 0x40000000
def stems(*exts):
    all_ = sorted(os.path.basename(p)[:-4] for p in glob.glob(D + "/*.pdf"))
    return [s for s in all_ if all(not (os.stat(f"{D}/{s}.{e}").st_flags & SF_DATALESS) for e in exts)]

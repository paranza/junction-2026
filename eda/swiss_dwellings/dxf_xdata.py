import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
import ezdxf, sys, collections
DS = _DATA + "/data/swiss_dwellings"
doc = ezdxf.readfile(f"{DS}/{sys.argv[1]}.dxf")
msp = doc.modelspace()
apps = [a.dxf.name for a in doc.appids]
print("appids", apps)
seen = collections.Counter()
for e in msp:
    pass
    for a in apps:
        if e.has_xdata(a):
            x = [(c, v) for c, v in e.get_xdata(a)]
            key = (e.dxftype(), e.dxf.layer)
            if seen[key] < 4:
                print(key, a, x[:12])
            seen[key] += 1
print(seen)

"""DWG probe: version string, ezdxf readability, embedded preview image, readable ASCII strings.
Writes any embedded PNG/BMP preview to <work_dir>/img/dwg_preview_<n>.(png|bmp).
Usage: python -I dwg_probe.py <dataset_dir> <work_dir>"""
import sys, os, re
import ezdxf
from ezdxf.addons import odafc

D, W = sys.argv[1], sys.argv[2]
root = os.path.join(D, "data", "opening_design")
VER = {"AC1015": "R2000", "AC1018": "R2004", "AC1021": "R2007", "AC1024": "R2010", "AC1027": "R2013", "AC1032": "R2018"}
print("ezdxf", ezdxf.__version__, "| ODA File Converter installed:", odafc.is_installed())
n = 0
for dp, _, fs in sorted(os.walk(root)):
    for f in sorted(fs):
        if not f.lower().endswith(".dwg"):
            continue
        n += 1
        full = os.path.join(dp, f)
        b = open(full, "rb").read()
        ver = b[:6].decode("ascii", "replace")
        try:
            ezdxf.readfile(full)
            ez = "read OK"
        except Exception as e:  # expected: DWG is a binary format ezdxf does not parse
            ez = type(e).__name__
        png = b.find(b"\x89PNG\r\n\x1a\n")
        prev = ""
        if png >= 0:
            end = b.find(b"IEND", png)
            if end > 0:
                out = os.path.join(W, "img", f"dwg_preview_{n:02d}.png")
                open(out, "wb").write(b[png:end + 8])
                prev = f"PNG {end + 8 - png} bytes -> {os.path.basename(out)}"
        # long ASCII runs (e.g. xref paths, layer names) as a cheap hint of content
        strs = [s.decode() for s in re.findall(rb"[ -~]{12,}", b[:2_000_000])]
        print(f"{n:2d} {ver} {VER.get(ver, '?'):6} {len(b):>9} B  ezdxf:{ez:22} preview:{prev or 'none':45} "
              f"ascii_runs={len(strs)} | {os.path.relpath(full, root)[:95]}")

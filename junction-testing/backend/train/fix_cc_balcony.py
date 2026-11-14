"""Re-render the balcony channel of CubiCasa labels built before balconies were
separated from other outdoor spaces (terraces, porches). Idempotent."""
import glob, os, sys
import cv2, numpy as np
from stoa.cubicasa import ROOM_TYPES, parse_svg
from train.build_cubicasa import CC_SEG, SCALE

def fix(npz, cc_root):
    name = os.path.basename(npz)[:-4]
    s, i = name.rsplit("-", 1)
    a = parse_svg(os.path.join(cc_root, s, i, "model.svg"))
    z = dict(np.load(npz))
    seg = np.unpackbits(z["seg"], axis=0)[: len(CC_SEG)]
    b = 3 + ROOM_TYPES.index("balcony")
    seg[b] = 0
    for sp in a["spaces"]:
        if sp["category"] == "balcony":
            cv2.fillPoly(seg[b], [np.round(np.asarray(sp["polygon"]) * SCALE).astype(np.int32)], 1)
    z["seg"] = np.packbits(seg, axis=0)
    np.savez_compressed(npz, **z)

if __name__ == "__main__":
    for d in sys.argv[2:]:
        for p in glob.glob(os.path.join(d, "*.npz")):
            fix(p, sys.argv[1])
    print("fixed")

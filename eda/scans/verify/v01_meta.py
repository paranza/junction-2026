import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Independent JPEG header parse (no PIL): dims, components, JFIF density, EXIF/XMP/ICC, IJG quality from DQT.
import os, struct, sys, csv, collections
import numpy as np
D = _DATA + "/data"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v01_meta.csv")
STD_L = np.array([16,11,10,16,24,40,51,61,12,12,14,19,26,58,60,55,14,13,16,24,40,57,69,56,14,17,22,29,51,87,80,62,
 18,22,37,56,68,109,103,77,24,35,55,64,81,104,113,92,49,64,78,87,103,121,120,101,72,92,95,98,112,100,103,99])
ZZ = [0,1,8,16,9,2,3,10,17,24,32,25,18,11,4,5,12,19,26,33,40,48,41,34,27,20,13,6,7,14,21,28,35,42,49,56,57,50,43,36,29,22,15,23,30,37,44,51,58,59,52,45,38,31,39,46,53,60,61,54,47,55,62,63]
def ijg(q):
    s = 5000//q if q < 50 else 200-2*q
    return np.clip((STD_L*s+50)//100, 1, 255)
TABLES = {q: ijg(q) for q in range(1, 101)}

def parse(path):
    b = open(path, 'rb').read()
    assert b[:2] == b'\xff\xd8', 'not jpeg'
    i = 2; r = dict(bytes=len(b), exif=0, xmp=0, icc=0, com=0, adobe=0, jfif_units=None, jfif_x=None, jfif_y=None, q_exact=None, q_near=None, sof=None)
    while i < len(b):
        if b[i] != 0xFF: i += 1; continue
        m = b[i+1]
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7: i += 2; continue
        if m == 0xD9: break
        L = struct.unpack('>H', b[i+2:i+4])[0]; seg = b[i+4:i+2+L]
        if m == 0xE0 and seg[:5] == b'JFIF\x00':
            r['jfif_units'], r['jfif_x'], r['jfif_y'] = seg[7], struct.unpack('>H', seg[8:10])[0], struct.unpack('>H', seg[10:12])[0]
        elif m == 0xE1 and seg[:6] == b'Exif\x00\x00': r['exif'] = 1
        elif m == 0xE1 and b'ns.adobe.com/xap' in seg[:64]: r['xmp'] = 1
        elif m == 0xE2 and seg[:12] == b'ICC_PROFILE\x00': r['icc'] = 1
        elif m == 0xFE: r['com'] = 1; r['com_text'] = seg[:80].decode('latin1')
        elif m == 0xEE: r['adobe'] = 1
        elif m == 0xDB:
            j = 0
            while j < len(seg):
                pq, tid = seg[j] >> 4, seg[j] & 15; j += 1
                n = 128 if pq else 64
                vals = struct.unpack('>64H', seg[j:j+n]) if pq else tuple(seg[j:j+64]); j += n
                if tid == 0:
                    nat = np.zeros(64, int); nat[ZZ] = vals
                    for q, t in TABLES.items():
                        if np.array_equal(t, nat): r['q_exact'] = q
                    r['q_near'] = min(TABLES, key=lambda q: np.abs(TABLES[q]-nat).sum())
        elif m in (0xC0, 0xC1, 0xC2):
            r['sof'] = m; r['h'], r['w'] = struct.unpack('>HH', seg[1:5]); r['ncomp'] = seg[5]
        elif m == 0xDA: break
        i += 2 + L
    return r

if __name__ == '__main__':
    assert ijg(50)[0] == 16 and ijg(100)[0] == 1  # self-check of the IJG scaling
    rows = []
    for s in ('europeana', 'finna', 'habs', 'wikimedia'):
        for f in sorted(os.listdir(os.path.join(D, s))):
            if not f.lower().endswith('.jpg'): continue
            r = parse(os.path.join(D, s, f)); r.update(source=s, file=f); rows.append(r)
    keys = sorted({k for r in rows for k in r})
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, keys); w.writeheader(); w.writerows(rows)
    import pandas as pd
    df = pd.DataFrame(rows); df['long'] = df[['w', 'h']].max(axis=1)
    print('n', len(df))
    print(df.groupby('source')['long'].describe()[['count', 'min', '50%', 'max']])
    for s, g in df.groupby('source'):
        print(s, 'long==3000:', (g.long == 3000).sum(), 'long==2500:', (g.long == 2500).sum(), '<500:', (g.long < 500).sum(), '<800:', (g.long < 800).sum(),
              'ncomp:', dict(collections.Counter(g.ncomp)), 'q_exact:', dict(collections.Counter(g.q_exact.fillna(-1).astype(int))), 'progressive:', (g.sof == 0xC2).sum())
    print('jfif units', collections.Counter(zip(df.jfif_units, df.jfif_x, df.jfif_y)))
    print('exif', df.exif.sum(), 'xmp', df.xmp.sum(), 'icc', df.icc.sum(), 'com', df.com.sum(), 'adobe', df.adobe.sum())
    print('median MB', df.groupby('source').bytes.median() / 1e6)

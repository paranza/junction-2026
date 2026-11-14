# Cross-checks: colour class agreement, text-height disagreement, dHash near-duplicates,
# opening (2x2 / 3x3) effect on text-like components for the analyst's 5 files + 5 seeded others,
# and a contact sheet of polarity disagreements.
import os, sys, numpy as np, pandas as pd, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v02_pixels import text_heights, D
V = os.path.dirname(os.path.abspath(__file__))
v = pd.read_csv(os.path.join(V, 'v02_pixels.csv')); e = pd.read_csv(os.path.join(V, '..', 'metrics_enriched.csv'))
m = v.merge(e[['file', 'colour_class', 'inverted', 'text_h_p50', 'n_words']], on='file', suffixes=('', '_a'))
# my colour class
def cc(r):
    if r.chroma_p99 < 6: return 'grey'
    return 'true_colour' if r.off_frac > 0.002 else 'tinted_mono'
m['mine_cc'] = m.apply(cc, axis=1)
print(pd.crosstab(m.colour_class, m.mine_cc))
print('mine true colour by source', m[m.mine_cc == 'true_colour'].groupby('source').size().to_dict())
# text height disagreement
both = m[(m.n_text >= 20) & m.text_h_p50.notna()]
print('both measured', len(both), pd.crosstab(both.text_h_p50 < 8, both.text_h_med < 8, rownames=['analyst<8'], colnames=['mine<8']))
dis = both[(both.text_h_p50 < 8) & (both.text_h_med >= 10)].sort_values('text_h_p50')
print(dis[['source', 'file', 'long', 'text_h_p50', 'n_words', 'text_h_med', 'n_text']].head(12).to_string())
# dHash near duplicates
hb = np.array([[c == '1' for c in s] for s in v.dhash.astype(str).str.zfill(64)])
dd = (hb[:, None, :] != hb[None, :, :]).sum(-1)
iu = np.argwhere(np.triu(dd <= 4, 1))
print('near-duplicate pairs (dHash <=4 bits):', len(iu))
for i, j in iu[:20]: print('  ', v.source[i], v.file[i], v.long[i], '|', v.source[j], v.file[j], v.long[j], dd[i, j])
# opening test on text-like components
an = ['europeana/0940415__nn5Vdgp.jpg', 'finna/hka.139877703731200_160499796228700.jpg', 'wikimedia/23820334.jpg',
      'europeana/1373_https___ekultura_hr_purl_url_4UTLLA7T2TB2DEO24EL2AR5J67EY7IWG.jpg', 'finna/hka.139881104940300_168569566239300.jpg']
rng = np.random.default_rng(11); others = v[v.n_text >= 20].sample(6, random_state=11)
files = an + [f'{s}/{f}' for s, f in zip(others.source, others.file)]
for rel in files:
    p = os.path.join(D, rel)
    if not os.path.exists(p): print('missing', rel); continue
    g = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    inv = v.set_index('file').loc[os.path.basename(rel), 'inverted']
    g = 255 - g if inv else g
    ink = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 12)
    _, otsu = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    res = [len(text_heights(ink))]
    for k in (2, 3):
        res.append(len(text_heights(cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((k, k), np.uint8)))))
    res.append(len(text_heights(otsu)))
    print(f'{rel[:60]:60s} long={max(g.shape)} text_comps orig={res[0]} open2={res[1]} open3={res[2]} otsu_global={res[3]}')
# polarity disagreement contact sheet
pdis = m[(m.inverted == 1) != (m.inverted_a == True)]
tiles = []
for _, r in pdis.iterrows():
    im = cv2.imread(os.path.join(D, r.source, r.file)); k = 300 / max(im.shape[:2])
    im = cv2.resize(im, (int(im.shape[1] * k), int(im.shape[0] * k)), interpolation=cv2.INTER_AREA)
    t = np.full((330, 300, 3), 255, np.uint8); t[:im.shape[0], :im.shape[1]] = im
    cv2.putText(t, f"{r.file[:22]} me{int(r.inverted)} an{int(r.inverted_a)}", (2, 325), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    tiles.append(t)
while len(tiles) % 5: tiles.append(np.full((330, 300, 3), 255, np.uint8))
sheet = np.vstack([np.hstack(tiles[i:i + 5]) for i in range(0, len(tiles), 5)])
cv2.imwrite(os.path.join(V, 'polarity_disagreements.jpg'), sheet)
print('sheet', sheet.shape, 'n', len(pdis))

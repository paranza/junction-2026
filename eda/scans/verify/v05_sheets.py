import os as _os  # portable paths, added when this script was copied into the repo
_DATA = _os.path.expanduser(_os.environ.get("STOA_DATA_ROOT", "~/stoa-data/junction-dataset-preview"))  # folder with data/ and questions.jsonl
# Contact sheets for adjudication by eye: agreed-inverted files, analyst "colour" vs my "tinted mono", near-duplicates.
import os, numpy as np, pandas as pd, cv2
D = _DATA + "/data"
V = os.path.dirname(os.path.abspath(__file__))
v = pd.read_csv(os.path.join(V, 'v02_pixels.csv')); e = pd.read_csv(os.path.join(V, '..', 'metrics_enriched.csv'))
m = v.merge(e[['file', 'colour_class', 'inverted']], on='file', suffixes=('', '_a'))
m['mine_cc'] = np.where(m.chroma_p99 < 6, 'grey', np.where(m.off_frac > 0.002, 'true_colour', 'tinted_mono'))
def sheet(rows, name, cols=5, side=300):
    tiles = []
    for s, f, lab in rows:
        im = cv2.imread(os.path.join(D, s, f)); k = side / max(im.shape[:2])
        im = cv2.resize(im, (max(1, int(im.shape[1] * k)), max(1, int(im.shape[0] * k))), interpolation=cv2.INTER_AREA)
        t = np.full((side + 30, side, 3), 255, np.uint8); t[:im.shape[0], :im.shape[1]] = im
        cv2.putText(t, lab[:40], (2, side + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1); tiles.append(t)
    while len(tiles) % cols: tiles.append(np.full((side + 30, side, 3), 255, np.uint8))
    cv2.imwrite(os.path.join(V, name), np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]))
agree = m[(m.inverted == 1) & (m.inverted_a == True)]
sheet([(r.source, r.file, f'{r.source[:4]} {r.file[:24]}') for r in agree.itertuples()], 'inverted_agreed.jpg')
cm = m[(m.colour_class == 'colour') & (m.mine_cc == 'tinted_mono')].sample(15, random_state=5)
sheet([(r.source, r.file, f'{r.source[:4]} {r.file[:16]} off={r.off_frac:.4f}') for r in cm.itertuples()], 'colour_disagree_sample.jpg')
sheet([('wikimedia', '3561257.jpg', '3561257'), ('wikimedia', '7156155.jpg', '7156155'), ('wikimedia', '70630004.jpg', '70630004'), ('wikimedia', '70630005.jpg', '70630005')], 'near_dups.jpg', cols=4)
print(len(agree), len(cm))

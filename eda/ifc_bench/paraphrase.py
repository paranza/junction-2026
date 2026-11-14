"""Cross-model paraphrase overlap of ifc_bench questions (token Jaccard). Usage: python -I paraphrase.py <work_dir>"""
import sys, os, json, re, itertools, collections
W = sys.argv[1]
rows = [json.loads(l) for l in open(os.path.join(W, "ifc_bench_questions.jsonl"))]
STOP = set("the a an of in on for and or with what which are is this these there how many building used here their its each by including any to be do does all from as at that it model".split())
tok = lambda q: {w for w in re.findall(r"[a-z0-9]+", q.lower()) if w not in STOP}
T = [tok(r["question"]) for r in rows]
mod = [r["path"].split("/")[-1][:-4] for r in rows]
best = []
pairs = collections.Counter()
for i in range(len(rows)):
    js = [(len(T[i] & T[j]) / max(1, len(T[i] | T[j])), j) for j in range(len(rows)) if mod[j] != mod[i]]
    jmax, j = max(js)
    best.append(jmax)
    if jmax >= 0.5:
        pairs[(mod[i], mod[j])] += 1
n = len(rows)
for th in (0.3, 0.5, 0.7):
    print(f"questions whose closest other-model question has Jaccard >= {th}: {sum(b >= th for b in best)}/{n}")
per_model = collections.defaultdict(list)
for m, b in zip(mod, best):
    per_model[m].append(b >= 0.5)
print({m: f"{sum(v)}/{len(v)}" for m, v in per_model.items()})
print("closest-match model pairs (J>=0.5):", dict(pairs))

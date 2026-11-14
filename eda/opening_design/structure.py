"""Folder structure of data/opening_design: projects, folder roles, dated transfers, sheet ids, versions.
Usage: python -I structure.py <dataset_dir> <work_dir>"""
import sys, re, os, collections
import pandas as pd

D, W = sys.argv[1], sys.argv[2]
root = os.path.join(D, "data", "opening_design")
q = pd.read_json(os.path.join(D, "questions.jsonl"), lines=True)
q = q[q.path.str.startswith("data/opening_design/")]
nq = q.groupby("path").size()

rows = []
for dp, _, fs in os.walk(root):
    for f in fs:
        if f == "LICENSE.md":
            continue
        full = os.path.join(dp, f)
        rel = os.path.relpath(full, root)
        parts = rel.split(os.sep)
        low = rel.lower()
        if "archive" in low:
            role = "archive"
        elif "current set" in low:
            role = "current_set"
        elif parts[1] == "Transfer":
            role = "transfer"
        elif parts[1].startswith("Models") or "ifc roundtrip" in low:
            role = "models"
        elif parts[1] == "Prints":
            role = "prints"
        else:
            role = "other"
        m = re.search(r"(?:^|/)(\d{8})\s*[-_ ]", rel)
        date = m.group(1) if m else ""
        # sheet id like A-801, A700, S-300, P1-04, A-100.A, A-101-B
        sm = re.search(r"\b([APSMEC]\d{0,2}-?\d{2,3}(?:[.-][A-Z])?)\b", f)
        sheet = sm.group(1).replace("-", "").replace(".", "") if sm else ""
        rows.append(dict(project=parts[0], role=role, folder_date=date, ext=f.rsplit(".", 1)[-1].lower(),
                         sheet_id=sheet, file=f, rel=rel, bytes=os.path.getsize(full),
                         n_questions=int(nq.get("data/opening_design/" + rel, 0))))
df = pd.DataFrame(rows).sort_values(["project", "rel"])
df.to_csv(os.path.join(W, "structure.csv"), index=False)

print("files", len(df), "| by ext", df.ext.value_counts().to_dict())
print("projects", df.project.nunique())
print(df.groupby("project").agg(files=("rel", "size"), pdf=("ext", lambda s: (s == "pdf").sum()),
                                dwg=("ext", lambda s: (s == "dwg").sum()), ifc=("ext", lambda s: (s == "ifc").sum()),
                                questions=("n_questions", "sum")).to_string())
print("\nrole counts", df.role.value_counts().to_dict())
print("files under a dated folder:", (df.folder_date != "").sum(), "of", len(df))
print("date range", df.folder_date[df.folder_date != ""].min(), df.folder_date[df.folder_date != ""].max())

# same sheet id (per project) seen in more than one file
s = df[df.sheet_id != ""]
g = s.groupby(["project", "sheet_id"])
print("\nfiles with a parseable sheet id:", len(s), "| distinct (project, sheet):", g.ngroups)
multi = [(k, grp) for k, grp in g if len(grp) > 1]
print("sheet ids with >1 file:", len(multi))
for (p, sh), grp in multi:
    print(f"  {p} {sh}:")
    for _, r in grp.iterrows():
        print(f"     [{r.role:11}] {r.ext} {r.bytes:>9} q={r.n_questions} {r.rel}")

# same basename in different folders
b = df.groupby("file").filter(lambda x: len(x) > 1)
print("\nidentical file names in different folders:", b.file.nunique())
for f, grp in b.groupby("file"):
    print("  ", f, list(grp.rel))

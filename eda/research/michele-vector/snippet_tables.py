# S4 final: schedule tables on real (often rotated) sheets -> DataFrames, fast path.
import sys, glob, time, pymupdf

def schedule_tables(page, title="SCHEDULE"):
    if page.rotation:
        page.remove_rotation()                 # in memory only: text becomes horizontal, coords match what a human sees
    paths = page.get_drawings()                # extract vector graphics once, reuse for every clip
    out = []
    for hit in page.search_for(title):         # ASCII case-insensitive; schedule titles sit above or below the grid
        clip = pymupdf.Rect(hit.x0 - 400, hit.y0 - 400, hit.x0 + 600, hit.y0 + 400) & page.rect
        for t in page.find_tables(clip=clip, paths=paths, use_layout=False).tables:  # default use_layout=True: ~40 s, 0 tables on a real sheet
            cells = [[page.get_text("text", clip=c).strip() if c else None for c in row.cells] for row in t.rows]  # robust per-cell text
            out.append((tuple(t.bbox), t.to_pandas(), cells))
    return out

if __name__ == "__main__":
    for f in sys.argv[1:]:
        for g in sorted(glob.glob(f + "/**/*.pdf", recursive=True)) if not f.endswith(".pdf") else [f]:
            page = pymupdf.open(g)[0]
            if not page.search_for("SCHEDULE"): continue
            t0 = time.time(); res = schedule_tables(page); dt = time.time() - t0
            print(f"rot-fixed page, {len(res)} tables in {dt:.1f}s", [df.shape for _, df, _ in res][:6])
            if res: print("   first table row1 (per-cell):", [str(c)[:12] for c in res[0][2][1][:6]])

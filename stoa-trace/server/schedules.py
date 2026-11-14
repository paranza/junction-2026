"""Ruled schedule tables from a PDF page: cells with their boxes, no hand-given regions.

Door, window, finish and type schedules on construction sheets are drawn as ruled grids.
We take the page's axis-parallel stroked rules, group touching rules into table regions,
and cut each region into a lattice of cells (columns from vertical rules, rows from
horizontal rules). A word belongs to the cell that holds its centre. Every cell keeps its
box so an answer can point at the exact rows it used.

Method adapted from the team EDA (eda/opening_design/sched.py, tables_auto.py), rewritten
without OpenCV. It reads only geometry and the text layer; it never reads answer labels.
"""
from __future__ import annotations

import re

_MIN_ROWS = 3


def _segments(drawings):
    """Axis-parallel stroked segments: hs = (x0, x1, y), vs = (y0, y1, x), in page coordinates."""
    hs, vs = [], []

    def add(ax, ay, bx, by):
        if abs(ay - by) < 0.5 and abs(ax - bx) > 2:
            hs.append((min(ax, bx), max(ax, bx), (ay + by) / 2))
        elif abs(ax - bx) < 0.5 and abs(ay - by) > 2:
            vs.append((min(ay, by), max(ay, by), (ax + bx) / 2))

    for d in drawings:
        for it in d.get("items", ()):
            if it[0] == "l":
                add(it[1].x, it[1].y, it[2].x, it[2].y)
            elif it[0] == "re":
                r = it[1]
                x0, y0, x1, y1 = min(r.x0, r.x1), min(r.y0, r.y1), max(r.x0, r.x1), max(r.y0, r.y1)
                if x1 - x0 > 2 and y1 - y0 > 2:
                    add(x0, y0, x1, y0); add(x0, y1, x1, y1); add(x0, y0, x0, y1); add(x1, y0, x1, y1)
    return hs, vs


def _regions(hs, vs, tol=1.5):
    """Group rules that touch or cross into connected regions (union-find on segments)."""
    segs = [("h", s) for s in hs] + [("v", s) for s in vs]
    parent = list(range(len(segs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def touch(a, b):
        (ka, sa), (kb, sb) = a, b
        if ka == kb == "h":
            return abs(sa[2] - sb[2]) <= tol and sa[0] <= sb[1] + tol and sb[0] <= sa[1] + tol
        if ka == kb == "v":
            return abs(sa[2] - sb[2]) <= tol and sa[0] <= sb[1] + tol and sb[0] <= sa[1] + tol
        h, v = (sa, sb) if ka == "h" else (sb, sa)
        return h[0] - tol <= v[2] <= h[1] + tol and v[0] - tol <= h[2] <= v[1] + tol

    # bucket by coarse cells so large sheets stay fast
    grid = {}
    for i, (k, s) in enumerate(segs):
        x0, x1, y0, y1 = (s[0], s[1], s[2], s[2]) if k == "h" else (s[2], s[2], s[0], s[1])
        for gx in range(int(x0 // 50), int(x1 // 50) + 1):
            for gy in range(int(y0 // 50), int(y1 // 50) + 1):
                grid.setdefault((gx, gy), []).append(i)
    for members in grid.values():
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                i, j = members[a], members[b]
                if find(i) != find(j) and touch(segs[i], segs[j]):
                    parent[find(i)] = find(j)
    groups = {}
    for i in range(len(segs)):
        groups.setdefault(find(i), []).append(segs[i])
    out = []
    for members in groups.values():
        h = [s for k, s in members if k == "h"]
        v = [s for k, s in members if k == "v"]
        if len(h) < 2 or len(v) < 2:
            continue
        x0 = min([s[0] for s in h] + [s[2] for s in v]); x1 = max([s[1] for s in h] + [s[2] for s in v])
        y0 = min([s[2] for s in h] + [s[0] for s in v]); y1 = max([s[2] for s in h] + [s[1] for s in v])
        if x1 - x0 >= 40 and y1 - y0 >= 15:
            out.append({"bbox": [x0, y0, x1, y1], "h": h, "v": v})
    return out


def _cluster(values, tol=1.5):
    values = sorted(values)
    groups = []
    for v in values:
        if groups and v - groups[-1][-1] <= tol:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [sum(g) / len(g) for g in groups]


def _merge_stacked(regions, edge_tol=4, gap=40):
    """A header box drawn separately right above its body grid (same left/right edges) is one table."""
    regions = sorted(regions, key=lambda r: (r["bbox"][1], r["bbox"][0]))
    merged = True
    while merged:
        merged = False
        for i, a in enumerate(regions):
            for j, b in enumerate(regions):
                if i == j:
                    continue
                (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = a["bbox"], b["bbox"]
                if abs(ax0 - bx0) < edge_tol and abs(ax1 - bx1) < edge_tol and 0 <= by0 - ay1 < gap:
                    regions[i] = {"bbox": [min(ax0, bx0), ay0, max(ax1, bx1), by1], "h": a["h"] + b["h"], "v": a["v"] + b["v"]}
                    del regions[j]
                    merged = True
                    break
            if merged:
                break
    return regions


def _lattice(region, words):
    x0, y0, x1, y1 = region["bbox"]
    inside = [w for w in words if x0 - 1 <= (w[0] + w[2]) / 2 <= x1 + 1 and y0 - 1 <= (w[1] + w[3]) / 2 <= y1 + 1]
    ys = _cluster([s[2] for s in region["h"]])
    xs = _cluster([s[2] for s in region["v"]])
    rows = []
    for ya, yb in zip(ys, ys[1:]):
        if yb - ya < 3:
            continue
        band = [w for w in inside if ya <= (w[1] + w[3]) / 2 < yb]
        if not band:
            continue
        cells = []
        for xa, xb in zip(xs, xs[1:]):
            if xb - xa < 3:
                continue
            ws = sorted((w for w in band if xa <= (w[0] + w[2]) / 2 < xb), key=lambda w: (round(w[1] / 3), w[0]))
            cells.append({"text": " ".join(w[4] for w in ws), "bbox": [xa, ya, xb, yb]})
        if any(c["text"] for c in cells):
            rows.append(cells)
    return rows, inside


def find_tables(page, drawings=None):
    """All ruled tables on a page (page coordinates, rotation already removed by the caller).
    Each table: title (text just above the grid or its first row), header cells, body rows."""
    drawings = drawings if drawings is not None else page.get_drawings()
    words = page.get_text("words")
    hs, vs = _segments(drawings)
    tables = []
    regions = _merge_stacked(_regions(hs, vs))
    for region in regions:
        rows, inside = _lattice(region, words)
        cols_with_text = sum(1 for j in range(len(rows[0]) if rows else 0)
                             if sum(1 for r in rows if j < len(r) and r[j]["text"]) >= 2)
        if len(rows) < _MIN_ROWS or cols_with_text < 2:
            continue
        x0, y0, x1, y1 = region["bbox"]
        first = " ".join(c["text"] for c in rows[0] if c["text"])
        # Title: the grid's own first row if it names a schedule, else the nearest line above
        # the grid (horizontally overlapping) that does.
        title = first if re.search(r"schedule", first, re.I) else ""
        if not title:
            lines = {}
            for w in words:
                if w[3] <= y0 + 1 and y0 - 250 <= w[1] and w[2] >= x0 - 2 and w[0] <= x1 + 2:
                    lines.setdefault((w[5], w[6]), []).append(w)
            named = [ws for ws in lines.values() if re.search(r"schedule", " ".join(w[4] for w in ws), re.I)]
            if named:
                best = max(named, key=lambda ws: max(w[3] for w in ws))
                title = " ".join(w[4] for w in sorted(best, key=lambda w: w[0]))
        # A header drawn just above the grid (outside its rules) when the first grid row is data.
        outside_header = None
        if any(re.search(r"\d", c["text"]) for c in rows[0][:2]):
            band = [w for w in words if y0 - 18 <= (w[1] + w[3]) / 2 < y0 and x0 - 2 <= (w[0] + w[2]) / 2 <= x1 + 2]
            if band:
                outside_header = []
                for c in rows[0]:
                    cx0, _, cx1, _ = c["bbox"]
                    ws = sorted((w for w in band if cx0 <= (w[0] + w[2]) / 2 < cx1), key=lambda w: w[0])
                    outside_header.append(" ".join(w[4] for w in ws))
        # Another grid starting right at this grid's bottom edge may hold its last rows; totals
        # over such a table are not trusted.
        touches = any(o is not region and abs(o["bbox"][1] - y1) < 3 and o["bbox"][0] < x1 and o["bbox"][2] > x0
                      for o in regions)
        tables.append({"title": title.strip(), "bbox": region["bbox"], "rows": rows,
                       "header_above": outside_header, "touches_below": touches})
    return tables


_HEADING_WORDS = set("""mark type types count qty quantity no number width height thickness depth length size level name
area room rooms door doors window windows frame material matl finish floor base wall walls ceiling notes note comments
comment remarks description family fire rating hardware group set glazing elevation location phase sill head jamb
manufacturer model unit units from to label key keynote category reinforcing reinf ties anchor bolt spacing elev rough
opening top bottom""".split())


def _is_heading_row(row):
    """A row is a heading when most of its non-empty cells are schedule column words."""
    cells = [c["text"].strip() for c in row if c["text"].strip()]
    if not cells:
        return False
    if any(re.search(r"schedule", c, re.I) for c in cells):
        return True
    def heading(text):
        words = re.findall(r"[a-z]+", text.lower())
        return bool(words) and not re.search(r"\d", text) and sum(w in _HEADING_WORDS for w in words) >= max(1, len(words) // 2)
    hits = sum(heading(c) for c in cells)
    return hits >= 2 and hits >= 0.6 * len(cells)


def split_header(rows, header_above=None):
    """Header rows are the leading rows without a digit in their first two cells (after a title row).
    If the grid starts with data, the header drawn just above the grid is used."""
    if header_above and any(re.search(r"\d", c["text"]) for c in rows[0][:2]):
        return list(header_above), rows
    start = None
    # Rows worded like column headings (Mark, Type, Width, Level, Name, Area, ...) or naming the
    # schedule form the header; data starts at the first row after them that is not.
    lead = 0
    while lead < min(len(rows), 6) and _is_heading_row(rows[lead]):
        lead += 1  # the contiguous run of heading rows at the top
    if lead and lead < len(rows):
        start = lead
    if start is None:
        for i, r in enumerate(rows):
            if i > 0 and any(re.search(r"\d", c["text"]) for c in r[:2]):
                start = i
                break
    if start is None:
        return [], rows
    head = rows[:start]
    names = []
    for j in range(len(rows[start])):
        parts = [r[j]["text"] for r in head if j < len(r) and r[j]["text"] and not re.search(r"schedule", r[j]["text"], re.I)]
        names.append(" ".join(parts).strip())
    return names, rows[start:]


if __name__ == "__main__":
    import sys
    import fitz
    page = fitz.open(sys.argv[1])[int(sys.argv[2]) if len(sys.argv) > 2 else 0]
    page.remove_rotation()
    for t in find_tables(page):
        names, body = split_header(t["rows"], t.get("header_above"))
        print(f"== {t['title'][:70]!r} rows={len(t['rows'])} body={len(body)} cols={len(t['rows'][0])}")
        print("   header:", names)
        for r in body[:3]:
            print("   ", [c["text"][:16] for c in r])


# ------------------------------------------------------------------ queries over schedules
_CODE = re.compile(r"(?<![\w'\-])([A-Z]{1,4}\d{0,3}(?:[-.][A-Z0-9]{1,3})?)(?![\w\-])")
_FREEFORM = re.compile(r"\b(if|whose|starts? with|consists? of|each|every|per|average|percent|largest|smallest|most|least)\b", re.I)
_COUNT_HEADER = re.compile(r"^(count|qty|quantity|no\.?|number)$", re.I)


def _cell_tokens(text):
    return {t.strip("()[]:;.") for t in re.split(r"[\s,/&]+", text.strip().upper()) if t.strip("()[]:;.")}


def _norm_dim(text):
    t = text.replace("\u2019", "'").replace("''", '"')
    t = re.sub(r"'\s*-\s*", "'-", t)
    return re.sub(r"\s+", "", t).upper()


def _stems(text):
    """Lower-case words with a plural -s removed, so 'windows' matches a 'WINDOW' title."""
    return {re.sub(r"(?<=[a-z]{3})s$", "", w) for w in re.findall(r"[a-z]+", text.lower())}


# Words that narrow a count to part of a schedule; this parser cannot apply them.
_SCOPE = re.compile(r"\b(floor|floors|level|levels|stor(?:e)?y|storeys|stories|building|wing|phase|zone|area|"
                    r"north|south|east|west|existing|new|demolished|ground|basement|upper|lower|except|excluding|without)\b", re.I)


def answer_count(question, tables):
    """Count schedule entries matching the codes named in a question.

    Codes are matched exactly against whole cells (or their comma/slash parts); codes in one
    column are alternatives (OR), constraints in different columns all apply (AND). If the
    table has a Count/Qty column its values are summed, otherwise rows are counted. Any code
    the table does not contain, or wording this parser does not handle, returns None.
    Returns dict(value, table, rows, basis) or None.
    """
    q = re.sub(r"^\s*on sheet .+? drawings(?:\s*\([^)]*\))?,\s*", "", question, flags=re.I)
    if not re.search(r"\bhow many\b", q, re.I) or _FREEFORM.search(q):
        return None
    if not re.search(r"schedul|listed", q, re.I):
        return None
    words = _stems(q)
    candidates = []
    for t in tables:
        title_words = _stems(t["title"]) - {"schedule", "simplified"}
        if not re.search(r"schedule", t["title"], re.I) or not t.get("header") or len(title_words) > 4:
            continue
        matched = len(title_words & words)
        if matched:
            candidates.append((matched - 0.5 * len(title_words - words), t))
    if not candidates:
        return None
    best = max(c[0] for c in candidates)
    top = [t for sc, t in candidates if sc == best]
    if len(top) > 1:
        # Same title (e.g. a notes box under a schedule): keep tables holding the named codes,
        # then tables with their own count column.
        codes = set(_CODE.findall(q))
        holding = [t for t in top if codes and codes & {tok for r in t["rows"] for c in r["cells"] for tok in _cell_tokens(c)}]
        top = holding or top
        if len(top) > 1:
            counted = [t for t in top if any(_COUNT_HEADER.match(re.sub(r"^(simplified|type)\s+", "", h.strip().lower())) for h in t["header"])]
            top = counted or top
    if len(top) != 1:
        return None
    table = top[0]
    header = [h.lower() for h in table["header"]]
    rows = table["rows"]
    constraints = {}  # column -> set of accepted tokens
    consumed = []
    depth, inside = 0, []
    for ch in q:  # mark characters inside parentheses
        depth += ch == "("
        inside.append(depth > 0)
        depth -= ch == ")" and depth > 0
    matches = list(_CODE.finditer(q))
    outside_found = any(not inside[m.start()] and any(m.group(1) in _cell_tokens(c) for r in rows for c in r["cells"])
                        for m in matches)
    for m in matches:
        code = m.group(1)
        in_parens = inside[m.start()]
        if in_parens and outside_found:
            continue  # the code is named outside; parenthesised words only describe it
        if code in {"A", "I"} and not re.search(r"\bnotes?\s+" + code + r"\b", q):
            continue
        cols = [j for j in range(len(header)) if any(j < len(r["cells"]) and code in _cell_tokens(r["cells"][j]) for r in rows)]
        if not cols:
            if in_parens:
                continue  # a descriptive gloss, e.g. "(2-WIDE (TEMP ALL LOW) ESDH3066)"
            return None  # a named code the table does not contain: do not guess
        if len(cols) > 1:
            # prefer the column whose header the question names (type, material, frame, note, mark)
            named = [j for j in cols if _stems(header[j]) & words]
            if len(named) != 1:
                return None
            cols = named
        constraints.setdefault(cols[0], set()).add(code)
        consumed.append(code)
    for dim, axis in re.findall(r"(\d+\s*'\s*-\s*\d+(?:\s+\d+/\d+)?\s*\")\s*(wide|high|tall)", q):
        cols = [j for j, h in enumerate(header) if ("width" in h if axis == "wide" else "height" in h)]
        if len(cols) != 1:
            return None
        constraints.setdefault(cols[0], set()).add(("dim", _norm_dim(dim)))
    room = re.search(r"\broom\s+(\d{2,4})\b", q, re.I)
    if room:
        cols = [j for j, h in enumerate(header) if "room" in h and ("number" in h or "no" in h.split())]
        if len(cols) != 1:
            return None
        constraints.setdefault(cols[0], set()).add(room.group(1))
    rest = re.sub(r"\([^()]*(?:\([^()]*\)[^()]*)*\)", " ", q)  # drop glosses
    for code in consumed:
        rest = re.sub(r"(?<![\w-])" + re.escape(code) + r"(?![\w-])", " ", rest)
    rest = re.sub(r"\d+\s*'\s*-\s*\d+(?:\s+\d+/\d+)?\s*\"", " ", rest)
    rest = re.sub(r"\broom\s+\d{2,4}\b", " ", rest, flags=re.I)
    safe = set("""how many doors door windows window items item rooms room entries entry schedule scheduled listed
        list lists in on of the a an are is there total type types mark marks material materials frame frames note notes
        carry carries have has with for does do and or all wide high tall counted assemblies assembly""".split())
    extra = [w for w in re.findall(r"[a-z]+", rest.lower()) if w not in safe]
    if extra:
        # With a code fixing the rows, remaining words describe that code ("unit entry doors
        # (type U01)"). Words that narrow the scope, or stray numbers, still abstain.
        if not consumed or _SCOPE.search(rest) or re.search(r"\d", rest):
            return None
    selected = []
    for r in rows:
        ok = True
        for j, accepted in constraints.items():
            cell = r["cells"][j] if j < len(r["cells"]) else ""
            toks = _cell_tokens(cell)
            if not any((a[1] == _norm_dim(cell)) if isinstance(a, tuple) else a in toks for a in accepted):
                ok = False
                break
        if ok and any(c.strip() for c in r["cells"]):
            selected.append(r)
    if not constraints and table.get("touches_below"):
        return None  # a total over a table that may continue in an adjacent grid
    count_cols = [j for j, h in enumerate(table["header"]) if _COUNT_HEADER.match(re.sub(r"^(simplified|type)\s+", "", h.strip().lower()))]
    if len(count_cols) == 1:
        j = count_cols[0]
        values = []
        for r in selected:
            cell = r["cells"][j].strip() if j < len(r["cells"]) else ""
            if not re.fullmatch(r"\d+", cell):
                return None
            values.append(int(cell))
        return {"value": sum(values), "table": table, "rows": selected, "terms": values,
                "basis": f"sum of the '{table['header'][j]}' column over {len(selected)} matching rows"}
    return {"value": len(selected), "table": table, "rows": selected, "terms": None,
            "basis": f"{len(selected)} matching schedule rows"}

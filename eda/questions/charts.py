"""Decision-relevant charts for the questions EDA. Run after analyze.py: python -I charts.py"""
import os as _os  # portable paths, added when this script was copied into the repo
_ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))  # repository root
import sys
sys.path.insert(0, _ROOT + "/eda/questions")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib.colors import LinearSegmentedColormap
from qlib import WORK

# Reference palette (dataviz skill, light mode); validated with validate_palette.js (adjacent pairs pass).
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQ = ["#fcfcfb", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
plt.rcParams.update({"font.family": "sans-serif", "font.size": 10, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": INK2, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.grid": False, "axes.titlecolor": INK, "axes.titlesize": 12, "axes.titleweight": "bold",
                     "axes.titlelocation": "left", "legend.frameon": False})
DPI = 150
q = pd.read_csv(WORK + "questions_annotated.csv")
SRC_ORDER = ["cubicasa5k", "swiss_dwellings", "ifc_models", "ifc_bench", "opening_design"]


def clean(ax, xgrid=True):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(AXIS)
    ax.spines["bottom"].set_color(AXIS)
    if xgrid:
        ax.xaxis.grid(True, color=GRID, linewidth=0.7)
        ax.set_axisbelow(True)


# 1. Questions by source: English originals vs translated twins, and type mix
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 3.6), dpi=DPI, gridspec_kw={"width_ratios": [1, 1.15]})
y = np.arange(len(SRC_ORDER))[::-1]
en = q[q.lang == "en"].groupby("source").size().reindex(SRC_ORDER).fillna(0)
tr = q[q.lang != "en"].groupby("source").size().reindex(SRC_ORDER).fillna(0)
a1.barh(y, en, height=0.55, color=CAT[0], edgecolor=SURF, linewidth=1, label="English original")
a1.barh(y, tr, left=en, height=0.55, color=CAT[1], edgecolor=SURF, linewidth=1, label="Translated twin (fi, de, fr, it, et, da)")
for yi, s in zip(y, SRC_ORDER):
    a1.text(en[s] + tr[s] + 60, yi, f"{int(en[s] + tr[s]):,}", va="center", color=INK2, fontsize=9)
a1.set_yticks(y, SRC_ORDER)
a1.set_xlim(0, 5000)
a1.set_title("Questions per source (n = 7,990)")
a1.legend(loc="lower right", fontsize=8.5)
clean(a1)
types = ["count", "area", "length", "volume", "text"]
mix = pd.crosstab(q.source, q.type).reindex(index=SRC_ORDER, columns=types).fillna(0)
share = mix.div(mix.sum(axis=1), axis=0) * 100
left = np.zeros(len(SRC_ORDER))
for i, t in enumerate(types):
    a2.barh(y, share[t], left=left, height=0.55, color=CAT[i], edgecolor=SURF, linewidth=1, label=t)
    for yi, s, l, v in zip(y, SRC_ORDER, left, share[t]):
        if v >= 9:
            a2.text(l + v / 2, yi, f"{v:.0f}%", va="center", ha="center", fontsize=8, color="#0b0b0b" if t == "volume" else "#ffffff")
    left += share[t].values
a2.set_yticks(y, [""] * len(y))
a2.set_xlim(0, 100)
a2.set_xlabel("share of the source's questions (%)")
a2.set_title("Answer type mix per source")
a2.legend(ncol=5, loc="upper left", bbox_to_anchor=(0, -0.2), fontsize=8.5)
clean(a2)
fig.tight_layout()
fig.savefig(WORK + "chart1_questions_by_source_type.png")
plt.close(fig)

# 2. Template coverage curves
tm = pd.read_csv(WORK + "templates.csv")
fam = pd.read_csv(WORK + "families.csv")
en_t = q[q.lang == "en"].groupby(["source", "template"]).size().sort_values(ascending=False)
curves = [("Language-specific templates, all questions", tm.n.sort_values(ascending=False).values, len(q), CAT[0]),
          ("English templates, English questions only", en_t.values, (q.lang == "en").sum(), CAT[1]),
          ("Cross-language families (intents)", fam.n.sort_values(ascending=False).values, len(q), CAT[2])]
fig, ax = plt.subplots(figsize=(8.5, 4.6), dpi=DPI)
for name, v, tot, c in curves:
    cum = np.cumsum(v) / tot * 100
    k = np.arange(1, len(v) + 1)
    ax.plot(k, cum, color=c, linewidth=2, solid_capstyle="round", label=f"{name} ({len(v)})")
    if len(v) >= 20:
        ax.plot([20], [cum[19]], "o", color=c, markersize=7, markeredgecolor=SURF, markeredgewidth=1.5)
        ax.annotate(f"{cum[19]:.0f}%", (20, cum[19]), xytext=(8, -4), textcoords="offset points", fontsize=9, color=INK)
ax.axvline(20, color=AXIS, linewidth=0.8)
ax.text(21, 4, "top 20", color=MUTED, fontsize=8.5)
ax.set_xscale("log")
ax.set_xlim(1, 500)
ax.set_ylim(0, 101)
ax.set_xlabel("number of templates, most frequent first (log scale)")
ax.set_ylabel("cumulative share of questions (%)")
ax.set_title("Template coverage: top 20 cover 58% of all lines, 83% of English lines")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
ax.legend(loc="lower right", fontsize=8.5)
clean(ax)
ax.yaxis.grid(True, color=GRID, linewidth=0.7)
fig.tight_layout()
fig.savefig(WORK + "chart2_template_coverage.png")
plt.close(fig)

# 3. Grounding scope (English questions = unique intents per drawing)
GMAP = {"whole_drawing": "Whole drawing (symbol or room counts, floor total)", "named_label_set": "All rooms carrying a quoted label",
        "named_room": "One room by id or name", "named_apartment": "One apartment by letter", "level": "One IFC storey (by name)",
        "level_report": "One IFC storey (by name)", "whole_model": "Whole IFC model (20 of 21 asked on a floor-plan PDF)",
        "building_report": "Whole-building report (IFC-Bench)", "named_entity_report": "One room or element in a report question",
        "table_all": "Schedule table on a named sheet", "table_filter": "Schedule table on a named sheet", "table_row": "Schedule table on a named sheet",
        "plan_detail": "Enlarged plan detail on a named sheet"}
e = q[q.lang == "en"].copy()
e["scope"] = e.grounding.map(GMAP)
sc = e.scope.value_counts().sort_values()
fig, ax = plt.subplots(figsize=(9, 4.2), dpi=DPI)
ax.barh(range(len(sc)), sc.values, height=0.6, color=CAT[0])
for i, v in enumerate(sc.values):
    ax.text(v + 25, i, f"{v:,}  ({v / len(e):.1%})", va="center", fontsize=8.5, color=INK2)
ax.set_yticks(range(len(sc)), sc.index, fontsize=9)
ax.set_xlim(0, sc.max() * 1.25)
ax.set_xlabel("English questions (n = 4,152; translated twins excluded)")
ax.set_title("What must be located before answering")
clean(ax)
fig.tight_layout()
fig.savefig(WORK + "chart3_grounding_scope.png")
plt.close(fig)

# 4. Count answer distribution per family: zeros are common in some families
c = e[(e.type == "count") & e.source.isin(["cubicasa5k", "swiss_dwellings"])].copy()
c["v"] = c.answer.astype(float)
bins = [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 10.5, 20.5, 1e9]
labels = ["0", "1", "2", "3", "4", "5", "6-10", "11-20", "21+"]
c["bin"] = pd.cut(c.v, bins, labels=labels)
c["row"] = c.source.str.replace("_dwellings", "").str.replace("5k", "") + " · " + c.family.str.replace("count_", "")
tab = pd.crosstab(c.row, c.bin, normalize="index").reindex(columns=labels).fillna(0) * 100
n = c.groupby("row").size()
tab = tab.loc[tab["0"].sort_values(ascending=False).index]
cmap = LinearSegmentedColormap.from_list("seqblue", SEQ)
fig, ax = plt.subplots(figsize=(9, 7.2), dpi=DPI)
im = ax.imshow(tab.values, aspect="auto", cmap=cmap, vmin=0, vmax=100)
ax.set_xticks(range(len(labels)), labels)
ax.set_yticks(range(len(tab)), [f"{r}  (n={n[r]})" for r in tab.index], fontsize=8.5)
for i in range(tab.shape[0]):
    for j in range(tab.shape[1]):
        v = tab.values[i, j]
        if v >= 15 or (j == 0 and v > 0):
            ax.text(j, i, f"{v:.0f}%" if v >= 1 else "<1%", ha="center", va="center", fontsize=7.5, color="#ffffff" if v >= 55 else INK)
ax.set_xticks(np.arange(-.5, len(labels)), minor=True)
ax.set_yticks(np.arange(-.5, len(tab)), minor=True)
ax.grid(which="minor", color=SURF, linewidth=1.5)
ax.tick_params(which="minor", length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.set_xlabel("ground-truth count")
ax.set_title("Count answers by family (English questions)")
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
cb.set_label("share of the family's questions (%)", color=INK2)
cb.outline.set_visible(False)
fig.tight_layout()
fig.savefig(WORK + "chart4_count_answers_by_family.png")
plt.close(fig)

# 5. Area answers (m2) and what the 2% tolerance means in absolute terms
a = e[(e.unit == "m2")].copy()
a["v"] = a.answer.astype(float)
edges = np.logspace(np.log10(1), np.log10(1500), 34)
fig, ax = plt.subplots(figsize=(9, 4.4), dpi=DPI)
for i, (src, lab) in enumerate([("swiss_dwellings", "swiss_dwellings (PDF)"), ("ifc_models", "ifc_models (IFC or IFC-rendered PDF)")]):
    v = a[a.source == src].v
    h, _ = np.histogram(v, edges)
    ax.stairs(h, edges, color=CAT[i], linewidth=2, label=f"{lab}, n={len(v)}")
for ref in [2, 5, 10, 50, 500]:
    ax.axvline(ref, color=GRID, linewidth=0.8, zorder=0)
ymax = ax.get_ylim()[1]
for ref in [2, 5, 10, 50, 500]:
    ax.text(ref * 1.05, ymax * 0.62 if ref == 5 else ymax * 0.93, f"±{0.02 * ref:.2g} m²\nat {ref} m²", fontsize=7.5, color=MUTED, va="top")
ax.set_xscale("log")
ax.set_xlabel("ground-truth area (m², log scale)")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
ax.set_ylabel("English questions")
small = (a.v < 5).mean()
ax.set_title(f"Area answers (m²): {small:.0%} are under 5 m², where 2% is under ±0.1 m²")
ax.legend(loc="upper right", bbox_to_anchor=(1, 0.78), fontsize=8.5)
clean(ax)
ax.xaxis.grid(False)
ax.yaxis.grid(True, color=GRID, linewidth=0.7)
fig.tight_layout()
fig.savefig(WORK + "chart5_area_answers_tolerance.png")
plt.close(fig)
print("charts written")

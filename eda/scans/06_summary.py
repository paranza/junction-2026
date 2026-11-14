"""Per-source summaries, worst-file flags and charts from metrics.csv. Outputs: summary_by_source.csv,
flags_worst.csv, fig_resolution.png, fig_quality.png (single hue; sources are named on the axis)."""
import pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = pathlib.Path(__file__).parent
d = pd.read_csv(OUT / "metrics.csv")
SRC = ["europeana", "finna", "habs", "wikimedia"]
d["abs_skew"] = d["skew_proj"].abs()
d["colour_class"] = np.select(
    [d["mode"].eq("L"), d["chroma_p99"] < 15, d["colour_std"] < 12],
    ["grayscale (L)", "RGB but gray", "tinted mono"], "colour")
d["long_side"] = d[["width", "height"]].max(axis=1)
d["at_3000_cap"] = d["long_side"].eq(3000)

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
num = ["long_side", "mp", "aspect", "bytes", "bytes_per_px", "jpeg_q", "lap_var", "lap_var_1500", "acutance", "noise_sigma",
       "bg_resid_std", "speckle_per_mp", "rms_contrast", "range_contrast", "otsu_eta", "fisher", "midtone_frac", "abs_skew",
       "skew_support", "bg_uneven", "dark_border", "colour_std", "tint", "text_h_p50", "n_words", "ink_frac_otsu"]
rows = []
for s in SRC:
    g = d[d.source == s]
    r = {"source": s, "n": len(g), "share_at_3000px_cap": g.at_3000_cap.mean(), "share_inverted": g.inverted.mean(),
         "share_landscape": (g.orientation == "landscape").mean()}
    for c in num:
        q = g[c].quantile([0.1, 0.5, 0.9])
        r[f"{c}_p10"], r[f"{c}_p50"], r[f"{c}_p90"] = q.values
    for k, v in g.colour_class.value_counts().items():
        r[f"cls_{k}"] = v
    rows.append(r)
summ = pd.DataFrame(rows)
summ.to_csv(OUT / "summary_by_source.csv", index=False)
show = ["long_side", "mp", "aspect", "bytes", "jpeg_q", "lap_var_1500", "acutance", "noise_sigma", "bg_resid_std", "speckle_per_mp",
        "range_contrast", "otsu_eta", "midtone_frac", "abs_skew", "bg_uneven", "dark_border", "text_h_p50"]
print(summ[["source", "n", "share_at_3000px_cap", "share_inverted", "share_landscape"] + [c for c in summ.columns if c.startswith("cls_")]].to_string(index=False))
for c in show:
    print(f"{c:16s}", "  ".join(f"{s[:5]} p10={summ.loc[i, c+'_p10']:.3g} p50={summ.loc[i, c+'_p50']:.3g} p90={summ.loc[i, c+'_p90']:.3g}" for i, s in enumerate(SRC)))
print("mode counts\n", pd.crosstab(d.source, d["mode"]).to_string())
print("jpeg_q counts\n", pd.crosstab(d.source, d.jpeg_q).to_string())
print("dpi values\n", d.dpi.fillna("none").value_counts().head(8).to_string())

# worst-file flags: rank-based so units do not matter. Higher concern = worse.
concern = pd.DataFrame({
    "blur": -d["acutance"].rank(pct=True) + 1,          # low acutance = blurry
    "noise": d["bg_resid_std"].rank(pct=True),
    "speckle": d["speckle_per_mp"].rank(pct=True),
    "low_contrast": -d["fisher"].rank(pct=True) + 1,
    "skew": d["abs_skew"].rank(pct=True),
    "uneven_bg": d["bg_uneven"].rank(pct=True),
})
d["concern_score"] = concern.mean(axis=1)
for c in concern:
    d[f"rank_{c}"] = concern[c]
cols = ["source", "file", "width", "height", "colour_class", "inverted", "acutance", "lap_var_1500", "noise_sigma", "bg_resid_std",
        "speckle_per_mp", "fisher", "range_contrast", "skew_proj", "skew_hough", "bg_uneven", "dark_border", "midtone_frac",
        "text_h_p50", "concern_score"]
d.sort_values("concern_score", ascending=False)[cols].to_csv(OUT / "flags_worst.csv", index=False)
d.to_csv(OUT / "metrics_enriched.csv", index=False)

# charts: small multiples, one hue, sources on the axis
BLUE, INK, MUTED = "#2a78d6", "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e1", "grid.linewidth": 0.6})
rng = np.random.default_rng(0)


def strip(ax, col, title, log=False, ref=None):
    for i, s in enumerate(SRC):
        v = d.loc[d.source == s, col].dropna().values
        ax.scatter(i + rng.uniform(-0.18, 0.18, len(v)), v, s=9, color=BLUE, alpha=0.55, linewidths=0)
        if len(v):
            ax.hlines(np.median(v), i - 0.3, i + 0.3, color=INK, linewidth=2)
    ax.set_xticks(range(len(SRC)), [f"{s}\n(n={int((d.source == s).sum())})" for s in SRC])
    ax.set_title(title, loc="left", fontsize=9, color=INK)
    if log:
        ax.set_yscale("log")
    if ref is not None:
        ax.axhline(ref[0], color=MUTED, linestyle=(0, (3, 3)), linewidth=0.8)
        ax.text(len(SRC) - 0.5, ref[0], ref[1], ha="right", va="bottom", fontsize=7, color=MUTED)


fig, axs = plt.subplots(2, 2, figsize=(11, 7.5))
strip(axs[0, 0], "long_side", "Long side (px). Dataset caps scans at 3,000 px", ref=(3000, "3,000 px cap"))
strip(axs[0, 1], "mp", "Megapixels")
strip(axs[1, 0], "aspect", "Aspect ratio (long / short side)", ref=(1.414, "ISO A-series 1.414"))
strip(axs[1, 1], "bytes", "File size (bytes, log scale)", log=True)
fig.suptitle("Scan sources: resolution and size per file (black bar = median)", x=0.01, ha="left", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "fig_resolution.png", dpi=130); plt.close(fig)

fig, axs = plt.subplots(3, 3, figsize=(13, 10.5))
strip(axs[0, 0], "acutance", "Sharpness: edge acutance (log; higher = crisper edges)", log=True)
strip(axs[0, 1], "lap_var_1500", "Sharpness: Laplacian variance at 1,500 px (log)", log=True)
strip(axs[0, 2], "text_h_p50", "Median lettering height proxy (px, native)", ref=(10, "10 px"))
strip(axs[1, 0], "bg_resid_std", "Paper noise: residual std on flat paper (grey levels)")
strip(axs[1, 1], "speckle_per_mp", "Speckle: 1-6 px blobs per megapixel (log)", log=True)
strip(axs[1, 2], "fisher", "Ink/paper separation (Fisher ratio, log; low = faint)", log=True)
strip(axs[2, 0], "abs_skew", "Absolute skew (deg, projection profile)", ref=(0.5, "0.5 deg"))
strip(axs[2, 1], "bg_uneven", "Background unevenness ((p95-p5)/median)")
strip(axs[2, 2], "colour_std", "Colour variation (Hasler-Suesstrunk std term)")
fig.suptitle("Scan sources: image-quality metrics per file (black bar = median)", x=0.01, ha="left", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "fig_quality.png", dpi=120); plt.close(fig)
print("charts written")

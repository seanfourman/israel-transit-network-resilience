"""Regenerate the structural-metrics comparison figure in a clean, print-friendly
(black-and-white) style, sized to stay legible when placed small in the report.

Highlights the real network (dark) and the configuration-model control
(mid-grey); the other null models recede to light grey. Saves a crisp PNG to
reports/figures/ .
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "outputs" / "nb" / "10_network_model_comparison" / "tables" / "network_model_comparison.csv"
OUT_DIR = REPO / "reports" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

d = pd.read_csv(CSV, encoding="utf-8-sig")

# short, language-neutral labels in the row order of the CSV
LABEL = {
    "real_transit": "Real",
    "erdos_renyi_gnm": "ER",
    "configuration_degree_sequence": "Config",
    "barabasi_albert_matched": "BA",
    "watts_strogatz_matched": "WS",
}
# Okabe-Ito colour-blind-safe palette: one fixed hue per model (real = blue anchor)
PALETTE = {
    "real_transit": "#0072B2",
    "erdos_renyi_gnm": "#E69F00",
    "configuration_degree_sequence": "#009E73",
    "barabasi_albert_matched": "#CC79A7",
    "watts_strogatz_matched": "#D55E00",
}

d = d[d["model"].isin(LABEL)].copy()
d["label"] = d["model"].map(LABEL)
d["color"] = d["model"].map(PALETTE)

PANELS = [
    ("average_clustering", "Average clustering"),
    ("transitivity", "Transitivity"),
    ("approx_average_shortest_path", "Avg. shortest path (hops)"),
]


import math


def fmt(v):
    """Plain decimal (never scientific): 13.8, 0.097, 0.000031, 0.00013 ..."""
    if v >= 1:
        return f"{v:.1f}"
    if v >= 0.01:
        return f"{v:.3f}"
    if v <= 0:
        return "0"
    decimals = -int(math.floor(math.log10(v))) + 1   # ~2 significant figures
    return f"{v:.{decimals}f}"


plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "axes.linewidth": 0.8})

fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.3), dpi=200)

for ax, (col, title) in zip(axes, PANELS):
    vals = d[col].values
    bars = ax.bar(d["label"], vals, color=d["color"], edgecolor="#5b6672",
                  linewidth=0.6, width=0.72, zorder=3)
    ax.set_title(title, fontsize=15, fontweight="bold", color="#1f2933", pad=8)
    top = vals.max()
    ax.set_ylim(0, top * 1.20)
    # value labels — rotate the near-zero ones to vertical so they don't collide
    for b, v in zip(bars, vals):
        small = v < 0.08 * top
        ax.annotate(fmt(v), (b.get_x() + b.get_width() / 2, b.get_height()),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom",
                    rotation=90 if small else 0,
                    fontsize=10.5 if small else 11.5, color="#1f2933")
    # clean chrome
    ax.yaxis.grid(True, color="#e7eaee", linewidth=0.9, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#9aa4af")
    ax.tick_params(axis="x", labelsize=13, colors="#1f2933", length=0)
    ax.tick_params(axis="y", labelsize=11.5, colors="#5b6672")

# Abbreviation key baked into the figure (LTR — avoids RTL/bidi jumbling in Word)
key = ("Real: real transit    ·    ER: Erdős–Rényi    ·    "
       "Config: configuration    ·    BA: Barabási–Albert    ·    "
       "WS: Watts–Strogatz")
fig.tight_layout(pad=1.2, w_pad=2.0, rect=[0, 0.08, 1, 1])
fig.text(0.5, 0.03, key, ha="center", va="bottom", fontsize=9.5, color="#5b6672")
out = OUT_DIR / "model_metric_comparison.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", out)
print("size:", out.stat().st_size // 1024, "KB")

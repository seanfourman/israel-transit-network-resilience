"""Regenerate the centrality-correlation heatmap in a clean, print-friendly style.

Sequential light->navy colour ramp (prints cleanly in black-and-white, unlike a
red-blue diverging map), large fonts so every cell stays legible when the figure
is placed small, and a subtle box on the headline cell (weighted degree vs
betweenness = 0.19). Saves a crisp PNG to reports/figures/ .
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "outputs" / "nb" / "04_centrality_analysis" / "tables" / "centrality_correlation_spearman.csv"
OUT = REPO / "reports" / "figures" / "centrality_correlation.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

d = pd.read_csv(CSV, encoding="utf-8-sig", index_col=0)
M = d.values
labels = ["degree", "weighted\ndegree", "PageRank", "betweenness", "harmonic"]
n = len(labels)

# sequential ramp: light -> report navy (grayscale-safe)
cmap = LinearSegmentedColormap.from_list(
    "navyseq", ["#f3f6f9", "#cdd9e6", "#93aecb", "#4d719b", "#1d3a5f"])

plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"]})
fig, ax = plt.subplots(figsize=(6.4, 5.6), dpi=200)
im = ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="equal")

# cell annotations — white on dark cells, dark on light
for i in range(n):
    for j in range(n):
        v = M[i, j]
        ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                fontsize=14, fontweight=("bold" if i == j else "normal"),
                color=("white" if v >= 0.58 else "#1f2933"))

# highlight the headline dissociation cell(s): weighted degree x betweenness
key = [(1, 3), (3, 1)]
for (i, j) in key:
    ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                           edgecolor="#1f2933", linewidth=2.8, zorder=5))

ax.set_xticks(range(n)); ax.set_yticks(range(n))
ax.set_xticklabels(labels, fontsize=12.5, rotation=32, ha="right")
ax.set_yticklabels([l.replace("\n", " ") for l in labels], fontsize=12.5)
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("Spearman correlation between centrality measures",
             fontsize=13.5, fontweight="bold", color="#1f2933", pad=12)

cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
cbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
cbar.ax.tick_params(labelsize=10.5)
cbar.outline.set_visible(False)

fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT, "|", OUT.stat().st_size // 1024, "KB")

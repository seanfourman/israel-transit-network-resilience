"""Regenerate the criticality-lens agreement heatmap (fig 10).

A 7x7 Spearman matrix between the criticality definitions. Because the values run
negative-to-positive, this uses a DIVERGING blue-white-red map (white at 0), not
the sequential ramp of the centrality heatmap. Pairs with no shared coverage are
left blank. Saved to reports/figures/ .
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "outputs" / "nb" / "23_critical_station_lenses" / "tables" / "lens_agreement.csv"
OUT = REPO / "reports" / "figures" / "lens_agreement_heatmap.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

ORDER = ["betweenness", "service_volume", "articulation", "no_walk_alternative",
         "demand_weighted", "peak_hour", "closure_time_cost"]
LABEL = ["betweenness", "service\nvolume", "articulation", "no-walk\nalternative",
         "demand", "peak hour", "closure\ncost"]
idx = {n: i for i, n in enumerate(ORDER)}
n = len(ORDER)

d = pd.read_csv(CSV, encoding="utf-8-sig")
M = np.full((n, n), np.nan)
for i in range(n):
    M[i, i] = 1.0
for r in d.itertuples():
    if r.lens_a in idx and r.lens_b in idx and pd.notna(r.spearman_rho):
        i, j = idx[r.lens_a], idx[r.lens_b]
        M[i, j] = M[j, i] = r.spearman_rho

cmap = LinearSegmentedColormap.from_list(
    "div", ["#2166ac", "#92c5de", "#f7f7f7", "#f4a582", "#b2182b"])
cmap.set_bad("#eef1f4")   # NaN cells -> faint grey

plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"]})
fig, ax = plt.subplots(figsize=(7.4, 6.4), dpi=200)
im = ax.imshow(np.ma.masked_invalid(M), cmap=cmap, vmin=-0.85, vmax=0.85, aspect="equal")

for i in range(n):
    for j in range(n):
        v = M[i, j]
        if np.isnan(v):
            ax.text(j, i, "–", ha="center", va="center", fontsize=13, color="#9aa4af")
            continue
        ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                fontsize=12.5, fontweight=("bold" if i == j else "normal"),
                color=("white" if abs(v) >= 0.6 else "#1f2933"))

ax.set_xticks(range(n)); ax.set_yticks(range(n))
ax.set_xticklabels(LABEL, fontsize=10.5, rotation=32, ha="right")
ax.set_yticklabels([l.replace("\n", " ") for l in LABEL], fontsize=10.5)
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.set_title("Agreement between the seven criticality definitions",
             fontsize=13.5, fontweight="bold", color="#1f2933", pad=12)

cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
cbar.set_ticks([-0.8, -0.4, 0, 0.4, 0.8])
cbar.set_label("Spearman ρ", fontsize=11, color="#1f2933")
cbar.ax.tick_params(labelsize=10)
cbar.outline.set_visible(False)

fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT, "|", OUT.stat().st_size // 1024, "KB")
print("NaN pairs:", [(ORDER[i], ORDER[j]) for i in range(n) for j in range(i + 1, n) if np.isnan(M[i, j])])

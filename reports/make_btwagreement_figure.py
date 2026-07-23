"""Regenerate the betweenness rank-agreement figure (fig 8) in the report palette.

Three log-log scatters of station rank under two betweenness variants. The first
two compare travel-time weighting against hop-count (they disagree, rho 0.61 /
0.59); the third compares two hop-count runs and is the sampling noise floor
(rho 0.96). The 500 top-by-travel-time stations are highlighted so the reader can
see the important stations move too. Saved to reports/figures/ .
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "outputs" / "nb" / "18_travel_time_network" / "tables" / "betweenness_traveltime.csv"
OUT = REPO / "reports" / "figures" / "betweenness_agreement.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

d = pd.read_csv(CSV, encoding="utf-8-sig")
top = d["rank_traveltime"] <= 500          # top-500 stations by travel-time betweenness

PANELS = [
    ("rank_hop_control", "rank_traveltime", "Hop-count rank", "Travel-time rank",
     "Travel-time vs hop-count", 0.61),
    ("rank_hop_nb04", "rank_traveltime", "Hop-count rank (earlier run)", "Travel-time rank",
     "Travel-time vs earlier hop-count", 0.59),
    ("rank_hop_nb04", "rank_hop_control", "Hop-count rank (earlier run)", "Hop-count rank",
     "Hop-count vs hop-count  =  noise floor", 0.96),
]

BASE, HL = "#0072B2", "#D55E00"
plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"]})
fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.7), dpi=200)

hi = int(max(d["rank_traveltime"].max(), d["rank_hop_control"].max(), d["rank_hop_nb04"].max()))
for ax, (xc, yc, xl, yl, title, rho) in zip(axes, PANELS):
    ax.plot([1, hi], [1, hi], ls="--", lw=1.4, color="#1f2933", zorder=1)
    ax.scatter(d.loc[~top, xc], d.loc[~top, yc], s=3, color=BASE, alpha=0.10,
               edgecolors="none", zorder=2)
    ax.scatter(d.loc[top, xc], d.loc[top, yc], s=13, color=HL, alpha=0.55,
               edgecolors="none", zorder=3, label="top 500 by travel time")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(1, hi * 1.1); ax.set_ylim(1, hi * 1.1)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=12, fontweight="bold", color="#1f2933", pad=6)
    ax.set_xlabel(xl, fontsize=11, color="#1f2933")
    ax.set_ylabel(yl, fontsize=11, color="#1f2933")
    ax.tick_params(labelsize=9.5, colors="#5b6672")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#9aa4af")
    ax.text(0.05, 0.95, f"ρ = {rho:.2f}", transform=ax.transAxes, ha="left", va="top",
            fontsize=15, fontweight="bold", color="#1f2933",
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#c8d0d8", lw=1.2))

axes[0].legend(loc="lower right", fontsize=9.5, frameon=True, framealpha=0.95, markerscale=1.4)
fig.suptitle("Betweenness rank agreement  -  closer to the diagonal = more agreement",
             fontsize=13.5, fontweight="bold", color="#1f2933", y=1.0)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT, "|", OUT.stat().st_size // 1024, "KB")

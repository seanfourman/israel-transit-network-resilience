"""Regenerate the dual-panel resilience-curve figure in a print-friendly style.

Seven series are distinguished by LINE STYLE + grey level (not colour alone), so
the chart stays readable in black-and-white: degree (dark solid) and betweenness
(dark dashed) carry the story, random and the (N-k)/N ceiling are reference lines,
the rest recede to light grey. Saved to reports/figures/ .
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "outputs" / "nb" / "06_robustness_analysis" / "tables" / "disruption_results.csv"
OUT = REPO / "reports" / "figures" / "resilience_curves.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

d = pd.read_csv(CSV, encoding="utf-8-sig")
N = int(d.loc[d["removed"] == 0, "surviving_nodes"].max())

# draw order (bottom of the band -> top) and per-series style
STYLE = {
    "degree":              dict(color="#1f2933", ls="-",  lw=2.4, label="degree (most damaging)"),
    "betweenness":         dict(color="#1f2933", ls="--", lw=2.0, label="betweenness"),
    "articulation points": dict(color="#5b6672", ls="-",  lw=1.6, label="articulation points"),
    "pagerank":            dict(color="#5b6672", ls=(0, (4, 2)), lw=1.4, label="PageRank"),
    "weighted degree":     dict(color="#9aa4af", ls="-",  lw=1.5, label="weighted degree"),
    "random (baseline)":   dict(color="#7f8a97", ls="-.", lw=2.0, label="random (baseline)"),
}

plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"]})
fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.2, 4.6), dpi=200, sharey=True)

for ax, ycol, sub in [(axL, "lcc_share_original", "Share of the original stations"),
                      (axR, "lcc_share_surviving", "Share of the surviving stations (corrected)")]:
    for strat, st in STYLE.items():
        s = d[d["strategy"] == strat].sort_values("removed")
        ax.plot(s["removed"], s[ycol], solid_capstyle="round", zorder=3, **st)
    # (N-k)/N ceiling
    k = np.sort(d["removed"].unique())
    ceil = (N - k) / N if ycol == "lcc_share_original" else np.ones_like(k, dtype=float)
    ax.plot(k, ceil, color="#c2cad2", ls=":", lw=1.8, zorder=2, label="ceiling (N−k)/N")
    ax.set_title(sub, fontsize=12, color="#1f2933", pad=6)
    ax.set_xlabel("Stations removed (k)", fontsize=11.5, color="#1f2933")
    ax.tick_params(labelsize=10.5, colors="#5b6672")
    ax.grid(True, color="#eef1f4", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color("#9aa4af")
axL.set_ylabel("Largest-component share", fontsize=11.5, color="#1f2933")
axL.set_ylim(0.28, 1.02)

fig.suptitle("Network resilience: targeted attack vs random failure",
             fontsize=14, fontweight="bold", color="#1f2933", y=1.0)
handles, labels = axL.get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=10.3,
           frameon=False, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=[0, 0.09, 1, 0.96])
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT, "| N =", N, "|", OUT.stat().st_size // 1024, "KB")

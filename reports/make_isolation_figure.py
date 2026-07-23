"""Regenerate the critical-station isolation bar chart in the report's clean style.

Replaces the green/red encoding (indistinguishable in grayscale and colour-blind
unfriendly) with light bars for substitutable stops and dark bars for the genuine
single points of failure. Large fonts, saved to reports/figures/ .
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "outputs" / "nb" / "05_critical_station_isolation" / "tables" / "isolation_summary.csv"
OUT = REPO / "reports" / "figures" / "critical_isolation.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

d = pd.read_csv(CSV, encoding="utf-8-sig")
LIGHT, DARK = "#9aa8ba", "#26313d"
d["color"] = d["verdict"].map({"substitutable": LIGHT, "isolated": DARK})

plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"]})
fig, ax = plt.subplots(figsize=(8.4, 4.6), dpi=200)

bars = ax.bar(d["distance_band"], d["n_critical_stops"], color=d["color"],
              edgecolor="#5b6672", linewidth=0.6, width=0.66, zorder=3)

top = d["n_critical_stops"].max()
ax.set_ylim(0, top * 1.16)
for b, cnt, sh in zip(bars, d["n_critical_stops"], d["share_pct"]):
    pct = f"{sh:.0f}%" if sh >= 5 else f"{sh:.1f}%"
    ax.annotate(f"{cnt:,}\n({pct})", (b.get_x() + b.get_width() / 2, b.get_height()),
                xytext=(0, 4), textcoords="offset points",
                ha="center", va="bottom", fontsize=11, color="#1f2933")

ax.set_title("Does a critical stop have a walkable alternative?",
             fontsize=14, fontweight="bold", color="#1f2933", pad=10)
ax.set_xlabel("Distance to the nearest alternative stop", fontsize=12.5, color="#1f2933")
ax.set_ylabel("Number of critical stops", fontsize=12.5, color="#1f2933")
ax.tick_params(axis="x", labelsize=12, colors="#1f2933", length=0)
ax.tick_params(axis="y", labelsize=11, colors="#5b6672")
ax.yaxis.grid(True, color="#eef1f4", linewidth=0.9, zorder=0)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color("#9aa4af")

legend = [
    Patch(facecolor=LIGHT, edgecolor="#5b6672", label="Substitutable - alternative within 300 m (98.2%)"),
    Patch(facecolor=DARK, edgecolor="#5b6672", label="Isolated - genuine single point of failure (1.8%)"),
]
ax.legend(handles=legend, loc="upper right", fontsize=11, frameon=True, framealpha=0.95)

fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT, "|", OUT.stat().st_size // 1024, "KB")

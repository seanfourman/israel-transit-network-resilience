"""Regenerate the link-prediction figure (fig 9) in the report palette.

Grouped horizontal bars per method: AUC on easy random negatives (light blue)
vs 2-hop hard negatives (orange). Every method that looked strong on random
negatives collapses below the 0.5 random-guessing line once the negatives are
hard. Saved to reports/figures/ .
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "outputs" / "nb" / "13_embeddings_link_prediction" / "tables" / "link_prediction_hard_negatives.csv"
OUT = REPO / "reports" / "figures" / "link_prediction_auc.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

d = pd.read_csv(CSV, encoding="utf-8-sig").sort_values("auc_random_negatives", kind="stable")
methods = d["method"].tolist()
y = np.arange(len(d))
RANDOM, HARD = "#8CC1E3", "#D55E00"

plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"]})
fig, ax = plt.subplots(figsize=(9.6, 5.2), dpi=200)

b1 = ax.barh(y + 0.20, d["auc_random_negatives"], height=0.38, color=RANDOM,
             edgecolor="#5b6672", linewidth=0.5, zorder=3, label="Random negatives (easy)")
b2 = ax.barh(y - 0.20, d["auc_hard_negatives"], height=0.38, color=HARD,
             edgecolor="#5b6672", linewidth=0.5, zorder=3, label="2-hop hard negatives")

ax.axvline(0.5, ls="--", color="#333333", lw=1.8, zorder=4)
ax.text(0.5, len(d) - 0.35, "random guessing (0.5)", rotation=90, va="top", ha="right",
        fontsize=10, color="#333333")

for bars in (b1, b2):
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.008, bar.get_y() + bar.get_height() / 2, f"{w:.2f}",
                va="center", ha="left", fontsize=10, color="#1f2933")

ax.set_yticks(y)
ax.set_yticklabels(methods, fontsize=11.5, color="#1f2933")
ax.set_xlim(0, 0.95)
ax.set_xlabel("AUC-ROC", fontsize=12.5, color="#1f2933")
ax.set_title("The difficulty of the negative sample drives most of the reported AUC",
             fontsize=13.5, fontweight="bold", color="#1f2933", pad=10)
ax.tick_params(axis="x", labelsize=10.5, colors="#5b6672")
ax.tick_params(axis="y", length=0)
ax.xaxis.grid(True, color="#eef1f4", linewidth=0.9, zorder=0)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#9aa4af")
ax.legend(loc="lower right", fontsize=10.5, frameon=True, framealpha=0.95)

fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT, "|", OUT.stat().st_size // 1024, "KB")

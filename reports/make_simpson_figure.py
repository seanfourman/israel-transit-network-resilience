"""Regenerate the Simpson's-paradox service-gap figure in the report's palette.

Faithfully reproduces the notebook-08 selection (the 15 communities with the
largest |rho| among those with >= 20 neighbourhoods, sorted by rho), but swaps
the colour-blind-unfriendly green/red for blue (weaker neighbourhoods favoured)
and orange (stronger favoured); lighter tints mark communities that do not
survive the Benjamini-Hochberg FDR correction. Hebrew city names are reordered
with python-bidi. Saved to reports/figures/ .
"""
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from bidi.algorithm import get_display

REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "outputs" / "nb" / "08_socioeconomic_equity" / "tables" / "socioeconomic_within_cluster_correlation.csv"
OUT = REPO / "reports" / "figures" / "simpson_paradox.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

FIG_MIN_NEIGHBORHOODS = 20
TOP = 15
NATIONAL_RHO = -0.1509

_HEB = re.compile(r"[֐-׿]")
def fix_he(t):
    return get_display(t) if isinstance(t, str) and _HEB.search(t) else t

d = pd.read_csv(CSV, encoding="utf-8-sig")
valid = d.dropna(subset=["rho_use_per_capita"]).copy()
valid["abs_rho"] = valid["rho_use_per_capita"].abs()

n_fdr = int(valid["significant_fdr_05"].sum())
n_raw = int(valid["significant_raw_05"].sum())
n_tested = len(valid)

bar = valid[valid["n_neighborhoods"] >= FIG_MIN_NEIGHBORHOODS]
bar = bar.sort_values("abs_rho", ascending=False).head(TOP).sort_values("rho_use_per_capita")

# blue = weaker neighbourhoods favoured (rho<0); orange = stronger (rho>0)
NEG, POS = "#0072B2", "#D55E00"
NEG_L, POS_L = "#a9cce5", "#f4c9a6"   # light tints = not significant after FDR
def bar_color(rho, sig):
    if rho < 0:
        return NEG if sig else NEG_L
    return POS if sig else POS_L

colors = [bar_color(r, s) for r, s in zip(bar["rho_use_per_capita"], bar["significant_fdr_05"])]
labels = [fix_he("%s  (%d neighbourhoods)" % (c, n))
          for c, n in zip(bar["dominant_city"], bar["n_neighborhoods"])]

plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "axes.unicode_minus": False})
fig, ax = plt.subplots(figsize=(11, 7.6), dpi=200)

y = np.arange(len(bar))
ax.barh(y, bar["rho_use_per_capita"], color=colors, edgecolor="#5b6672",
        linewidth=0.5, height=0.72, zorder=3)

ax.axvline(0, color="#9aa4af", linewidth=1.0, zorder=2)
ax.axvline(NATIONAL_RHO, color="#333333", linestyle="--", linewidth=2.0, zorder=2)

for yi, v in zip(y, bar["rho_use_per_capita"]):
    ax.text(v + (0.017 if v >= 0 else -0.017), yi, "%+.2f" % v, va="center",
            ha="left" if v >= 0 else "right", fontsize=11, fontweight="bold",
            color="#1f2933")

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=11, color="#1f2933")
lo, hi = float(bar["rho_use_per_capita"].min()), float(bar["rho_use_per_capita"].max())
ax.set_xlim(lo - 0.22, hi + 0.22)
ax.set_xlabel("Spearman ρ   (socioeconomic cluster  vs  service per 1,000 residents)\n"
              "ρ < 0: weaker neighbourhoods favoured      ρ > 0: stronger neighbourhoods favoured",
              fontsize=11, color="#1f2933")
ax.set_title("The socioeconomic service gap changes sign from community to community\n"
             "blue = weaker neighbourhoods get more service per capita; orange = stronger ones do",
             fontsize=13.5, fontweight="bold", color="#1f2933", pad=12)

ax.tick_params(axis="x", labelsize=10.5, colors="#5b6672")
ax.tick_params(axis="y", length=0)
ax.xaxis.grid(True, color="#eef1f4", linewidth=0.9, zorder=0)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#9aa4af")

legend = [
    Patch(facecolor=NEG, edgecolor="#5b6672", label="Weaker neighbourhoods favoured (ρ < 0)"),
    Patch(facecolor=POS, edgecolor="#5b6672", label="Stronger neighbourhoods favoured (ρ > 0)"),
    Line2D([0], [0], color="#333333", ls="--", lw=2.0, label="National pooled ρ = −0.15"),
]
ax.legend(handles=legend, loc="lower right", fontsize=10, frameon=True, framealpha=0.95)

ax.text(0.015, 0.985,
        "Lighter bar = not significant after Benjamini–Hochberg FDR correction\n"
        "(%d of %d tested communities survive FDR; %d would pass at raw p < 0.05)\n"
        "Shown: the %d largest |ρ| among communities with ≥ %d neighbourhoods"
        % (n_fdr, n_tested, n_raw, len(bar), FIG_MIN_NEIGHBORHOODS),
        transform=ax.transAxes, ha="left", va="top", fontsize=9.5, color="#5b6672",
        bbox=dict(boxstyle="round,pad=0.4", fc="#f7f9fb", ec="#d0d7de", lw=1.0))

fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT, "|", OUT.stat().st_size // 1024, "KB")
print("selection (bottom->top):")
for c, n, r, s in zip(bar["dominant_city"], bar["n_neighborhoods"],
                      bar["rho_use_per_capita"], bar["significant_fdr_05"]):
    print("  %-16s n=%-4d rho=%+.2f  fdr_sig=%s" % (c, n, r, bool(s)))

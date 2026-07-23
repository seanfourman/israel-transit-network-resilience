"""Regenerate the seed-stability (noise-floor) scatter in the report's clean style.

Recomputes approx betweenness under two random seeds on the largest connected
component (the raw per-station values are not stored as a table), then plots
seed-42 vs seed-7 with the perfect-agreement diagonal. Print-friendly colours,
large fonts, saved to reports/figures/ .
"""
import pickle
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parent.parent
GRAPH = REPO / "outputs" / "nb" / "02_graph_construction" / "graph_undirected.pkl"
OUT = REPO / "reports" / "figures" / "betweenness_seed_stability.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

K = 300
print("loading graph ...")
G = pickle.load(open(GRAPH, "rb"))
lcc = G.subgraph(max(nx.connected_components(G), key=len))
print(f"LCC: {lcc.number_of_nodes()} nodes; computing betweenness (k={K}) x2 ...")
b42 = nx.betweenness_centrality(lcc, k=K, seed=42, weight=None, normalized=True)
b7 = nx.betweenness_centrality(lcc, k=K, seed=7, weight=None, normalized=True)
nodes = list(lcc.nodes())
x = [b42[n] for n in nodes]
y = [b7[n] for n in nodes]
rho = spearmanr(x, y).correlation
print(f"Spearman rho = {rho:.3f}")

hi = max(max(x), max(y)) * 1.03

plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"]})
fig, ax = plt.subplots(figsize=(6.2, 5.8), dpi=200)

ax.plot([0, hi], [0, hi], ls="--", lw=1.6, color="#1f2933",
        zorder=1, label="perfect agreement")
ax.scatter(x, y, s=7, color="#0072B2", alpha=0.30, edgecolors="none", zorder=2)

ax.set_xlim(0, hi)
ax.set_ylim(0, hi)
ax.set_aspect("equal")
ax.set_xlabel("Approx. betweenness (seed 42)", fontsize=13, color="#1f2933")
ax.set_ylabel("Approx. betweenness (seed 7)", fontsize=13, color="#1f2933")
ax.set_title(f"Same estimator, different random sample (k={K})",
             fontsize=13.5, fontweight="bold", color="#1f2933", pad=10)
ax.tick_params(labelsize=11, colors="#5b6672")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for s in ("left", "bottom"):
    ax.spines[s].set_color("#9aa4af")
ax.grid(True, color="#eef1f4", linewidth=0.8, zorder=0)
ax.set_axisbelow(True)

# self-contained stat annotation
ax.text(0.04, 0.93, f"Spearman ρ = {rho:.2f}", transform=ax.transAxes,
        fontsize=13, fontweight="bold", color="#1f2933",
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#c8d0d8", lw=1))
ax.legend(loc="lower right", fontsize=11.5, frameon=True, framealpha=0.9)

fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT, "|", OUT.stat().st_size // 1024, "KB")

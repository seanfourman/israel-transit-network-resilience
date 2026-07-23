"""Regenerate the mode-interdependence figure — a clean, readable version.

The modes form a near-bipartite "double star": bus and rail are the two hubs and
the four minor modes connect only to them, so a fixed left/right hub layout draws
with zero edge crossings. The same node positions are used in both panels, so the
reader can directly compare the strict definition (one link) with the walkable one
(nine links). Edge width and its printed number both encode the shared-stop count.
Saved to reports/figures/ .
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
T = REPO / "outputs" / "nb" / "17_multimodal_transfer_hubs" / "tables"
OUT = REPO / "reports" / "figures" / "mode_interdependence.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

SHORT = {"bus": "Bus", "rail": "Rail", "tram/light rail": "Light rail",
         "demand/other bus": "Demand bus", "cable tram": "Cable tram",
         "trolleybus/taxi-coded": "Trolleybus"}
COLOR = {"bus": "#0072B2", "rail": "#D55E00", "tram/light rail": "#009E73",
         "demand/other bus": "#E69F00", "cable tram": "#CC79A7",
         "trolleybus/taxi-coded": "#7f7f7f"}
POS = {"bus": (0, 0), "rail": (11, 0),
       "tram/light rail": (5.5, 4), "demand/other bus": (5.5, 1.35),
       "cable tram": (5.5, -1.35), "trolleybus/taxi-coded": (5.5, -4)}
LABEL_ABOVE = {"tram/light rail", "demand/other bus"}   # push labels away from centre


def load_edges(fname, wcol):
    d = pd.read_csv(T / fname, encoding="utf-8-sig")
    return {(r.mode_a, r.mode_b): int(getattr(r, wcol))
            for r in d.itertuples() if int(getattr(r, wcol)) > 0}


strict = load_edges("mode_interdependence.csv", "shared_stops")
walk = load_edges("mode_interdependence_walkable.csv", "interchange_stops")


def draw(ax, edges, title, subtitle):
    for (a, b), w in edges.items():
        xa, ya = POS[a]; xb, yb = POS[b]
        lw = 1.3 + (w ** 0.5) * 0.5
        # bus<->rail runs straight through the empty centre line (y=0)
        ax.plot([xa, xb], [ya, yb], color="#9aa4af", lw=lw, zorder=1, alpha=0.9,
                solid_capstyle="round")
        lx, ly = (xa + xb) / 2, (ya + yb) / 2
        ax.text(lx, ly, str(w), fontsize=10, ha="center", va="center", zorder=5,
                color="#1f2933", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.92))

    for m, (x, y) in POS.items():
        ax.scatter([x], [y], s=1250, color=COLOR[m], edgecolors="white",
                   linewidths=2.0, zorder=3)
    # node names: hub labels pushed outward, minor modes centred just below
    ax.text(-1.0, 0, SHORT["bus"], ha="right", va="center", fontsize=12,
            fontweight="bold", color="#1f2933", zorder=6)
    ax.text(12.0, 0, SHORT["rail"], ha="left", va="center", fontsize=12,
            fontweight="bold", color="#1f2933", zorder=6)
    for m in ("tram/light rail", "demand/other bus", "cable tram", "trolleybus/taxi-coded"):
        x, y = POS[m]
        above = m in LABEL_ABOVE
        ax.text(x, y + (0.95 if above else -0.95), SHORT[m], ha="center",
                va="bottom" if above else "top", fontsize=11,
                fontweight="bold", color="#1f2933", zorder=6,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))

    ax.set_title(title, fontsize=14, fontweight="bold", color="#1f2933", pad=24)
    ax.text(0.5, 1.02, subtitle, transform=ax.transAxes, ha="center", va="bottom",
            fontsize=11.5, color="#5b6672")
    ax.set_xlim(-4.6, 15.6)
    ax.set_ylim(-5.7, 5.7)
    ax.set_aspect("equal")
    ax.axis("off")


plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"]})
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.5, 6.6), dpi=200)
draw(axL, strict, "Strict definition", "shared stop code  →  1 interchange link")
draw(axR, walk, "Walkable definition", "modes within 150 m  →  9 interchange links")
fig.suptitle("How the transport modes connect  —  nodes are modes, link width and number = shared stops",
             fontsize=13.5, fontweight="bold", color="#1f2933", y=1.0)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
print("saved:", OUT, "|", OUT.stat().st_size // 1024, "KB")
print("strict edges:", strict)
print("walk edges  :", len(walk))

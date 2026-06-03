"""
שלב 03 — ניתוח תיאורי של הרשת
קלט:  02_graph_construction/outputs/
פלט:  03_network_descriptive_analysis/outputs/ + figures/
"""
import pickle, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH_DIR = ROOT / "public_transport_network_research/02_graph_construction/outputs"
OUT_DIR   = Path(__file__).resolve().parents[1] / "outputs"
FIG_DIR   = ROOT / "public_transport_network_research/figures/03_network_descriptive_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

def load_graphs():
    with open(GRAPH_DIR / "graph_undirected.pkl", "rb") as f:
        G = pickle.load(f)
    with open(GRAPH_DIR / "graph_directed.pkl", "rb") as f:
        D = pickle.load(f)
    return G, D

def compute_summary(G, D):
    components = sorted(nx.connected_components(G), key=len, reverse=True)
    largest = len(components[0])
    ap = list(nx.articulation_points(G))
    br = list(nx.bridges(G))

    wcc = list(nx.weakly_connected_components(D))
    scc = list(nx.strongly_connected_components(D))

    degrees = [d for _, d in G.degree()]
    return {
        "num_nodes": G.number_of_nodes(),
        "num_edges_undirected": G.number_of_edges(),
        "num_edges_directed": D.number_of_edges(),
        "density": round(nx.density(G), 6),
        "avg_degree": round(np.mean(degrees), 2),
        "max_degree": int(np.max(degrees)),
        "min_degree": int(np.min(degrees)),
        "num_connected_components": len(components),
        "largest_component_nodes": largest,
        "largest_component_share": round(largest / G.number_of_nodes(), 4),
        "num_weakly_connected": len(wcc),
        "num_strongly_connected": len(scc),
        "largest_scc_nodes": max(len(c) for c in scc),
        "num_articulation_points": len(ap),
        "num_bridges": len(br),
    }, ap, br

def plot_degree_distribution(G, fig_dir):
    degrees = [d for _, d in G.degree()]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].hist(degrees, bins=60, color="#2563eb", edgecolor="white", linewidth=0.3)
    axes[0].set_xlabel("Degree (מספר שכנים)")
    axes[0].set_ylabel("מספר תחנות")
    axes[0].set_title("התפלגות דרגות — רשת תחבורה ישראל")

    deg_counts = pd.Series(degrees).value_counts().sort_index()
    deg_counts = deg_counts[deg_counts.index > 0]
    axes[1].scatter(np.log10(deg_counts.index), np.log10(deg_counts.values), s=8, color="#dc2626", alpha=0.6)
    axes[1].set_xlabel("log₁₀(Degree)")
    axes[1].set_ylabel("log₁₀(Count)")
    axes[1].set_title("Log-Log Degree Distribution (בדיקת Power Law)")

    plt.tight_layout()
    plt.savefig(fig_dir / "degree_distribution.png", dpi=150)
    plt.close()
    print("  ✓ degree_distribution.png")

def plot_network_map(G, fig_dir):
    nodes_with_coords = [(n, d) for n, d in G.nodes(data=True)
                         if d.get("lat") and d.get("lon")]
    if not nodes_with_coords:
        print("  ✗ אין קואורדינטות לתחנות")
        return

    lats = [d["lat"] for _, d in nodes_with_coords]
    lons = [d["lon"] for _, d in nodes_with_coords]
    degrees = [G.degree(n) for n, _ in nodes_with_coords]
    max_deg = max(degrees) if degrees else 1

    sizes = [2 + 30 * (d / max_deg) for d in degrees]
    colors = degrees

    fig, ax = plt.subplots(figsize=(8, 11))
    sc = ax.scatter(lons, lats, c=colors, s=sizes, cmap="viridis",
                    alpha=0.55, linewidths=0)
    plt.colorbar(sc, ax=ax, label="Degree")
    ax.set_xlabel("קו אורך")
    ax.set_ylabel("קו רוחב")
    ax.set_title(f"מפת תחנות תחבורה ציבורית ישראל\n({len(nodes_with_coords):,} תחנות פעילות)")
    plt.tight_layout()
    plt.savefig(fig_dir / "network_overview_map.png", dpi=150)
    plt.close()
    print("  ✓ network_overview_map.png")

def plot_component_sizes(G, fig_dir):
    sizes = sorted([len(c) for c in nx.connected_components(G)], reverse=True)
    top = sizes[:20]
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#2563eb" if i == 0 else "#94a3b8" for i in range(len(top))]
    ax.bar(range(1, len(top)+1), top, color=colors)
    ax.set_xlabel("רכיב קשור (#)")
    ax.set_ylabel("מספר תחנות")
    ax.set_title("גדלי רכיבים קשורים (Top 20)")
    ax.set_yscale("log")
    plt.tight_layout()
    plt.savefig(fig_dir / "components_summary_bar.png", dpi=150)
    plt.close()
    print("  ✓ components_summary_bar.png")

def plot_region_distribution(G, fig_dir):
    regions = {}
    for n, d in G.nodes(data=True):
        r = d.get("region", "לא ידוע")
        regions[r] = regions.get(r, 0) + 1

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(regions.keys(), regions.values(),
                  color=["#2563eb","#16a34a","#dc2626","#d97706"])
    ax.set_xlabel("אזור")
    ax.set_ylabel("מספר תחנות")
    ax.set_title("פיזור תחנות לפי אזור גיאוגרפי")
    for bar, val in zip(bars, regions.values()):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                f"{val:,}", ha="center", va="bottom", fontsize=10)
    plt.tight_layout()
    plt.savefig(fig_dir / "stops_by_region.png", dpi=150)
    plt.close()
    print("  ✓ stops_by_region.png")

def save_ap_bridges(ap, br, G, out_dir):
    nodes_df = pd.DataFrame([{"stop_id": n, **G.nodes[n]} for n in G.nodes()])
    ap_set = set(ap)
    ap_df = nodes_df[nodes_df["stop_id"].isin(ap_set)].copy()
    ap_df.to_csv(out_dir / "articulation_points.csv", index=False, encoding="utf-8-sig")

    br_rows = []
    for u, v in br:
        br_rows.append({
            "from_stop": u,
            "to_stop": v,
            "trip_frequency": int(G[u][v].get("weight", 1)),
        })
    pd.DataFrame(br_rows).to_csv(out_dir / "bridges.csv", index=False, encoding="utf-8-sig")
    print(f"  ✓ articulation_points.csv ({len(ap_df)} AP)")
    print(f"  ✓ bridges.csv ({len(br_rows)} bridges)")

def main():
    print("=== שלב 03: ניתוח תיאורי ===")
    G, D = load_graphs()
    print(f"  גרף נטען: {G.number_of_nodes():,} צמתים, {G.number_of_edges():,} קשתות")

    print("  מחשב סטטיסטיקות (AP ו-Bridges עשויים לקחת כדקה) ...")
    summary, ap, br = compute_summary(G, D)

    with open(OUT_DIR / "network_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    pd.DataFrame([summary]).to_csv(OUT_DIR / "network_summary.csv",
                                    index=False, encoding="utf-8-sig")

    print("\n  ממצאים:")
    for k, v in summary.items():
        print(f"    {k}: {v}")

    save_ap_bridges(ap, br, G, OUT_DIR)

    print("\n  יוצר גרפים ...")
    plot_degree_distribution(G, FIG_DIR)
    plot_network_map(G, FIG_DIR)
    plot_component_sizes(G, FIG_DIR)
    plot_region_distribution(G, FIG_DIR)

    print(f"\nפלטים נשמרו ב:\n  {OUT_DIR}\n  {FIG_DIR}")

if __name__ == "__main__":
    main()

"""
שלב 07 — זיהוי קהילות (Community Detection)
קלט:  02_graph_construction/outputs/
פלט:  07_community_detection/outputs/ + figures/
"""
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH_DIR   = ROOT / "public_transport_network_research/02_graph_construction/outputs"
METRICS_CSV = ROOT / "public_transport_network_research/04_centrality_analysis/outputs/stop_metrics.csv"
OUT_DIR     = Path(__file__).resolve().parents[1] / "outputs"
FIG_DIR     = ROOT / "public_transport_network_research/figures/07_community_detection"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd
import numpy as np
import networkx as nx
import community as community_louvain
import matplotlib
matplotlib.use("Agg")
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from _hebrew_bidi import install_hebrew
install_hebrew()
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

def load():
    with open(GRAPH_DIR / "graph_undirected.pkl", "rb") as f:
        G = pickle.load(f)
    metrics = pd.read_csv(METRICS_CSV, encoding="utf-8-sig")
    return G, metrics

def run_louvain(G):
    print("  Louvain community detection ...")
    Gc = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    partition = community_louvain.best_partition(Gc, weight="weight", random_state=42)
    modularity = community_louvain.modularity(partition, Gc, weight="weight")
    print(f"  Modularity = {modularity:.4f}")
    n_communities = len(set(partition.values()))
    print(f"  קהילות שנמצאו: {n_communities}")
    return partition, modularity, Gc

def run_label_propagation(G):
    print("  Label Propagation ...")
    Gc = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    communities = list(nx.algorithms.community.label_propagation_communities(Gc))
    partition_lp = {}
    for i, comm in enumerate(communities):
        for node in comm:
            partition_lp[node] = i
    print(f"  Label Propagation: {len(communities)} קהילות")
    return partition_lp

def build_community_summary(partition, G, metrics):
    community_ids = set(partition.values())
    rows = []
    metrics_idx = metrics.set_index("stop_id") if "stop_id" in metrics.columns else metrics

    for cid in sorted(community_ids):
        members = [n for n, c in partition.items() if c == cid]
        sub = G.subgraph(members)
        member_metrics = metrics_idx.loc[metrics_idx.index.isin(members)] if hasattr(metrics_idx.index, '__iter__') else pd.DataFrame()

        lats = [G.nodes[n].get("lat") for n in members if G.nodes[n].get("lat")]
        lons = [G.nodes[n].get("lon") for n in members if G.nodes[n].get("lon")]

        rows.append({
            "community_id": cid,
            "size": len(members),
            "internal_edges": sub.number_of_edges(),
            "centroid_lat": round(np.mean(lats), 4) if lats else None,
            "centroid_lon": round(np.mean(lons), 4) if lons else None,
        })

    return pd.DataFrame(rows).sort_values("size", ascending=False)

def find_inter_community_nodes(G, partition):
    rows = []
    for node in G.nodes():
        if node not in partition:
            continue
        own = partition[node]
        neighbor_comms = {partition[nb] for nb in G.neighbors(node) if nb in partition}
        neighbor_comms.discard(own)
        if neighbor_comms:
            rows.append({
                "stop_id": node,
                "stop_name": G.nodes[node].get("stop_name", ""),
                "own_community": own,
                "connected_communities": len(neighbor_comms),
                "degree": G.degree(node),
                "lat": G.nodes[node].get("lat"),
                "lon": G.nodes[node].get("lon"),
            })
    return pd.DataFrame(rows).sort_values("connected_communities", ascending=False)

def plot_community_map(partition, G, fig_dir, title, fname):
    comm_ids = list(set(partition.values()))
    cmap = matplotlib.colormaps.get_cmap("tab20").resampled(len(comm_ids))
    color_map = {cid: cmap(i) for i, cid in enumerate(comm_ids)}

    lons, lats, cols = [], [], []
    for node, cid in partition.items():
        lat = G.nodes[node].get("lat")
        lon = G.nodes[node].get("lon")
        if lat and lon:
            lons.append(lon); lats.append(lat); cols.append(color_map[cid])

    fig, ax = plt.subplots(figsize=(8, 11))
    ax.scatter(lons, lats, s=3, color=cols, alpha=0.5, linewidths=0)
    ax.set_title(title)
    ax.set_xlabel("קו אורך"); ax.set_ylabel("קו רוחב")
    plt.tight_layout()
    plt.savefig(fig_dir / fname, dpi=150)
    plt.close()
    print(f"  ✓ {fname}")

def plot_community_sizes(summary, fig_dir):
    top = summary.head(20).sort_values("size")
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(top["community_id"].astype(str), top["size"], color="#7c3aed")
    ax.set_xlabel("מספר תחנות")
    ax.set_title("גדלי הקהילות הגדולות ביותר (Top 20)")
    plt.tight_layout()
    plt.savefig(fig_dir / "community_sizes_bar.png", dpi=150)
    plt.close()
    print("  ✓ community_sizes_bar.png")

def plot_inter_community(inter_df, G, fig_dir):
    data = inter_df.dropna(subset=["lat","lon"]).head(100)
    fig, ax = plt.subplots(figsize=(8, 11))
    # כל תחנות הרשת ברקע (scatter וקטורי אחד)
    bg_lons = [d["lon"] for _, d in G.nodes(data=True) if d.get("lat") and d.get("lon")]
    bg_lats = [d["lat"] for _, d in G.nodes(data=True) if d.get("lat") and d.get("lon")]
    ax.scatter(bg_lons, bg_lats, s=1, color="#e2e8f0", alpha=0.3, linewidths=0)
    sc = ax.scatter(data["lon"], data["lat"],
                    s=data["connected_communities"]*20,
                    c=data["connected_communities"], cmap="Reds",
                    zorder=5, edgecolors="black", linewidths=0.3)
    plt.colorbar(sc, ax=ax, label="קהילות מחוברות")
    ax.set_title("תחנות בין-קהילתיות (גודל = מספר קהילות מחוברות)")
    ax.set_xlabel("קו אורך"); ax.set_ylabel("קו רוחב")
    plt.tight_layout()
    plt.savefig(fig_dir / "inter_community_nodes.png", dpi=150)
    plt.close()
    print("  ✓ inter_community_nodes.png")

def main():
    print("=== שלב 07: Community Detection ===")
    G, metrics = load()
    print(f"  גרף: {G.number_of_nodes():,} צמתים, {G.number_of_edges():,} קשתות")

    partition_louvain, modularity, Gc = run_louvain(G)
    partition_lp = run_label_propagation(G)

    # שמירת שיוכי קהילות
    assign_rows = []
    for node in G.nodes():
        assign_rows.append({
            "stop_id": node,
            "stop_name": G.nodes[node].get("stop_name",""),
            "lat": G.nodes[node].get("lat"),
            "lon": G.nodes[node].get("lon"),
            "region": G.nodes[node].get("region",""),
            "community_louvain": partition_louvain.get(node, -1),
            "community_lp":      partition_lp.get(node, -1),
        })
    assign_df = pd.DataFrame(assign_rows)
    assign_df.to_csv(OUT_DIR / "community_assignments.csv", index=False, encoding="utf-8-sig")
    print(f"  ✓ community_assignments.csv")

    summary = build_community_summary(partition_louvain, G, metrics)
    summary.to_csv(OUT_DIR / "community_summary.csv", index=False, encoding="utf-8-sig")
    print(f"  ✓ community_summary.csv ({len(summary)} קהילות)")

    inter_df = find_inter_community_nodes(G, partition_louvain)
    inter_df.to_csv(OUT_DIR / "inter_community_bridges.csv", index=False, encoding="utf-8-sig")
    print(f"  ✓ inter_community_bridges.csv ({len(inter_df)} תחנות)")

    print(f"\n  Modularity (Louvain): {modularity:.4f}")
    print(f"  קהילות Louvain: {len(set(partition_louvain.values()))}")
    print(f"  קהילות Label Propagation: {len(set(partition_lp.values()))}")

    print("\n  יוצר גרפים ...")
    plot_community_map(partition_louvain, G, FIG_DIR,
                       f"מפת קהילות — Louvain (Modularity={modularity:.3f})",
                       "community_map_louvain.png")
    plot_community_sizes(summary, FIG_DIR)
    plot_inter_community(inter_df, G, FIG_DIR)

    print(f"\nTop 5 קהילות לפי גודל:")
    print(summary.head(5).to_string(index=False))
    print(f"\nפלטים נשמרו ב:\n  {OUT_DIR}\n  {FIG_DIR}")

if __name__ == "__main__":
    main()

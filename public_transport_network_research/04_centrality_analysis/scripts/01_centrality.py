"""
שלב 04 — ניתוח מרכזיות (Centrality)
קלט:  02_graph_construction/outputs/
פלט:  04_centrality_analysis/outputs/ + figures/
"""
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH_DIR = ROOT / "public_transport_network_research/02_graph_construction/outputs"
AP_PATH   = ROOT / "public_transport_network_research/03_network_descriptive_analysis/outputs/articulation_points.csv"
OUT_DIR   = Path(__file__).resolve().parents[1] / "outputs"
FIG_DIR   = ROOT / "public_transport_network_research/figures/04_centrality_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from _hebrew_bidi import install_hebrew
install_hebrew()
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)
BETWEENNESS_K = 300   # approximation samples

def load_graph():
    with open(GRAPH_DIR / "graph_undirected.pkl", "rb") as f:
        G = pickle.load(f)
    with open(GRAPH_DIR / "graph_directed.pkl", "rb") as f:
        D = pickle.load(f)
    return G, D

def largest_component(G):
    nodes = max(nx.connected_components(G), key=len)
    return G.subgraph(nodes).copy()

def compute_all_centrality(G, D):
    print("  Degree Centrality ...")
    deg_c = nx.degree_centrality(G)

    print("  In/Out Degree ...")
    in_deg  = dict(D.in_degree())
    out_deg = dict(D.out_degree())

    print("  PageRank ...")
    pr = nx.pagerank(D, weight="weight", alpha=0.85)

    print(f"  Betweenness (k={BETWEENNESS_K} samples) ...")
    Gc = largest_component(G)
    k = min(BETWEENNESS_K, Gc.number_of_nodes())
    btw = nx.betweenness_centrality(Gc, k=k, seed=42, normalized=True)

    print("  Harmonic Centrality (on largest component) ...")
    harm = nx.harmonic_centrality(Gc)

    nodes = list(G.nodes())
    rows = []
    for n in nodes:
        rows.append({
            "stop_id": n,
            "stop_name": G.nodes[n].get("stop_name", ""),
            "region": G.nodes[n].get("region", ""),
            "metro": G.nodes[n].get("metro", ""),
            "lat": G.nodes[n].get("lat"),
            "lon": G.nodes[n].get("lon"),
            "degree": G.degree(n),
            "degree_centrality": round(deg_c.get(n, 0), 6),
            "in_degree": in_deg.get(n, 0),
            "out_degree": out_deg.get(n, 0),
            "pagerank": round(pr.get(n, 0), 8),
            "betweenness": round(btw.get(n, 0), 8),
            "harmonic": round(harm.get(n, 0), 4),
        })

    df = pd.DataFrame(rows)
    return df

def plot_top10_bar(df, col, title, fname, color):
    top = df.nlargest(15, col)[["stop_name","stop_id",col]].copy()
    top["label"] = top["stop_name"].where(top["stop_name"] != "", top["stop_id"])
    top = top.sort_values(col)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(top["label"], top[col], color=color)
    ax.set_xlabel(col.replace("_", " ").title())
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(FIG_DIR / fname, dpi=150)
    plt.close()
    print(f"  ✓ {fname}")

def plot_correlation_heatmap(df):
    cols = ["degree","pagerank","betweenness","harmonic"]
    corr = df[cols].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm",
                center=0, ax=ax, square=True)
    ax.set_title("קורלציית Spearman בין מדדי Centrality")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "centrality_correlation_heatmap.png", dpi=150)
    plt.close()
    print("  ✓ centrality_correlation_heatmap.png")

def plot_scatter(df):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].scatter(df["degree"], df["betweenness"], s=3, alpha=0.3, color="#2563eb")
    axes[0].set_xlabel("Degree")
    axes[0].set_ylabel("Betweenness Centrality")
    axes[0].set_title("Degree vs. Betweenness")

    axes[1].scatter(df["degree"], df["pagerank"], s=3, alpha=0.3, color="#16a34a")
    axes[1].set_xlabel("Degree")
    axes[1].set_ylabel("PageRank")
    axes[1].set_title("Degree vs. PageRank")

    plt.tight_layout()
    plt.savefig(FIG_DIR / "centrality_scatter.png", dpi=150)
    plt.close()
    print("  ✓ centrality_scatter.png")

def plot_centrality_map(df):
    data = df.dropna(subset=["lat","lon"])
    top_btw = set(data.nlargest(50, "betweenness")["stop_id"])

    fig, ax = plt.subplots(figsize=(8, 11))
    ax.scatter(data["lon"], data["lat"], s=2, alpha=0.2, color="#94a3b8")
    top_data = data[data["stop_id"].isin(top_btw)]
    sc = ax.scatter(top_data["lon"], top_data["lat"],
                    s=40, c=top_data["betweenness"], cmap="Reds",
                    zorder=5, edgecolors="black", linewidths=0.3)
    plt.colorbar(sc, ax=ax, label="Betweenness")
    ax.set_title("Top 50 תחנות לפי Betweenness Centrality")
    ax.set_xlabel("קו אורך")
    ax.set_ylabel("קו רוחב")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "centrality_map_betweenness.png", dpi=150)
    plt.close()
    print("  ✓ centrality_map_betweenness.png")

def main():
    print("=== שלב 04: ניתוח מרכזיות ===")
    G, D = load_graph()
    print(f"  גרף נטען: {G.number_of_nodes():,} צמתים")

    df = compute_all_centrality(G, D)
    df.to_csv(OUT_DIR / "stop_metrics.csv", index=False, encoding="utf-8-sig")
    print(f"  ✓ stop_metrics.csv ({len(df)} שורות)")

    corr = df[["degree","pagerank","betweenness","harmonic"]].corr(method="spearman").round(4)
    corr.to_csv(OUT_DIR / "centrality_correlation_spearman.csv", encoding="utf-8-sig")

    for metric, n in [("degree",15),("betweenness",15),("pagerank",15),("harmonic",15)]:
        df.nlargest(n, metric).to_csv(
            OUT_DIR / f"top_{metric}.csv", index=False, encoding="utf-8-sig")

    print("\n  יוצר גרפים ...")
    plot_top10_bar(df, "degree", "Top 15 תחנות לפי Degree", "top_degree_bar.png", "#2563eb")
    plot_top10_bar(df, "betweenness", "Top 15 תחנות לפי Betweenness", "top_betweenness_bar.png", "#dc2626")
    plot_top10_bar(df, "pagerank", "Top 15 תחנות לפי PageRank", "top_pagerank_bar.png", "#16a34a")
    plot_top10_bar(df, "harmonic", "Top 15 תחנות לפי Harmonic Centrality", "top_harmonic_bar.png", "#d97706")
    plot_correlation_heatmap(df)
    plot_scatter(df)
    plot_centrality_map(df)

    print("\nTop 5 Betweenness:")
    print(df.nlargest(5,"betweenness")[["stop_name","stop_id","region","degree","betweenness","pagerank"]].to_string(index=False))
    print(f"\nפלטים נשמרו ב:\n  {OUT_DIR}\n  {FIG_DIR}")

if __name__ == "__main__":
    main()

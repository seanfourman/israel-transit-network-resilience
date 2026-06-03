"""
שלב 05 — ניתוח שיבושים ועמידות (Robustness)
קלט:  02_graph_construction/ + 04_centrality_analysis/
פלט:  05_robustness.../outputs/ + figures/
"""
import pickle, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH_DIR  = ROOT / "public_transport_network_research/02_graph_construction/outputs"
METRIC_CSV = ROOT / "public_transport_network_research/04_centrality_analysis/outputs/stop_metrics.csv"
AP_CSV     = ROOT / "public_transport_network_research/03_network_descriptive_analysis/outputs/articulation_points.csv"
OUT_DIR    = Path(__file__).resolve().parents[1] / "outputs"
FIG_DIR    = ROOT / "public_transport_network_research/figures/05_robustness_and_disruption_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

MAX_REMOVALS = 3000   # ~10% מהרשת — מספיק כדי שעקומת העמידות תתעקם ויראו הבדל בין אסטרטגיות
STEPS = 40
RANDOM_TRIALS = 5
SEED = 42

def load():
    with open(GRAPH_DIR / "graph_undirected.pkl", "rb") as f:
        G = pickle.load(f)
    metrics = pd.read_csv(METRIC_CSV, dtype=str)
    metrics["degree"]      = pd.to_numeric(metrics["degree"])
    metrics["betweenness"] = pd.to_numeric(metrics["betweenness"])
    metrics["pagerank"]    = pd.to_numeric(metrics["pagerank"])
    metrics["harmonic"]    = pd.to_numeric(metrics["harmonic"])
    ap_df = pd.read_csv(AP_CSV, dtype=str)
    return G, metrics, ap_df

def lcc_size(G, removed):
    Gr = G.copy()
    Gr.remove_nodes_from(removed)
    if Gr.number_of_nodes() == 0:
        return 0
    return max(len(c) for c in nx.connected_components(Gr))

def simulate(G, ordered_nodes, max_removals, steps, baseline_n):
    ks = sorted(set(int(round(x)) for x in np.linspace(0, max_removals, steps)))
    rows = []
    for k in ks:
        removed = set(ordered_nodes[:k])
        size = lcc_size(G, removed)
        rows.append({
            "removed": k,
            "lcc_size": size,
            "lcc_share": round(size / baseline_n, 4),
        })
        if k % 50 == 0:
            print(f"    k={k}: LCC share={size/baseline_n:.3f}")
    return rows

def simulate_random(G, max_removals, steps, baseline_n, trials, seed):
    ks = sorted(set(int(round(x)) for x in np.linspace(0, max_removals, steps)))
    rng = random.Random(seed)
    nodes = list(G.nodes())
    rows = []
    for k in ks:
        sizes = []
        for _ in range(trials):
            removed = set(rng.sample(nodes, min(k, len(nodes))))
            sizes.append(lcc_size(G, removed))
        rows.append({
            "removed": k,
            "lcc_size": np.mean(sizes),
            "lcc_share": round(np.mean(sizes) / baseline_n, 4),
        })
    return rows

def run_all(G, metrics, ap_df):
    baseline_n = G.number_of_nodes()
    all_results = {}

    strategies = {
        "degree (גבוה→נמוך)":      metrics.sort_values("degree", ascending=False)["stop_id"].tolist(),
        "betweenness (גבוה→נמוך)": metrics.sort_values("betweenness", ascending=False)["stop_id"].tolist(),
        "pagerank (גבוה→נמוך)":    metrics.sort_values("pagerank", ascending=False)["stop_id"].tolist(),
        "articulation points":      ap_df["stop_id"].tolist() + metrics.sort_values("degree", ascending=False)["stop_id"].tolist(),
    }

    for name, ordered in strategies.items():
        print(f"\n  הסרה לפי: {name}")
        rows = simulate(G, ordered, MAX_REMOVALS, STEPS, baseline_n)
        df = pd.DataFrame(rows)
        df["strategy"] = name
        all_results[name] = df

    print(f"\n  הסרה אקראית (baseline, {RANDOM_TRIALS} ניסויים)")
    rand_rows = simulate_random(G, MAX_REMOVALS, STEPS, baseline_n, RANDOM_TRIALS, SEED)
    df_rand = pd.DataFrame(rand_rows)
    df_rand["strategy"] = "אקראי (baseline)"
    all_results["אקראי (baseline)"] = df_rand

    return pd.concat(all_results.values(), ignore_index=True)

def plot_resilience_curves(df):
    fig, ax = plt.subplots(figsize=(11, 6))
    colors = ["#dc2626","#2563eb","#16a34a","#d97706","#6b7280"]
    for (strategy, grp), color in zip(df.groupby("strategy"), colors):
        grp = grp.sort_values("removed")
        ax.plot(grp["removed"], grp["lcc_share"],
                marker="o", markersize=4, linewidth=2,
                label=strategy, color=color)
    ax.set_xlabel("מספר תחנות שהוסרו")
    ax.set_ylabel("Largest Component Share")
    ax.set_title("עקומות עמידות הרשת לפי אסטרטגיית הסרה")
    y_min = max(0.0, df["lcc_share"].min() - 0.03)
    ax.set_ylim(y_min, 1.01)
    ax.legend(loc="lower left", fontsize=9)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "resilience_curves_comparison.png", dpi=150)
    plt.close()
    print("  ✓ resilience_curves_comparison.png")

def plot_damage_bar(df):
    k_val = 50
    rows = []
    for strat, grp in df.groupby("strategy"):
        idx = (grp["removed"] - k_val).abs().argmin()
        row = grp.iloc[idx].copy()
        rows.append({"strategy": strat, "removed": row["removed"], "lcc_share": row["lcc_share"]})
    snapshot = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#dc2626","#2563eb","#16a34a","#d97706","#6b7280"]
    bars = ax.bar(snapshot["strategy"], snapshot["lcc_share"], color=colors[:len(snapshot)])
    ax.set_ylabel("LCC Share אחרי הסרת ~50 תחנות")
    ax.set_title("נזק לפי אסטרטגיית הסרה (k≈50)")
    ax.set_ylim(0, 1.05)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    for bar, val in zip(bars, snapshot["lcc_share"]):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.01,
                f"{val:.3f}", ha="center", fontsize=9)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "damage_at_k50_bar.png", dpi=150)
    plt.close()
    print("  ✓ damage_at_k50_bar.png")

def plot_area_under_curve(df):
    auc = df.groupby("strategy").apply(
        lambda g: np.trapz(g.sort_values("removed")["lcc_share"],
                           g.sort_values("removed")["removed"])
    ).reset_index()
    auc.columns = ["strategy", "auc"]
    auc = auc.sort_values("auc")

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#dc2626","#2563eb","#16a34a","#d97706","#6b7280"]
    ax.barh(auc["strategy"], auc["auc"], color=colors)
    ax.set_xlabel("Area Under Resilience Curve (גבוה = עמיד יותר)")
    ax.set_title("עמידות כוללת לפי אסטרטגיה (AUC)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "auc_comparison.png", dpi=150)
    plt.close()
    print("  ✓ auc_comparison.png")

def main():
    print("=== שלב 05: ניתוח שיבושים ועמידות ===")
    G, metrics, ap_df = load()
    print(f"  גרף: {G.number_of_nodes():,} צמתים, {G.number_of_edges():,} קשתות")
    print(f"  מדדי centrality: {len(metrics):,} תחנות")
    print(f"  Articulation Points: {len(ap_df):,}")

    df = run_all(G, metrics, ap_df)
    df.to_csv(OUT_DIR / "disruption_results.csv", index=False, encoding="utf-8-sig")
    print(f"\n  ✓ disruption_results.csv ({len(df)} שורות)")

    print("\n  יוצר גרפים ...")
    plot_resilience_curves(df)
    plot_damage_bar(df)
    plot_area_under_curve(df)

    print("\nסיכום LCC Share @ k=50:")
    snap_rows = []
    for strat, grp in df.groupby("strategy"):
        idx = (grp["removed"] - 50).abs().argmin()
        r = grp.iloc[idx]
        snap_rows.append({"strategy": strat, "removed": r["removed"], "lcc_share": r["lcc_share"]})
    snap = pd.DataFrame(snap_rows)
    print(snap.sort_values("lcc_share").to_string(index=False))

    print(f"\nפלטים נשמרו ב:\n  {OUT_DIR}\n  {FIG_DIR}")

if __name__ == "__main__":
    main()

"""
שלב 06 — השוואה אזורית
קלט:  04_centrality + 03_descriptive outputs
פלט:  06_regional_comparison/outputs/ + figures/
"""
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
METRICS_CSV = ROOT / "public_transport_network_research/04_centrality_analysis/outputs/stop_metrics.csv"
AP_CSV      = ROOT / "public_transport_network_research/03_network_descriptive_analysis/outputs/articulation_points.csv"
BRIDGES_CSV = ROOT / "public_transport_network_research/03_network_descriptive_analysis/outputs/bridges.csv"
GRAPH_DIR   = ROOT / "public_transport_network_research/02_graph_construction/outputs"
OUT_DIR     = Path(__file__).resolve().parents[1] / "outputs"
FIG_DIR     = ROOT / "public_transport_network_research/figures/06_regional_comparison"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=1.1)

def main():
    print("=== שלב 06: השוואה אזורית ===")
    metrics = pd.read_csv(METRICS_CSV, encoding="utf-8-sig")
    ap_df   = pd.read_csv(AP_CSV,      encoding="utf-8-sig")
    br_df   = pd.read_csv(BRIDGES_CSV, encoding="utf-8-sig")

    ap_set = set(ap_df["stop_id"].astype(str))
    metrics["is_ap"] = metrics["stop_id"].astype(str).isin(ap_set)
    metrics["betweenness"] = pd.to_numeric(metrics["betweenness"], errors="coerce").fillna(0)
    metrics["degree"]      = pd.to_numeric(metrics["degree"],      errors="coerce").fillna(0)

    btw_p90 = metrics["betweenness"].quantile(0.90)
    metrics["is_critical"] = metrics["is_ap"] | (metrics["betweenness"] >= btw_p90)

    # ——— סיכום לפי אזור ———
    region_summary = metrics.groupby("region").agg(
        total_stops      = ("stop_id",     "count"),
        critical_stops   = ("is_critical", "sum"),
        ap_stops         = ("is_ap",       "sum"),
        avg_degree       = ("degree",      "mean"),
        avg_betweenness  = ("betweenness", "mean"),
        max_betweenness  = ("betweenness", "max"),
    ).reset_index()
    region_summary["pct_critical"] = (region_summary["critical_stops"] / region_summary["total_stops"] * 100).round(1)
    region_summary["pct_ap"]       = (region_summary["ap_stops"]       / region_summary["total_stops"] * 100).round(2)

    region_summary.to_csv(OUT_DIR / "regional_summary.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(OUT_DIR / "stops_with_region.csv", index=False, encoding="utf-8-sig")

    print(region_summary.to_string(index=False))

    # ——— גרפים ———
    regions = region_summary.sort_values("pct_critical", ascending=False)
    colors  = ["#2563eb","#dc2626","#16a34a","#d97706"]

    # גרף 1 — תחנות קריטיות לפי אזור
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].bar(regions["region"], regions["critical_stops"], color=colors)
    axes[0].set_title("מספר תחנות קריטיות לפי אזור")
    axes[0].set_ylabel("מספר תחנות")
    axes[1].bar(regions["region"], regions["pct_critical"], color=colors)
    axes[1].set_title("% תחנות קריטיות מכלל האזור")
    axes[1].set_ylabel("אחוז (%)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "critical_stations_by_region.png", dpi=150)
    plt.close()
    print("  ✓ critical_stations_by_region.png")

    # גרף 2 — AP לפי אזור
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(region_summary["region"], region_summary["pct_ap"], color=colors)
    ax.set_title("% Articulation Points לפי אזור")
    ax.set_ylabel("% מכלל תחנות האזור")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "ap_by_region.png", dpi=150)
    plt.close()
    print("  ✓ ap_by_region.png")

    # גרף 3 — Betweenness ממוצע לפי אזור
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(region_summary["region"], region_summary["avg_betweenness"], color=colors)
    ax.set_title("Betweenness Centrality ממוצע לפי אזור")
    ax.set_ylabel("Betweenness ממוצע")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "avg_betweenness_by_region.png", dpi=150)
    plt.close()
    print("  ✓ avg_betweenness_by_region.png")

    # גרף 4 — מפה לפי אזור
    df_map = metrics.dropna(subset=["lat","lon"])
    region_colors_map = {"מרכז":"#2563eb","צפון":"#16a34a","דרום":"#dc2626","ירושלים":"#d97706"}
    fig, ax = plt.subplots(figsize=(8, 11))
    for reg, grp in df_map.groupby("region"):
        c = region_colors_map.get(reg, "#6b7280")
        ax.scatter(grp["lon"], grp["lat"], s=2, alpha=0.3, color=c, label=reg)
    # סמן תחנות קריטיות
    critical = df_map[df_map["is_critical"]]
    ax.scatter(critical["lon"], critical["lat"], s=15, color="black", alpha=0.7, zorder=5, label="קריטי")
    ax.legend(markerscale=3, fontsize=9)
    ax.set_title("מפת תחנות לפי אזור + תחנות קריטיות (שחור)")
    ax.set_xlabel("קו אורך"); ax.set_ylabel("קו רוחב")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "stations_map_by_region.png", dpi=150)
    plt.close()
    print("  ✓ stations_map_by_region.png")

    # גרף 5 — השוואה כוללת (grouped bar)
    metrics_to_compare = ["pct_critical","pct_ap","avg_degree"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    titles = ["% תחנות קריטיות","% Articulation Points","Degree ממוצע"]
    for ax, col, title in zip(axes, metrics_to_compare, titles):
        ax.bar(region_summary["region"], region_summary[col], color=colors)
        ax.set_title(title)
    plt.suptitle("השוואה אזורית — רשת התחבורה הציבורית")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "regional_vulnerability_comparison.png", dpi=150)
    plt.close()
    print("  ✓ regional_vulnerability_comparison.png")

    print(f"\nפלטים נשמרו ב:\n  {OUT_DIR}\n  {FIG_DIR}")

if __name__ == "__main__":
    main()

"""
Build a curated folder of presentation-ready figures.

Matplotlib does not handle Hebrew bidirectional text reliably in this project
environment, so Hebrew characters are reversed before plotting. English terms,
numbers, and acronyms are protected so technical labels stay readable.
The README remains normal Hebrew because Markdown renders RTL text correctly.
"""
from __future__ import annotations

import json
import pickle
import re
import textwrap
from pathlib import Path

import matplotlib
import networkx as nx
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter
from sklearn.decomposition import PCA


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "public_transport_network_research"
OUT_DIR = RESEARCH / "figures" / "presentation_key_findings"

GRAPH_PKL = RESEARCH / "02_graph_construction/outputs/graph_undirected.pkl"
SPATIAL_SUMMARY_JSON = RESEARCH / "03_network_descriptive_analysis/outputs/network_summary.json"
PRIMARY_SUMMARY_JSON = ROOT / "outputs/summary.json"
METRICS_CSV = RESEARCH / "04_centrality_analysis/outputs/stop_metrics.csv"
CENTRALITY_CORR_CSV = RESEARCH / "04_centrality_analysis/outputs/centrality_correlation_spearman.csv"
DISRUPTION_CSV = RESEARCH / "05_robustness_and_disruption_analysis/outputs/disruption_results.csv"
REGIONAL_CSV = RESEARCH / "06_regional_comparison/outputs/regional_summary.csv"
STOPS_WITH_REGION_CSV = RESEARCH / "06_regional_comparison/outputs/stops_with_region.csv"
SOCIO_CLUSTER_CSV = RESEARCH / "06_regional_comparison/outputs/socioeconomic_cluster_summary.csv"
SOCIO_CORR_CSV = RESEARCH / "06_regional_comparison/outputs/socioeconomic_correlation_summary.csv"
SOCIO_STOPS_CSV = RESEARCH / "06_regional_comparison/outputs/stops_with_socioeconomic.csv"
COMMUNITY_SUMMARY_CSV = RESEARCH / "07_community_detection/outputs/community_summary.csv"
COMMUNITY_ASSIGN_CSV = RESEARCH / "07_community_detection/outputs/community_assignments.csv"
EMBEDDINGS_CSV = RESEARCH / "08_graph_learning_node_embeddings/outputs/embeddings_df.csv"
LINK_RESULTS_CSV = RESEARCH / "09_link_prediction_and_network_improvement/outputs/link_prediction_results.csv"
TOP_LINKS_CSV = RESEARCH / "09_link_prediction_and_network_improvement/outputs/top_k_suggested_links.csv"

FIGURE_DPI = 180
PALETTE = {
    "blue": "#2563eb",
    "teal": "#0f766e",
    "green": "#16a34a",
    "orange": "#f97316",
    "red": "#dc2626",
    "purple": "#7c3aed",
    "pink": "#db2777",
    "gray": "#64748b",
    "dark": "#111827",
    "light": "#cbd5e1",
}

REGION_HE = {
    "מרכז": "מרכז",
    "צפון": "צפון",
    "דרום": "דרום",
    "ירושלים": "ירושלים",
}

CENTRALITY_HE = {
    "degree": "Degree",
    "degree_centrality": "Degree Centrality",
    "pagerank": "PageRank",
    "betweenness": "Betweenness",
    "harmonic": "Harmonic",
}

HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
LTR_TOKEN_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9+/#_.:%-]*(?:\s+[A-Za-z0-9][A-Za-z0-9+/#_.:%-]*)*"
)


def rtl(text: object) -> str:
    """Reverse Hebrew line-by-line for Matplotlib while preserving English tokens."""
    lines = []
    for line in str(text).split("\n"):
        if not HEBREW_RE.search(line):
            lines.append(line)
            continue

        protected: dict[str, str] = {}

        def protect(match: re.Match[str]) -> str:
            placeholder = chr(0xE000 + len(protected))
            protected[placeholder] = match.group(0)
            return placeholder

        prepared = LTR_TOKEN_RE.sub(protect, line)
        visual = prepared[::-1]
        for placeholder, original in protected.items():
            visual = visual.replace(placeholder, original)
        lines.append(visual)
    return "\n".join(lines)


def set_title(ax: plt.Axes, text: str, **kwargs) -> None:
    ax.set_title(rtl(text), **kwargs)


def set_xlabel(ax: plt.Axes, text: str, **kwargs) -> None:
    ax.set_xlabel(rtl(text), **kwargs)


def set_ylabel(ax: plt.Axes, text: str, **kwargs) -> None:
    ax.set_ylabel(rtl(text), **kwargs)


def he_region(value: object) -> str:
    return REGION_HE.get(str(value), str(value))


def ensure_output_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in OUT_DIR.glob("*.png"):
        path.unlink()


def save(fig: plt.Figure, filename: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT_DIR / filename, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)


def fmt_int(value, _pos=None) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def fmt_pct(value, _pos=None) -> str:
    return f"{value:.0%}"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_graph() -> nx.Graph:
    with GRAPH_PKL.open("rb") as f:
        return pickle.load(f)


def components_by_size(graph: nx.Graph) -> list[set]:
    return sorted(nx.connected_components(graph), key=len, reverse=True)


def graph_nodes_df(graph: nx.Graph, lcc: set | None = None) -> pd.DataFrame:
    rows = []
    for node, attrs in graph.nodes(data=True):
        lat = attrs.get("lat")
        lon = attrs.get("lon")
        if lat is None or lon is None:
            continue
        rows.append(
            {
                "stop_id": str(node),
                "lat": float(lat),
                "lon": float(lon),
                "region": attrs.get("region", ""),
                "in_lcc": bool(lcc and node in lcc),
            }
        )
    return pd.DataFrame(rows)


def strategy_key(value: str) -> str:
    text = str(value).lower()
    if "betweenness" in text:
        return "Betweenness"
    if "pagerank" in text:
        return "PageRank"
    if "degree" in text:
        return "Degree"
    if "ap" in text or "articulation" in text:
        return "Articulation Points"
    if "random" in text:
        return "Random"
    return str(value)


def metric_label(column: str) -> str:
    return CENTRALITY_HE.get(column, column)


def bbox_filter(df: pd.DataFrame, lon_min: float, lon_max: float, lat_min: float, lat_max: float) -> pd.DataFrame:
    return df[(df["lon"].between(lon_min, lon_max)) & (df["lat"].between(lat_min, lat_max))].copy()


def annotate_stop_ids(ax: plt.Axes, df: pd.DataFrame, color: str = "#111827") -> None:
    for _, row in df.iterrows():
        ax.text(row["lon"], row["lat"], str(row["stop_id"]), fontsize=7, color=color, ha="left", va="bottom")


def plot_graph_model_comparison() -> None:
    spatial = load_json(SPATIAL_SUMMARY_JSON)
    primary = load_json(PRIMARY_SUMMARY_JSON)["network_summary"]

    rows = pd.DataFrame(
        [
            {
                "model": rtl("גרף נסיעות"),
                "components": primary["connected_components"],
                "largest_component_share": primary["largest_component_share"],
                "articulation_points": primary["articulation_points"],
                "bridges": primary["bridges"],
            },
            {
                "model": rtl("גרף קרבה חצי קמ"),
                "components": spatial["num_connected_components"],
                "largest_component_share": spatial["largest_component_share"],
                "articulation_points": spatial["num_articulation_points"],
                "bridges": spatial["num_bridges"],
            },
        ]
    )

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    sns.barplot(data=rows, x="model", y="components", hue="model", legend=False, ax=axes[0],
                palette=[PALETTE["green"], PALETTE["orange"]])
    set_title(axes[0], "רכיבי קשירות")
    axes[0].set_xlabel("")
    set_ylabel(axes[0], "כמות")
    axes[0].yaxis.set_major_formatter(FuncFormatter(fmt_int))
    axes[0].tick_params(axis="x", rotation=12)

    sns.barplot(data=rows, x="model", y="largest_component_share", hue="model", legend=False, ax=axes[1],
                palette=[PALETTE["green"], PALETTE["orange"]])
    set_title(axes[1], "חלק הרכיב הגדול")
    axes[1].set_xlabel("")
    set_ylabel(axes[1], "חלק מכל התחנות")
    axes[1].yaxis.set_major_formatter(FuncFormatter(fmt_pct))
    axes[1].set_ylim(0, 1.05)
    axes[1].tick_params(axis="x", rotation=12)

    long = rows.melt(
        id_vars="model",
        value_vars=["articulation_points", "bridges"],
        var_name="metric",
        value_name="count",
    )
    long["metric"] = long["metric"].map(
        {"articulation_points": "Articulation Points", "bridges": "Bridges"}
    )
    sns.barplot(data=long, x="metric", y="count", hue="model", ax=axes[2],
                palette=[PALETTE["green"], PALETTE["orange"]])
    set_title(axes[2], "נקודות פגיעות מבניות")
    axes[2].set_xlabel("")
    set_ylabel(axes[2], "כמות")
    axes[2].yaxis.set_major_formatter(FuncFormatter(fmt_int))
    axes[2].legend(title="", fontsize=8)

    fig.suptitle(rtl("שני מודלים של הרשת מספרים סיפור שונה"), fontsize=16, weight="bold", y=1.03)
    save(fig, "01_graph_model_comparison.png")


def plot_connectivity_overview() -> None:
    summary = load_json(SPATIAL_SUMMARY_JSON)
    lcc = summary["largest_component_nodes"]
    total = summary["num_nodes"]
    other = total - lcc

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5))
    axes[0].bar([rtl("הרכיב הגדול"), rtl("שאר הרכיבים")], [lcc, other],
                color=[PALETTE["blue"], PALETTE["gray"]])
    set_title(axes[0], "פירוק רשת הנסיעות לרכיבים")
    set_ylabel(axes[0], "תחנות")
    axes[0].yaxis.set_major_formatter(FuncFormatter(fmt_int))
    for i, value in enumerate([lcc, other]):
        axes[0].text(i, value, f"{value:,}\n({value / total:.1%})", ha="center", va="bottom", fontsize=10)

    metrics = [
        ("תחנות", summary["num_nodes"]),
        ("קשתות", summary["num_edges_undirected"]),
        ("רכיבים", summary["num_connected_components"]),
        ("Articulation\nPoints", summary["num_articulation_points"]),
        ("Bridges", summary["num_bridges"]),
    ]
    axes[1].axis("off")
    for idx, (label, value) in enumerate(metrics):
        row, col = divmod(idx, 3)
        x = 0.05 + col * 0.31
        y = 0.67 - row * 0.38
        axes[1].text(x, y + 0.12, rtl(label), fontsize=11, color=PALETTE["gray"], transform=axes[1].transAxes)
        axes[1].text(x, y, f"{value:,}", fontsize=21, weight="bold", color=PALETTE["dark"],
                     transform=axes[1].transAxes)
    metric_parts = [
        (0.05, "Avg Degree", PALETTE["gray"]),
        (0.25, f"{summary['avg_degree']:.2f}", PALETTE["blue"]),
        (0.40, rtl("צפיפות"), PALETTE["gray"]),
        (0.55, f"{summary['density']:.5f}", PALETTE["blue"]),
    ]
    for x, value, color in metric_parts:
        axes[1].text(
            x,
            0.08,
            value,
            fontsize=11,
            color=color,
            transform=axes[1].transAxes,
        )

    fig.suptitle(rtl("ממצא בסיסי: רשת הנסיעות מחוברת מאוד"), fontsize=16, weight="bold", y=1.02)
    save(fig, "02_connectivity_overview.png")


def plot_component_rank_size(graph: nx.Graph) -> None:
    sizes = np.array([len(c) for c in components_by_size(graph)])
    ranks = np.arange(1, len(sizes) + 1)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(ranks, sizes, color=PALETTE["blue"], linewidth=2)
    axes[0].set_yscale("log")
    set_title(axes[0], "גודל רכיב לפי דירוג")
    set_xlabel(axes[0], "דירוג רכיב")
    set_ylabel(axes[0], "תחנות, סולם לוגריתמי")
    axes[0].yaxis.set_major_formatter(FuncFormatter(fmt_int))

    top = sizes[:20][::-1]
    labels = [str(i) for i in range(len(top), 0, -1)]
    axes[1].barh(labels, top, color=PALETTE["teal"])
    set_title(axes[1], "הרכיבים הגדולים ביותר")
    set_xlabel(axes[1], "תחנות")
    axes[1].xaxis.set_major_formatter(FuncFormatter(fmt_int))

    fig.suptitle(rtl("רוב הרכיבים קטנים, ורכיב אחד בולט מעל כולם"), fontsize=16, weight="bold", y=1.02)
    save(fig, "03_component_size_distribution.png")


def plot_lcc_map(graph: nx.Graph) -> None:
    lcc = components_by_size(graph)[0]
    df = graph_nodes_df(graph, lcc)

    fig, ax = plt.subplots(figsize=(8, 10.5))
    other = df[~df["in_lcc"]]
    main = df[df["in_lcc"]]
    ax.scatter(other["lon"], other["lat"], s=2.2, alpha=0.22, color=PALETTE["gray"], label=rtl("רכיבים אחרים"))
    ax.scatter(main["lon"], main["lat"], s=4, alpha=0.65, color=PALETTE["blue"], label=rtl("הרכיב הגדול"))
    set_title(ax, "הרכיב הקשיר הגדול במרחב הגיאוגרפי")
    set_xlabel(ax, "קו אורך")
    set_ylabel(ax, "קו רוחב")
    ax.legend(markerscale=5, frameon=True)
    save(fig, "04_largest_component_map.png")


def plot_degree_distribution(metrics: pd.DataFrame) -> None:
    degree = pd.to_numeric(metrics["degree"], errors="coerce").dropna()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].hist(degree, bins=50, color=PALETTE["blue"], alpha=0.9)
    set_title(axes[0], "התפלגות דרגות")
    axes[0].set_xlabel("Degree")
    set_ylabel(axes[0], "תחנות")
    axes[0].yaxis.set_major_formatter(FuncFormatter(fmt_int))

    counts = degree.value_counts().sort_index()
    axes[1].scatter(counts.index, counts.values, s=18, color=PALETTE["purple"], alpha=0.75)
    axes[1].set_yscale("log")
    set_title(axes[1], "זנב ההתפלגות בסולם לוגריתמי")
    axes[1].set_xlabel("Degree")
    set_ylabel(axes[1], "תחנות, לוג")
    axes[1].yaxis.set_major_formatter(FuncFormatter(fmt_int))
    fig.suptitle(rtl("מעט תחנות מרכזות הרבה מאוד קשרי נסיעה"), fontsize=16, weight="bold", y=1.02)
    save(fig, "05_degree_distribution.png")


def stop_bar(metrics: pd.DataFrame, column: str, filename: str, title: str, color: str) -> None:
    top = metrics.copy()
    top[column] = pd.to_numeric(top[column], errors="coerce").fillna(0)
    top = top.sort_values(column, ascending=False).head(12).iloc[::-1]
    top["short_name"] = top["stop_name"].astype(str).str.slice(0, 24)
    top["label"] = top["stop_id"].astype(str) + " | " + top["short_name"].map(rtl)

    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.barh(top["label"], top[column], color=color)
    set_title(ax, title)
    set_xlabel(ax, metric_label(column))
    set_ylabel(ax, "תחנה")
    if top[column].max() < 1:
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _pos: f"{x:.3f}"))
    else:
        ax.xaxis.set_major_formatter(FuncFormatter(fmt_int))
    save(fig, filename)


def plot_centrality_figures(metrics: pd.DataFrame) -> None:
    stop_bar(metrics, "degree", "06_top_degree_stops.png", "תחנות מובילות לפי Degree", PALETTE["blue"])
    stop_bar(metrics, "betweenness", "07_top_betweenness_stops.png", "תחנות מובילות לפי Betweenness", PALETTE["red"])
    stop_bar(metrics, "pagerank", "08_top_pagerank_stops.png", "תחנות מובילות לפי PageRank", PALETTE["green"])

    corr = pd.read_csv(CENTRALITY_CORR_CSV, encoding="utf-8-sig", index_col=0)
    labels = [rtl(CENTRALITY_HE.get(col, col)) for col in corr.columns]
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="vlag", center=0, square=True, ax=ax, cbar_kws={"shrink": 0.8})
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_yticklabels(labels, rotation=0)
    set_title(ax, "מתאם בין מדדי Centrality")
    save(fig, "09_centrality_correlation.png")


def plot_robustness() -> None:
    df = pd.read_csv(DISRUPTION_CSV, encoding="utf-8-sig")
    df["strategy_key"] = df["strategy"].map(strategy_key)
    order = ["Degree", "Betweenness", "PageRank", "Articulation Points", "Random"]
    order = [item for item in order if item in set(df["strategy_key"])]

    fig, ax = plt.subplots(figsize=(11, 6))
    palette = [PALETTE["red"], PALETTE["purple"], PALETTE["green"], PALETTE["orange"], PALETTE["gray"]]
    for idx, strategy in enumerate(order):
        part = df[df["strategy_key"] == strategy].sort_values("removed")
        ax.plot(part["removed"], part["lcc_share"], linewidth=2.5, label=rtl(strategy), color=palette[idx % len(palette)])
    set_title(ax, "עמידות הרשת תחת הסרת תחנות מכוונת")
    set_xlabel(ax, "מספר תחנות שהוסרו")
    set_ylabel(ax, "חלק הרכיב הגדול")
    ax.yaxis.set_major_formatter(FuncFormatter(fmt_pct))
    ax.legend(title="", ncol=2, fontsize=9)
    save(fig, "10_resilience_curves.png")

    last = df.sort_values("removed").groupby("strategy_key").tail(1)
    baseline = float(df[df["removed"] == 0]["lcc_share"].iloc[0])
    last["lcc_share_drop"] = baseline - last["lcc_share"]
    last = last.sort_values("lcc_share_drop", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.barh(last["strategy_key"].map(rtl), last["lcc_share_drop"], color=PALETTE["red"])
    set_title(ax, "נזק לאחר ההסרה המקסימלית בסימולציה")
    set_xlabel(ax, "ירידה בחלק הרכיב הגדול")
    ax.xaxis.set_major_formatter(FuncFormatter(fmt_pct))
    save(fig, "11_resilience_final_damage.png")


def plot_regional() -> None:
    regional = pd.read_csv(REGIONAL_CSV, encoding="utf-8-sig")
    regional["region_he"] = regional["region"].map(he_region).map(rtl)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    colors = [PALETTE["blue"], PALETTE["green"], PALETTE["orange"], PALETTE["red"]]

    sns.barplot(data=regional, x="region_he", y="total_stops", hue="region_he", legend=False, palette=colors, ax=axes[0])
    set_title(axes[0], "תחנות לפי אזור")
    axes[0].set_xlabel("")
    set_ylabel(axes[0], "תחנות")
    axes[0].yaxis.set_major_formatter(FuncFormatter(fmt_int))

    sns.barplot(data=regional, x="region_he", y="pct_critical", hue="region_he", legend=False, palette=colors, ax=axes[1])
    set_title(axes[1], "אחוז תחנות קריטיות")
    axes[1].set_xlabel("")
    set_ylabel(axes[1], "אחוז קריטיות")

    sns.barplot(data=regional, x="region_he", y="avg_degree", hue="region_he", legend=False, palette=colors, ax=axes[2])
    set_title(axes[2], "Proximity Degree ממוצע")
    axes[2].set_xlabel("")
    axes[2].set_ylabel("Avg Degree")

    fig.suptitle(rtl("השוואה אזורית: חשיפה ופגיעות"), fontsize=16, weight="bold", y=1.02)
    save(fig, "12_regional_comparison.png")


def plot_communities() -> None:
    summary = pd.read_csv(COMMUNITY_SUMMARY_CSV, encoding="utf-8-sig")
    top = summary.sort_values("size", ascending=False).head(20).iloc[::-1]

    fig, ax = plt.subplots(figsize=(9.5, 7))
    ax.barh(top["community_id"].astype(str), top["size"], color=PALETTE["purple"])
    set_title(ax, "קהילות Louvain הגדולות ביותר")
    set_xlabel(ax, "תחנות")
    set_ylabel(ax, "מספר קהילה")
    ax.xaxis.set_major_formatter(FuncFormatter(fmt_int))
    save(fig, "13_community_sizes.png")

    assign = pd.read_csv(COMMUNITY_ASSIGN_CSV, encoding="utf-8-sig")
    top_ids = set(summary.sort_values("size", ascending=False).head(12)["community_id"].astype(int))
    assign["plot_group"] = np.where(assign["community_louvain"].isin(top_ids), assign["community_louvain"].astype(str), "אחר")
    order = [str(i) for i in sorted(top_ids)] + ["אחר"]
    palette = sns.color_palette("tab20", n_colors=len(order))
    color_map = dict(zip(order, palette))

    fig, ax = plt.subplots(figsize=(8, 10.5))
    for group in order[::-1]:
        part = assign[assign["plot_group"] == group]
        size = 2.0 if group == "אחר" else 6
        alpha = 0.18 if group == "אחר" else 0.75
        ax.scatter(part["lon"], part["lat"], s=size, alpha=alpha, color=color_map[group], label=rtl(group))
    set_title(ax, "קהילות Louvain מרכזיות על המפה")
    set_xlabel(ax, "קו אורך")
    set_ylabel(ax, "קו רוחב")
    ax.legend(title="Louvain", markerscale=3, fontsize=8, ncol=2, frameon=True)
    save(fig, "14_community_map_top12.png")


def plot_socioeconomic() -> None:
    if not SOCIO_CLUSTER_CSV.exists() or not SOCIO_CORR_CSV.exists():
        return

    cluster = pd.read_csv(SOCIO_CLUSTER_CSV, encoding="utf-8-sig")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.lineplot(data=cluster, x="socio_cluster", y="median_area_stops_per_1000", marker="o",
                 color=PALETTE["blue"], linewidth=2.5, ax=axes[0])
    set_title(axes[0], "חציון תחנות לאלף תושבים")
    set_xlabel(axes[0], "אשכול חברתי-כלכלי")
    set_ylabel(axes[0], "חציון תחנות לאלף תושבים")
    axes[0].set_xticks(range(1, 11))

    sns.lineplot(data=cluster, x="socio_cluster", y="median_area_stop_use_count_per_1000", marker="o",
                 color=PALETTE["orange"], linewidth=2.5, ax=axes[1])
    set_title(axes[1], "חציון שירות לאלף תושבים")
    set_xlabel(axes[1], "אשכול חברתי-כלכלי")
    set_ylabel(axes[1], "חציון מופעי עצירה לאלף תושבים")
    axes[1].set_xticks(range(1, 11))
    fig.suptitle(rtl("זמינות תחבורה לפי אשכול חברתי-כלכלי"), fontsize=16, weight="bold", y=1.02)
    save(fig, "15_socioeconomic_access.png")

    corr = pd.read_csv(SOCIO_CORR_CSV, encoding="utf-8-sig")
    corr = corr[corr["scope"] == "statistical_area"].copy()
    label_map = {
        "stops_per_1000_residents": "תחנות לאלף תושבים",
        "stop_use_count_per_1000_residents": "שירות לאלף תושבים",
        "stop_use_count_per_stop": "שירות לתחנה",
        "avg_proximity_degree": "Proximity Degree",
        "critical_stop_share": "חלק תחנות קריטיות",
    }
    corr["label"] = corr["metric"].map(label_map).fillna(corr["metric"]).map(rtl)
    corr = corr.sort_values("spearman_rho")

    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    colors = [PALETTE["red"] if v < 0 else PALETTE["green"] for v in corr["spearman_rho"]]
    ax.barh(corr["label"], corr["spearman_rho"], color=colors)
    ax.axvline(0, color=PALETTE["dark"], linewidth=1)
    set_title(ax, "מתאם עם אשכול חברתי-כלכלי")
    set_xlabel(ax, "מתאם דירוג")
    save(fig, "16_socioeconomic_correlations.png")


def plot_link_prediction() -> None:
    results = pd.read_csv(LINK_RESULTS_CSV, encoding="utf-8-sig")
    method_map = {
        "Common Neighbors": "Common Neighbors",
        "Jaccard": "Jaccard",
        "Adamic-Adar": "Adamic-Adar",
        "Resource Allocation": "Resource Allocation",
        "Preferential Attachment": "Preferential Attachment",
        "Node2Vec + LR": "Node2Vec + LR",
    }
    results["method_he"] = results["method"].map(method_map).fillna(results["method"]).map(rtl)
    results = results.sort_values("auc", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.barh(results["method_he"], results["auc"], color=PALETTE["teal"])
    ax.set_xlim(0.5, 1.01)
    set_title(ax, "ביצועי Link Prediction")
    ax.set_xlabel("AUC")
    for y, value in enumerate(results["auc"]):
        ax.text(value + 0.005, y, f"{value:.3f}", va="center", fontsize=9)
    save(fig, "17_link_prediction_auc.png")


def plot_embeddings(metrics: pd.DataFrame) -> None:
    if not EMBEDDINGS_CSV.exists():
        return

    embeddings = pd.read_csv(EMBEDDINGS_CSV, encoding="utf-8-sig")
    embeddings["stop_id"] = embeddings["stop_id"].astype(str)
    feature_cols = [col for col in embeddings.columns if col.startswith("e")]
    coords = PCA(n_components=2, random_state=42).fit_transform(embeddings[feature_cols])
    emb = embeddings[["stop_id"]].copy()
    emb["pc1"] = coords[:, 0]
    emb["pc2"] = coords[:, 1]

    labels = pd.read_csv(STOPS_WITH_REGION_CSV, encoding="utf-8-sig")
    labels["stop_id"] = labels["stop_id"].astype(str)
    emb = emb.merge(labels[["stop_id", "region", "is_critical"]], on="stop_id", how="left")
    emb["is_critical"] = emb["is_critical"].astype(str).str.lower().isin(["true", "1"])

    fig, ax = plt.subplots(figsize=(8.5, 7))
    normal = emb[~emb["is_critical"]]
    critical = emb[emb["is_critical"]]
    ax.scatter(normal["pc1"], normal["pc2"], s=4, alpha=0.18, color=PALETTE["gray"], label=rtl("לא קריטי"))
    ax.scatter(critical["pc1"], critical["pc2"], s=10, alpha=0.7, color=PALETTE["red"], label=rtl("קריטי"))
    set_title(ax, "Node2Vec Embeddings לפי קריטיות")
    ax.set_xlabel("PCA 1")
    ax.set_ylabel("PCA 2")
    ax.legend(frameon=True)
    save(fig, "18_embedding_pca_by_critical.png")

    fig, ax = plt.subplots(figsize=(8.5, 7))
    colors = {
        "מרכז": PALETTE["blue"],
        "צפון": PALETTE["green"],
        "דרום": PALETTE["orange"],
        "ירושלים": PALETTE["red"],
    }
    for region, group in emb.groupby("region"):
        ax.scatter(group["pc1"], group["pc2"], s=5, alpha=0.35, color=colors.get(region, PALETTE["gray"]),
                   label=rtl(he_region(region)))
    set_title(ax, "Node2Vec Embeddings לפי אזור")
    ax.set_xlabel("PCA 1")
    ax.set_ylabel("PCA 2")
    ax.legend(frameon=True, markerscale=3)
    save(fig, "19_embedding_pca_by_region.png")


def plot_suggested_links_map(graph: nx.Graph) -> None:
    if not TOP_LINKS_CSV.exists():
        return
    links = pd.read_csv(TOP_LINKS_CSV, encoding="utf-8-sig").head(20)
    nodes = graph_nodes_df(graph)
    coords = nodes.set_index("stop_id")[["lat", "lon"]]

    rows = []
    for _, row in links.iterrows():
        a = str(row["stop_a"])
        b = str(row["stop_b"])
        if a in coords.index and b in coords.index:
            rows.append(
                {
                    "a": a,
                    "b": b,
                    "lat_a": coords.loc[a, "lat"],
                    "lon_a": coords.loc[a, "lon"],
                    "lat_b": coords.loc[b, "lat"],
                    "lon_b": coords.loc[b, "lon"],
                    "score": row["cosine_sim"],
                }
            )
    line_df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(8, 10.5))
    ax.scatter(nodes["lon"], nodes["lat"], s=2, alpha=0.12, color=PALETTE["gray"], label=rtl("תחנות"))
    for _, row in line_df.iterrows():
        ax.plot([row["lon_a"], row["lon_b"]], [row["lat_a"], row["lat_b"]], color=PALETTE["red"], alpha=0.8, linewidth=1.4)
    if not line_df.empty:
        ax.scatter(line_df[["lon_a", "lon_b"]].to_numpy().ravel(), line_df[["lat_a", "lat_b"]].to_numpy().ravel(),
                   s=18, color=PALETTE["red"], alpha=0.9, label=rtl("הצעות קישור"))
    set_title(ax, "הצעות קישור חדשות לפי Node2Vec")
    set_xlabel(ax, "קו אורך")
    set_ylabel(ax, "קו רוחב")
    ax.legend(frameon=True, markerscale=3)
    save(fig, "20_suggested_links_map.png")


def plot_zoom_lcc_center(graph: nx.Graph) -> None:
    lcc = components_by_size(graph)[0]
    nodes = graph_nodes_df(graph, lcc)
    zoom = bbox_filter(nodes, 34.68, 35.00, 31.88, 32.18)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(zoom.loc[~zoom["in_lcc"], "lon"], zoom.loc[~zoom["in_lcc"], "lat"],
               s=4, alpha=0.18, color=PALETTE["gray"], label=rtl("רכיבים אחרים"))
    ax.scatter(zoom.loc[zoom["in_lcc"], "lon"], zoom.loc[zoom["in_lcc"], "lat"],
               s=8, alpha=0.75, color=PALETTE["blue"], label=rtl("הרכיב הגדול"))
    set_title(ax, "זום: הרכיב הגדול בגוש דן")
    set_xlabel(ax, "קו אורך")
    set_ylabel(ax, "קו רוחב")
    ax.legend(frameon=True, markerscale=3)
    save(fig, "21_zoom_lcc_center.png")


def plot_zoom_top_degree(graph: nx.Graph, metrics: pd.DataFrame) -> None:
    nodes = graph_nodes_df(graph)
    top = metrics.copy()
    top["degree"] = pd.to_numeric(top["degree"], errors="coerce").fillna(0)
    top = top.sort_values("degree", ascending=False).head(15)
    zoom = bbox_filter(nodes, 34.755, 34.795, 32.045, 32.070)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(zoom["lon"], zoom["lat"], s=8, alpha=0.22, color=PALETTE["gray"], label=rtl("תחנות באזור"))
    ax.scatter(top["lon"], top["lat"], s=60, color=PALETTE["blue"], edgecolor="white", linewidth=0.7,
               label=rtl("תחנות High Degree"))
    annotate_stop_ids(ax, top, color=PALETTE["dark"])
    set_title(ax, "זום: ריכוז High Degree סביב התחנה המרכזית תל אביב")
    set_xlabel(ax, "קו אורך")
    set_ylabel(ax, "קו רוחב")
    ax.legend(frameon=True)
    save(fig, "22_zoom_tel_aviv_top_degree.png")


def plot_zoom_betweenness_corridor(graph: nx.Graph, metrics: pd.DataFrame) -> None:
    nodes = graph_nodes_df(graph)
    top = metrics.copy()
    top["betweenness"] = pd.to_numeric(top["betweenness"], errors="coerce").fillna(0)
    top = top.sort_values("betweenness", ascending=False).head(15)
    zoom = bbox_filter(nodes, 34.745, 34.815, 31.955, 32.055)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(zoom["lon"], zoom["lat"], s=7, alpha=0.20, color=PALETTE["gray"], label=rtl("תחנות באזור"))
    ax.scatter(top["lon"], top["lat"], s=58, color=PALETTE["red"], edgecolor="white", linewidth=0.7,
               label=rtl("תחנות High Betweenness"))
    annotate_stop_ids(ax, top, color=PALETTE["dark"])
    set_title(ax, "זום: מסדרון High Betweenness בדרום גוש דן")
    set_xlabel(ax, "קו אורך")
    set_ylabel(ax, "קו רוחב")
    ax.legend(frameon=True)
    save(fig, "23_zoom_betweenness_corridor.png")


def plot_zoom_communities() -> None:
    assign = pd.read_csv(COMMUNITY_ASSIGN_CSV, encoding="utf-8-sig")
    summary = pd.read_csv(COMMUNITY_SUMMARY_CSV, encoding="utf-8-sig")
    top_ids = set(summary.sort_values("size", ascending=False).head(8)["community_id"].astype(int))
    zoom = bbox_filter(assign, 34.70, 34.93, 31.93, 32.13)
    zoom["plot_group"] = np.where(zoom["community_louvain"].isin(top_ids), zoom["community_louvain"].astype(str), "אחר")
    order = [str(i) for i in sorted(top_ids)] + ["אחר"]
    palette = sns.color_palette("tab10", n_colors=len(order))
    color_map = dict(zip(order, palette))

    fig, ax = plt.subplots(figsize=(8, 8))
    for group in order[::-1]:
        part = zoom[zoom["plot_group"] == group]
        alpha = 0.16 if group == "אחר" else 0.75
        size = 4 if group == "אחר" else 14
        ax.scatter(part["lon"], part["lat"], s=size, alpha=alpha, color=color_map[group], label=rtl(group))
    set_title(ax, "זום: קהילות Louvain בגוש דן")
    set_xlabel(ax, "קו אורך")
    set_ylabel(ax, "קו רוחב")
    ax.legend(title="Louvain", frameon=True, fontsize=8, markerscale=2, ncol=2)
    save(fig, "24_zoom_communities_gush_dan.png")


def plot_zoom_socioeconomic() -> None:
    if not SOCIO_STOPS_CSV.exists():
        return
    stops = pd.read_csv(SOCIO_STOPS_CSV, encoding="utf-8-sig")
    zoom = bbox_filter(stops.dropna(subset=["socio_cluster"]), 34.70, 34.93, 31.93, 32.13)
    zoom["group"] = pd.cut(
        zoom["socio_cluster"].astype(float),
        bins=[0, 4, 7, 10],
        labels=["אשכול נמוך", "אשכול ביניים", "אשכול גבוה"],
    )
    colors = {"אשכול נמוך": PALETTE["red"], "אשכול ביניים": PALETTE["orange"], "אשכול גבוה": PALETTE["green"]}

    fig, ax = plt.subplots(figsize=(8, 8))
    for group, part in zoom.groupby("group", observed=True):
        ax.scatter(part["lon"], part["lat"], s=8, alpha=0.55, color=colors[str(group)], label=rtl(group))
    set_title(ax, "זום: אשכולות חברתיים-כלכליים בגוש דן")
    set_xlabel(ax, "קו אורך")
    set_ylabel(ax, "קו רוחב")
    ax.legend(frameon=True, markerscale=3)
    save(fig, "25_zoom_socioeconomic_gush_dan.png")


def plot_zoom_link_suggestions(graph: nx.Graph) -> None:
    if not TOP_LINKS_CSV.exists():
        return
    links = pd.read_csv(TOP_LINKS_CSV, encoding="utf-8-sig").head(20)
    nodes = graph_nodes_df(graph)
    coords = nodes.set_index("stop_id")[["lat", "lon"]]
    zoom = bbox_filter(nodes, 34.72, 34.86, 31.96, 32.10)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(zoom["lon"], zoom["lat"], s=6, alpha=0.17, color=PALETTE["gray"], label=rtl("תחנות באזור"))
    for _, row in links.iterrows():
        a = str(row["stop_a"])
        b = str(row["stop_b"])
        if a not in coords.index or b not in coords.index:
            continue
        lon_a, lat_a = coords.loc[a, "lon"], coords.loc[a, "lat"]
        lon_b, lat_b = coords.loc[b, "lon"], coords.loc[b, "lat"]
        if 34.72 <= lon_a <= 34.86 and 31.96 <= lat_a <= 32.10:
            ax.plot([lon_a, lon_b], [lat_a, lat_b], color=PALETTE["red"], alpha=0.85, linewidth=1.7)
            ax.scatter([lon_a, lon_b], [lat_a, lat_b], s=25, color=PALETTE["red"], alpha=0.9)
    set_title(ax, "זום: קישורים מוצעים באזור המרכז")
    set_xlabel(ax, "קו אורך")
    set_ylabel(ax, "קו רוחב")
    ax.legend(frameon=True, markerscale=3)
    save(fig, "26_zoom_link_suggestions_gush_dan.png")


def write_readme() -> None:
    text = """# גרפים מרכזיים למצגת

התיקייה הזו מכילה סט גרפים מסודר לשימוש במצגת. בגרפים עצמם הטקסט העברי מוזן הפוך ל-Matplotlib כדי לעקוף את בעיית ה-RTL, אבל מושגים מקצועיים באנגלית כמו Degree, Betweenness, PageRank, Louvain, Node2Vec ו-AUC נשארים באנגלית רגילה. בקובץ הזה העברית כתובה רגיל.

## סדר מומלץ במצגת

1. להתחיל בהבדל בין שני מודלי הרשת: גרף נסיעות מול גרף קרבה.
2. להראות שרשת הקרבה מפוצלת מאוד מבחינת רכיבי קשירות.
3. להראות מי התחנות המרכזיות לפי מדדי Centrality שונים.
4. להראות מה קורה בסימולציית שיבושים.
5. לעבור להשוואה אזורית ולקהילות Louvain.
6. להוסיף את שכבת ה-equity: מדד חברתי-כלכלי מול זמינות תחבורה.
7. לסיים בהצעות שיפור דרך Link Prediction.

## הסבר לפי גרף

### 01_graph_model_comparison.png
משווה בין גרף הנסיעות הראשי לבין גרף הקרבה של 500 מטר. זה גרף פתיחה חשוב כי הוא מונע בלבול: גרף הנסיעות כמעט מחובר כולו, בעוד גרף הקרבה מפוצל מאוד. במצגת כדאי לומר שהמשך הניתוח ב-public_transport_network_research מתאר בעיקר קרבה מרחבית, לא בהכרח רצף נסיעה אמיתי.

### 02_connectivity_overview.png
מסכם את מספר התחנות, הקשתות, הרכיבים, Articulation Points ו-Bridges. הממצא הקריטי: רק חלק קטן מהתחנות נמצא ברכיב הקשיר הגדול של גרף הקרבה. זה הבסיס לכל טענת הפגיעות המבנית.

### 03_component_size_distribution.png
מראה את גודל הרכיבים לפי דירוג ואת 20 הרכיבים הגדולים. מתאים להסביר שהרשת אינה מתפרקת לשני חלקים גדולים, אלא להרבה רכיבים קטנים ועוד רכיב מרכזי אחד.

### 04_largest_component_map.png
מפה ארצית של הרכיב הקשיר הגדול מול שאר הרכיבים. הממצא הוויזואלי: הרכיב הגדול מרוכז באזור המרכז, ושאר הארץ מופיעה כאיים מרחביים רבים.

### 05_degree_distribution.png
התפלגות הדרגות בגרף הקרבה. מתאים להסביר שיש זנב ארוך: רוב התחנות מחוברות למספר סביר של שכנות קרובות, אבל מעט תחנות מקבלות הרבה מאוד קשרים ולכן הן בולטות כמרכזים מקומיים.

### 06_top_degree_stops.png
תחנות מובילות לפי Degree. זה מדגיש צפיפות מקומית: תחנות סביב התחנה המרכזית תל אביב ולוינסקי מקבלות Degree גבוה מאוד בגלל ריכוז תחנות סמוכות.

### 07_top_betweenness_stops.png
תחנות מובילות לפי Betweenness. זה מדגיש תחנות שנמצאות על מסלולים קצרים רבים בתוך הרכיב הגדול. כדאי להדגיש שזה מדד של "גשר פנימי" ולא רק של צפיפות.

### 08_top_pagerank_stops.png
תחנות מובילות לפי PageRank. מתאים להראות שמרכזיות יכולה להימדד גם דרך איכות השכנים ולא רק כמותם.

### 09_centrality_correlation.png
מפת חום של מתאם בין מדדי Centrality. המטרה היא להסביר למה לא מספיק לבחור מדד אחד: Degree, PageRank, Betweenness ו-Harmonic לא מודדים בדיוק אותו תפקיד ברשת.

### 10_resilience_curves.png
עקומות עמידות תחת הסרת תחנות לפי אסטרטגיות שונות. זה הגרף המרכזי של Robustness. אם העקומה יורדת מהר יותר, האסטרטגיה פוגעת יותר ברכיב הגדול.

### 11_resilience_final_damage.png
סיכום הנזק בסוף סימולציית ההסרה. מתאים לשקף קצר שמראה מי אסטרטגיית ההסרה הכי מזיקה.

### 12_regional_comparison.png
השוואה אזורית: מספר תחנות, אחוז קריטיות ו-Avg Degree. הממצא החשוב הוא שהמרכז דומיננטי גם בכמות התחנות וגם בשיעור התחנות הקריטיות בגרף הקרבה.

### 13_community_sizes.png
גודל קהילות Louvain הגדולות. מתאים להציג את העובדה שהרשת מתארגנת לאשכולות מבניים מקומיים.

### 14_community_map_top12.png
מפת הקהילות המרכזיות. זה טוב לשקף ש-Community Detection יוצר אזורי תחבורה טבעיים ולא רק חלוקה מנהלית.

### 15_socioeconomic_access.png
מדדי זמינות תחבורה לפי אשכול חברתי-כלכלי. השתמשתי בחציון ברמת אזור סטטיסטי כדי לא לתת לאשכול קטן מדי להכתיב את המסקנה. הגרף מבחין בין כיסוי תחנות לבין עוצמת שירות.

### 16_socioeconomic_correlations.png
מתאמי Spearman בין אשכול חברתי-כלכלי לבין מדדי זמינות. מתאים לשקף מסקנה: הקשרים קיימים אבל חלשים, ולכן צריך להציג את זה כניתוח equity זהיר ולא כסיבתיות.

### 17_link_prediction_auc.png
השוואת שיטות Link Prediction לפי AUC. מתאים להראות ששיטות מבניות כמו Jaccard ו-Resource Allocation מצליחות מאוד, בעוד Preferential Attachment חלשה יותר.

### 18_embedding_pca_by_critical.png
הטמעות Node2Vec אחרי PCA, בצביעה לפי תחנות קריטיות. מתאים להראות האם תחנות קריטיות נבדלות במרחב Embedding.

### 19_embedding_pca_by_region.png
הטמעות Node2Vec אחרי PCA, בצביעה לפי אזור. מתאים להראות האם המבנה הנלמד משמר הפרדה גיאוגרפית/אזורית.

### 20_suggested_links_map.png
מפה ארצית של קישורים מוצעים לפי Node2Vec. זה שקף טוב לסיום: מעבר מאבחון פגיעות להצעת שיפור.

## גרפי Zoom למקומות וממצאים שצריך להדגיש

### 21_zoom_lcc_center.png
זום על גוש דן והרכיב הקשיר הגדול. זה הגרף שהייתי שם מיד אחרי המפה הארצית, כדי להראות שהרכיב הגדול לא "כל הארץ" אלא אזור מרכזי וצפוף.

### 22_zoom_tel_aviv_top_degree.png
זום סביב התחנה המרכזית תל אביב ולוינסקי. מדגיש למה תחנות High Degree הן בעיקר תוצר של צפיפות תחנות באותו אזור קטן.

### 23_zoom_betweenness_corridor.png
זום על מסדרון דרום גוש דן שבו נמצאות תחנות High Betweenness. זה חשוב כי הוא מספר סיפור שונה מ-Degree: לא רק צפיפות, אלא תפקיד של מעבר בין חלקים ברכיב.

### 24_zoom_communities_gush_dan.png
זום על קהילות Louvain בגוש דן. מתאים להסביר שהקהילות אינן בהכרח ערים רשמיות אלא אזורים מבניים שנוצרו מהקישוריות.

### 25_zoom_socioeconomic_gush_dan.png
זום על אשכולות סוציו-אקונומיים בגוש דן. זה הגרף שמחבר את הרחבת ה-equity למרחב אמיתי ומראה שונות חברתית בתוך אותו אזור תחבורתי.

### 26_zoom_link_suggestions_gush_dan.png
זום על קישורים מוצעים באזור המרכז. מתאים לשקף הסיום: איפה המודל חושב שחסרים קישורים, ומה אפשר לבדוק תכנונית בהמשך.

## הערת הצגה

לא חייבים להכניס את כל 26 הגרפים למצגת. אם המצגת קצרה, הייתי משתמש ב-01, 02, 04, 06, 07, 10, 12, 14, 15, 16, 20, ובוחר 2-3 גרפי zoom לפי הזמן.
"""
    (OUT_DIR / "README.md").write_text(textwrap.dedent(text), encoding="utf-8")


def main() -> None:
    ensure_output_dir()
    print(f"Writing presentation figures to: {OUT_DIR}")

    graph = load_graph()
    metrics = pd.read_csv(METRICS_CSV, encoding="utf-8-sig")
    metrics["stop_id"] = metrics["stop_id"].astype(str)
    metrics["lat"] = pd.to_numeric(metrics["lat"], errors="coerce")
    metrics["lon"] = pd.to_numeric(metrics["lon"], errors="coerce")

    # plot_graph_model_comparison()  # מבוטל: השווה גרף נסיעות מול גרף קרבה; כעת עובדים רק על גרף הנסיעות
    plot_connectivity_overview()
    plot_component_rank_size(graph)
    plot_lcc_map(graph)
    plot_degree_distribution(metrics)
    plot_centrality_figures(metrics)
    plot_robustness()
    plot_regional()
    plot_communities()
    # plot_socioeconomic()  # מבוטל: דורש הרצת תת-שלב 06/02 (הורדת נתוני למ"ס) על גרף הנסיעות
    plot_link_prediction()
    plot_embeddings(metrics)
    plot_suggested_links_map(graph)
    plot_zoom_lcc_center(graph)
    plot_zoom_top_degree(graph, metrics)
    plot_zoom_betweenness_corridor(graph, metrics)
    plot_zoom_communities()
    # plot_zoom_socioeconomic()  # מבוטל: תלוי בנתוני הסוציו-אקונומי הישנים
    plot_zoom_link_suggestions(graph)
    write_readme()

    generated = sorted(p.name for p in OUT_DIR.glob("*.png"))
    print(f"Generated {len(generated)} PNG figures:")
    for name in generated:
        print(f"  - {name}")


if __name__ == "__main__":
    main()

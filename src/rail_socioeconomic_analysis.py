"""Advanced centrality and socioeconomic analysis for the rail service graph.

This script consumes the rail outputs and the project's existing CBS 2021
socioeconomic spatial join. It does not download or alter source data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import spearmanr

from rail_network_analysis import display_text


CENTRALITY_METRICS = [
    "degree",
    "weighted_degree",
    "pagerank",
    "betweenness",
    "harmonic",
]
DAMAGE_METRIC = "stations_outside_largest_component"
PROFILE_METRICS = CENTRALITY_METRICS + [DAMAGE_METRIC]
PROFILE_LABELS = {
    "degree": "Degree",
    "weighted_degree": "Service volume",
    "pagerank": "PageRank",
    "betweenness": "Betweenness",
    "harmonic": "Harmonic",
    DAMAGE_METRIC: "Single-outage damage",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rail-output-dir", type=Path, default=Path("outputs/rail"))
    parser.add_argument(
        "--socioeconomic-csv",
        type=Path,
        default=Path(
            "public_transport_network_research/06_regional_comparison/outputs/"
            "stops_with_socioeconomic.csv"
        ),
    )
    return parser.parse_args()


def load_analysis_frame(rail_output_dir: Path, socioeconomic_csv: Path) -> pd.DataFrame:
    tables = rail_output_dir / "tables"
    metrics = pd.read_csv(
        tables / "rail_station_metrics.csv", dtype={"stop_id": str}, encoding="utf-8-sig"
    )
    damage = pd.read_csv(
        tables / "single_station_damage.csv",
        dtype={"stop_id": str},
        encoding="utf-8-sig",
    )[["stop_id", DAMAGE_METRIC, "components"]]
    socioeconomic = pd.read_csv(
        socioeconomic_csv, dtype={"stop_id": str}, encoding="utf-8-sig", low_memory=False
    )
    socio_columns = [
        "stop_id",
        "socio_locality",
        "socio_cluster",
        "socio_index_value",
        "socio_population",
        "socio_join_method",
        "socio_join_distance_m",
        "region",
        "metro",
    ]
    frame = metrics.merge(damage, on="stop_id", how="left").merge(
        socioeconomic[socio_columns], on="stop_id", how="left"
    )
    if frame["socio_cluster"].isna().any():
        missing = frame.loc[frame["socio_cluster"].isna(), "stop_name"].tolist()
        raise ValueError(f"Rail stations missing socioeconomic assignments: {missing}")

    frame["socio_group"] = pd.cut(
        frame["socio_cluster"],
        bins=[0, 4, 7, 10],
        labels=["Lower (clusters 2–4)", "Middle (clusters 5–7)", "Higher (clusters 8–9)"],
    )
    for metric in CENTRALITY_METRICS:
        frame[f"{metric}_percentile"] = frame[metric].rank(method="average", pct=True)
    # A zero-damage station should read as zero in the profile rather than inherit
    # the average tied-rank of the many stations that do not fragment the graph.
    frame[f"{DAMAGE_METRIC}_percentile"] = 0.0
    damaging = frame[DAMAGE_METRIC] > 0
    frame.loc[damaging, f"{DAMAGE_METRIC}_percentile"] = frame.loc[
        damaging, DAMAGE_METRIC
    ].rank(method="average", pct=True)
    frame["composite_centrality_score"] = (
        100
        * frame[[f"{metric}_percentile" for metric in CENTRALITY_METRICS]].mean(axis=1)
    )
    frame["top_quintile_centrality_count"] = sum(
        frame[f"{metric}_percentile"].ge(0.8).astype(int)
        for metric in CENTRALITY_METRICS
    )
    frame["station_archetype"] = frame.apply(classify_station, axis=1)
    return frame


def classify_station(row: pd.Series) -> str:
    high_service = (
        row["weighted_degree_percentile"] >= 0.8
        and row["pagerank_percentile"] >= 0.8
    )
    high_brokerage = row["betweenness_percentile"] >= 0.8
    damaging_cut = bool(row["is_articulation_point"]) and row[DAMAGE_METRIC] > 0
    if high_service and damaging_cut:
        return "critical high-service hub"
    if high_service and not damaging_cut:
        return "redundant high-service hub"
    if high_brokerage and damaging_cut:
        return "structural bottleneck"
    if high_brokerage:
        return "structural broker with alternatives"
    if damaging_cut:
        return "branch gateway"
    if row["harmonic_percentile"] >= 0.8:
        return "globally accessible connector"
    return "ordinary or peripheral station"


def correlation_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    samples = {
        "all assignments": frame,
        "within-polygon only": frame[frame["socio_join_method"] == "within"],
    }
    for sample_name, sample in samples.items():
        for socio_variable in ["socio_cluster", "socio_index_value"]:
            for metric in PROFILE_METRICS:
                subset = sample[[socio_variable, metric]].dropna()
                rho, p_value = spearmanr(subset[socio_variable], subset[metric])
                rows.append(
                    {
                        "sample": sample_name,
                        "socioeconomic_variable": socio_variable,
                        "network_metric": metric,
                        "spearman_rho": float(rho),
                        "p_value_two_sided": float(p_value),
                        "n_stations": len(subset),
                    }
                )
    return pd.DataFrame(rows)


def centrality_correlation_table(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[PROFILE_METRICS + ["scheduled_stop_calls"]].corr(method="spearman")


def group_summary(frame: pd.DataFrame) -> pd.DataFrame:
    summary = (
        frame.groupby("socio_group", observed=True)
        .agg(
            stations=("stop_id", "size"),
            within_polygon_share=("socio_join_method", lambda values: (values == "within").mean()),
            median_socio_cluster=("socio_cluster", "median"),
            mean_degree=("degree", "mean"),
            median_weighted_degree=("weighted_degree", "median"),
            mean_scheduled_stop_calls=("scheduled_stop_calls", "mean"),
            median_scheduled_stop_calls=("scheduled_stop_calls", "median"),
            total_scheduled_stop_calls=("scheduled_stop_calls", "sum"),
            mean_pagerank=("pagerank", "mean"),
            mean_betweenness=("betweenness", "mean"),
            median_betweenness=("betweenness", "median"),
            mean_harmonic=("harmonic", "mean"),
            articulation_point_share=("is_articulation_point", "mean"),
            stations_causing_fragmentation=(DAMAGE_METRIC, lambda values: (values > 0).sum()),
            mean_single_station_damage=(DAMAGE_METRIC, "mean"),
        )
        .reset_index()
    )
    summary["scheduled_stop_call_share"] = (
        summary["total_scheduled_stop_calls"]
        / summary["total_scheduled_stop_calls"].sum()
    )
    return summary


def regional_summary(frame: pd.DataFrame) -> pd.DataFrame:
    summary = (
        frame.groupby("region", dropna=False)
        .agg(
            stations=("stop_id", "size"),
            mean_socio_cluster=("socio_cluster", "mean"),
            mean_scheduled_stop_calls=("scheduled_stop_calls", "mean"),
            total_scheduled_stop_calls=("scheduled_stop_calls", "sum"),
            mean_betweenness=("betweenness", "mean"),
            mean_harmonic=("harmonic", "mean"),
            articulation_point_share=("is_articulation_point", "mean"),
            mean_single_station_damage=(DAMAGE_METRIC, "mean"),
        )
        .reset_index()
    )
    return summary.sort_values("mean_betweenness", ascending=False)


def plot_centrality_profiles(frame: pd.DataFrame, path: Path) -> None:
    ranking = frame.sort_values(
        ["top_quintile_centrality_count", "composite_centrality_score"],
        ascending=False,
    ).head(16)
    values = ranking[[f"{metric}_percentile" for metric in PROFILE_METRICS]].copy()
    values.columns = [PROFILE_LABELS[metric] for metric in PROFILE_METRICS]
    values.index = [display_text(name) for name in ranking["stop_name"]]
    fig, axis = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        values,
        annot=True,
        fmt=".0%",
        cmap="viridis",
        vmin=0,
        vmax=1,
        linewidths=0.4,
        cbar_kws={"label": "Percentile among 67 rail stations"},
        ax=axis,
    )
    axis.set_title("Multi-metric profiles of Israel Railways' leading stations")
    axis.set_xlabel("")
    axis.set_ylabel("")
    fig.tight_layout()
    fig.savefig(path, dpi=210)
    plt.close(fig)


def plot_service_vs_damage(frame: pd.DataFrame, path: Path) -> None:
    fig, axis = plt.subplots(figsize=(10, 7))
    sizes = 45 + 650 * frame["betweenness"] / max(frame["betweenness"].max(), 1e-12)
    scatter = axis.scatter(
        frame["scheduled_stop_calls"],
        frame[DAMAGE_METRIC],
        c=frame["socio_cluster"],
        s=sizes,
        cmap="viridis",
        vmin=1,
        vmax=10,
        alpha=0.82,
        edgecolor="white",
        linewidth=0.7,
    )
    labels = frame[
        (frame[DAMAGE_METRIC] >= 3)
        | (frame["scheduled_stop_calls"] >= frame["scheduled_stop_calls"].quantile(0.92))
    ].sort_values(DAMAGE_METRIC, ascending=False)
    offsets = [(-8, 8), (-8, -12), (-6, 9), (6, -12), (-6, 9), (6, 8), (-6, -12), (6, 8)]
    for (_, row), offset in zip(labels.iterrows(), offsets):
        axis.annotate(
            display_text(row["stop_name"]),
            (row["scheduled_stop_calls"], row[DAMAGE_METRIC]),
            xytext=offset,
            textcoords="offset points",
            fontsize=8,
            ha="left" if offset[0] > 0 else "right",
            arrowprops={"arrowstyle": "-", "lw": 0.5, "color": "#64748b"},
        )
    axis.axvline(frame["scheduled_stop_calls"].median(), color="#94a3b8", ls="--", lw=1)
    axis.set_xscale("log")
    axis.set_xlabel("Scheduled stop calls (log scale)")
    axis.set_ylabel("Other stations separated by one modeled outage")
    axis.set_title("Operational busyness versus structural rail vulnerability")
    axis.margins(x=0.09, y=0.12)
    axis.grid(alpha=0.2)
    colorbar = fig.colorbar(scatter, ax=axis)
    colorbar.set_label("Local CBS socioeconomic cluster")
    fig.text(
        0.5,
        0.01,
        "Bubble size represents betweenness centrality; color describes the station's assigned statistical area.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=210)
    plt.close(fig)


def plot_socioeconomic_profiles(frame: pd.DataFrame, path: Path) -> None:
    percentile_columns = [f"{metric}_percentile" for metric in CENTRALITY_METRICS]
    profile = frame.groupby("socio_group", observed=True)[percentile_columns].mean().T
    profile.index = [PROFILE_LABELS[metric] for metric in CENTRALITY_METRICS]
    fig, axis = plt.subplots(figsize=(9, 6))
    markers = ["o", "s", "^"]
    for marker, group in zip(markers, profile.columns):
        axis.plot(
            profile.index,
            100 * profile[group],
            marker=marker,
            linewidth=2,
            markersize=7,
            label=str(group),
        )
    axis.axhline(50, color="#94a3b8", ls="--", lw=1)
    axis.set_ylabel("Mean station percentile")
    axis.set_title("Rail centrality profiles by local socioeconomic group")
    axis.set_ylim(30, 70)
    axis.grid(axis="y", alpha=0.2)
    axis.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=210)
    plt.close(fig)


def plot_regional_profile(summary: pd.DataFrame, path: Path) -> None:
    ordered = summary.sort_values("mean_scheduled_stop_calls", ascending=False)
    labels = [display_text(region) for region in ordered["region"]]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    axes[0].bar(labels, ordered["mean_scheduled_stop_calls"], color="#2563eb")
    axes[0].set_title("Mean scheduled calls per station")
    axes[0].set_ylabel("Scheduled stop calls")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].bar(labels, 100 * ordered["articulation_point_share"], color="#dc2626")
    axes[1].set_title("Stations that are articulation points")
    axes[1].set_ylabel("Share of regional stations (%)")
    axes[1].tick_params(axis="x", rotation=20)
    for axis in axes:
        axis.grid(axis="y", alpha=0.2)
    fig.suptitle("Regional rail service intensity and structural fragility")
    fig.tight_layout()
    fig.savefig(path, dpi=210)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    tables = args.rail_output_dir / "tables"
    figures = args.rail_output_dir / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    frame = load_analysis_frame(args.rail_output_dir, args.socioeconomic_csv)
    correlations = correlation_table(frame)
    centrality_correlations = centrality_correlation_table(frame)
    socioeconomic_groups = group_summary(frame)
    regions = regional_summary(frame)

    frame.sort_values("composite_centrality_score", ascending=False).to_csv(
        tables / "rail_station_archetypes.csv", index=False, encoding="utf-8-sig"
    )
    correlations.to_csv(
        tables / "rail_socioeconomic_correlations.csv", index=False, encoding="utf-8-sig"
    )
    centrality_correlations.to_csv(
        tables / "rail_centrality_spearman.csv", encoding="utf-8-sig"
    )
    socioeconomic_groups.to_csv(
        tables / "rail_socioeconomic_group_summary.csv", index=False, encoding="utf-8-sig"
    )
    regions.to_csv(
        tables / "rail_regional_summary.csv", index=False, encoding="utf-8-sig"
    )

    plot_centrality_profiles(frame, figures / "centrality_profile_heatmap.png")
    plot_service_vs_damage(frame, figures / "service_vs_structural_damage.png")
    plot_socioeconomic_profiles(frame, figures / "socioeconomic_centrality_profiles.png")
    plot_regional_profile(regions, figures / "regional_rail_profile.png")

    strongest = correlations.loc[correlations["spearman_rho"].abs().idxmax()]
    print(
        f"Wrote advanced rail analysis for {len(frame)} stations. "
        f"Socioeconomic joins: {(frame.socio_join_method == 'within').sum()} within, "
        f"{(frame.socio_join_method == 'nearest').sum()} nearest. "
        f"Strongest tested socioeconomic association: "
        f"rho={strongest.spearman_rho:.3f} ({strongest.network_metric}, {strongest['sample']})."
    )


if __name__ == "__main__":
    main()

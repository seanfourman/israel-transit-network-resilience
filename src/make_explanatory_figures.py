"""Create presentation-friendly explanatory figures from final outputs."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


STRATEGY_LABELS = {
    "approx_betweenness": "Stations on many\nshortest routes",
    "articulation_degree": "Stations that\nsplit the network",
    "pagerank": "Flow-ranked\nstations",
    "weighted_degree": "Busiest\nstations",
    "random_mean": "Random\nstations",
    "bridge_frequency": "Segments with no\nbackup path",
    "segment_frequency": "Busiest\nsegments",
    "random_segment_mean": "Random\nsegments",
}


def main() -> None:
    base = Path("outputs/final")
    sensitivity = Path("outputs/sensitivity")
    out = base / "explanatory_figures"
    out.mkdir(parents=True, exist_ok=True)

    metrics = pd.read_csv(base / "tables/station_metrics.csv")
    station_impact = pd.read_csv(base / "tables/single_station_disruption_impact.csv")
    segment_impact = pd.read_csv(base / "tables/single_segment_disruption_impact.csv")
    station_resilience = pd.read_csv(base / "tables/resilience_curve.csv")
    segment_resilience = pd.read_csv(base / "tables/segment_resilience_curve.csv")
    mitigation = pd.read_csv(base / "tables/mitigation_summary.csv")
    radius = pd.read_csv(sensitivity / "radius_sensitivity.csv")
    cutoff = pd.read_csv(sensitivity / "cutoff_sensitivity.csv")

    create_research_flow(out / "01_research_flow.png")
    create_radius_choice(radius, cutoff, out / "02_radius_choice.png")
    create_station_strategy_bars(station_resilience, out / "03_station_removal_strategies.png")
    create_station_vs_segment_comparison(
        station_resilience,
        segment_resilience,
        out / "04_stations_vs_segments.png",
    )
    create_busy_vs_critical(metrics, station_impact, out / "05_busy_vs_critical.png")
    create_critical_station_map(metrics, station_impact, out / "06_critical_station_map.png")
    create_critical_station_zooms(metrics, station_impact, out / "07_critical_station_zooms.png")
    create_top_critical_table(metrics, station_impact, out / "top_critical_stations.csv")
    create_segment_story(segment_resilience, segment_impact, out / "08_segment_story.png")
    create_backup_story(mitigation, out / "09_backup_links_before_after.png")


def create_research_flow(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.axis("off")
    boxes = [
        ("GTFS schedule data", "stops, trips,\nstop_times"),
        ("Build network", "unified stations\n+ trip segments"),
        ("Simulate disruption", "remove stations\nor segments"),
        ("Measure damage", "reachable stations\nwithin 60 min"),
        ("Test backup links", "nearby alternative\nconnections"),
    ]
    x_positions = np.linspace(0.08, 0.92, len(boxes))
    for index, ((title, subtitle), x) in enumerate(zip(boxes, x_positions)):
        ax.text(
            x,
            0.58,
            title + "\n" + subtitle,
            ha="center",
            va="center",
            fontsize=11,
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#eef2ff", edgecolor="#4f46e5"),
        )
        if index < len(boxes) - 1:
            ax.annotate(
                "",
                xy=(x_positions[index + 1] - 0.08, 0.58),
                xytext=(x + 0.08, 0.58),
                arrowprops=dict(arrowstyle="->", color="#334155", lw=1.8),
            )
    ax.set_title("What did we test?", fontsize=16, weight="bold", pad=16)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def create_radius_choice(radius: pd.DataFrame, cutoff: pd.DataFrame, path: Path) -> None:
    cutoff_60 = cutoff[cutoff["cutoff_minutes"] == 60].sort_values("merge_radius_meters")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    axes[0].plot(radius["merge_radius_meters"], radius["station_nodes"], marker="o", color="#2563eb")
    axes[0].set_title("Model choice: merge radius")
    axes[0].set_xlabel("Merge radius (meters)")
    axes[0].set_ylabel("Number of unified stations")
    axes[0].grid(alpha=0.25)

    axes[1].plot(
        cutoff_60["merge_radius_meters"],
        cutoff_60["mean_reachable_share"] * 100,
        marker="o",
        color="#16a34a",
    )
    axes[1].axvline(80, color="#dc2626", linestyle="--", lw=1.4)
    axes[1].text(82, cutoff_60["mean_reachable_share"].max() * 100, "chosen: 80m", color="#dc2626")
    axes[1].set_title("Accessibility stays similar")
    axes[1].set_xlabel("Merge radius (meters)")
    axes[1].set_ylabel("Reachable share within 60 min (%)")
    axes[1].grid(alpha=0.25)
    fig.suptitle("Why we used 80 meters for unified stations", fontsize=15, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def create_station_strategy_bars(resilience: pd.DataFrame, path: Path) -> None:
    end = final_rows(resilience, "removed_stations")
    order = [
        "approx_betweenness",
        "articulation_degree",
        "pagerank",
        "weighted_degree",
        "random_mean",
    ]
    end = end.set_index("strategy").loc[order].reset_index()
    labels = [STRATEGY_LABELS[value] for value in end["strategy"]]
    x = np.arange(len(end))
    width = 0.38

    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.bar(
        x - width / 2,
        end["reachable_share_loss"] * 100,
        width,
        label="Accessibility loss",
        color="#dc2626",
    )
    ax.bar(
        x + width / 2,
        end["largest_component_share_loss"] * 100,
        width,
        label="Connectivity loss",
        color="#2563eb",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Loss after removing 200 stations (%)")
    ax.set_title("Different ways to choose stations produce different damage", weight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    annotate_bars(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def create_station_vs_segment_comparison(
    station_resilience: pd.DataFrame,
    segment_resilience: pd.DataFrame,
    path: Path,
) -> None:
    station_end = final_rows(station_resilience, "removed_stations")
    segment_end = final_rows(segment_resilience, "removed_segments")
    station_best = station_end.loc[station_end["reachable_share_loss"].idxmax()]
    segment_best = segment_end.loc[segment_end["reachable_share_loss"].idxmax()]
    random_station = station_end[station_end["strategy"] == "random_mean"].iloc[0]
    random_segment = segment_end[segment_end["strategy"] == "random_segment_mean"].iloc[0]

    labels = [
        "Worst station\nstrategy",
        "Random\nstations",
        "Worst segment\nstrategy",
        "Random\nsegments",
    ]
    values = [
        station_best["reachable_share_loss"] * 100,
        random_station["reachable_share_loss"] * 100,
        segment_best["reachable_share_loss"] * 100,
        random_segment["reachable_share_loss"] * 100,
    ]
    colors = ["#dc2626", "#fca5a5", "#7c3aed", "#c4b5fd"]

    fig, ax = plt.subplots(figsize=(8.5, 5))
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("Accessibility loss after 200 removals (%)")
    ax.set_title("In this model, station failures matter more than single-segment failures", weight="bold")
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.2f}%", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def create_busy_vs_critical(metrics: pd.DataFrame, impact: pd.DataFrame, path: Path) -> None:
    data = impact.merge(
        metrics[["station_id", "station_lat", "station_lon"]],
        on="station_id",
        how="left",
    ).copy()
    data = data.dropna(subset=["weighted_degree", "reachable_share_loss"])
    top = data.head(8)

    fig, ax = plt.subplots(figsize=(8.8, 5.8))
    ax.scatter(
        data["weighted_degree"],
        data["reachable_share_loss"] * 100,
        s=34,
        alpha=0.45,
        color="#64748b",
        label="tested stations",
    )
    ax.scatter(
        top["weighted_degree"],
        top["reachable_share_loss"] * 100,
        s=90,
        color="#dc2626",
        label="largest damage",
    )
    for rank, row in enumerate(top.itertuples(index=False), start=1):
        ax.annotate(str(rank), (row.weighted_degree, row.reachable_share_loss * 100), xytext=(4, 4), textcoords="offset points")
    ax.set_xscale("log")
    ax.set_xlabel("How busy is the station? Weighted degree, log scale")
    ax.set_ylabel("Accessibility loss if this station is removed (%)")
    ax.set_title("Busy station does not always mean critical station", weight="bold")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def create_critical_station_map(metrics: pd.DataFrame, impact: pd.DataFrame, path: Path) -> None:
    data = impact.merge(
        metrics[["station_id", "station_lat", "station_lon"]],
        on="station_id",
        how="left",
    ).dropna(subset=["station_lat", "station_lon"])
    top = data.head(10)

    fig, ax = plt.subplots(figsize=(6.5, 8.5))
    ax.scatter(metrics["station_lon"], metrics["station_lat"], s=2, color="#cbd5e1", alpha=0.45)
    ax.scatter(top["station_lon"], top["station_lat"], s=95, color="#dc2626", edgecolor="white", linewidth=0.8)
    for rank, row in enumerate(top.itertuples(index=False), start=1):
        ax.annotate(str(rank), (row.station_lon, row.station_lat), ha="center", va="center", color="white", fontsize=8, weight="bold")
    ax.set_xlim(34.2, 35.9)
    ax.set_ylim(29.4, 33.4)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Where are the most damaging single-station failures?", weight="bold")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def create_critical_station_zooms(metrics: pd.DataFrame, impact: pd.DataFrame, path: Path) -> None:
    data = impact.merge(
        metrics[["station_id", "station_lat", "station_lon"]],
        on="station_id",
        how="left",
    ).dropna(subset=["station_lat", "station_lon"])
    top = data.head(4)
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    axes = axes.ravel()
    for rank, (ax, row) in enumerate(zip(axes, top.itertuples(index=False)), start=1):
        lat = row.station_lat
        lon = row.station_lon
        nearby = metrics[
            metrics["station_lat"].between(lat - 0.04, lat + 0.04)
            & metrics["station_lon"].between(lon - 0.04, lon + 0.04)
        ]
        ax.scatter(nearby["station_lon"], nearby["station_lat"], s=12, color="#cbd5e1", alpha=0.8)
        ax.scatter([lon], [lat], s=150, color="#dc2626", edgecolor="white", linewidth=1.0)
        ax.annotate(str(rank), (lon, lat), ha="center", va="center", color="white", weight="bold")
        ax.set_title(f"#{rank}: station {row.station_id}\nloss {row.reachable_share_loss * 100:.2f}%")
        ax.set_xlim(lon - 0.04, lon + 0.04)
        ax.set_ylim(lat - 0.04, lat + 0.04)
        ax.grid(alpha=0.2)
    fig.suptitle("Zoom-in around the top damaging stations", fontsize=15, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def create_top_critical_table(metrics: pd.DataFrame, impact: pd.DataFrame, path: Path) -> None:
    data = impact.merge(
        metrics[["station_id", "station_lat", "station_lon", "stop_count"]],
        on="station_id",
        how="left",
    )
    table = data.head(10)[
        [
            "station_id",
            "station_name",
            "reachable_share_loss",
            "largest_component_share_loss",
            "weighted_degree",
            "pagerank",
            "approx_betweenness",
            "is_articulation_point",
            "station_lat",
            "station_lon",
            "stop_count",
        ]
    ].copy()
    table.insert(0, "rank", range(1, len(table) + 1))
    table["reachable_share_loss_percent"] = table["reachable_share_loss"] * 100
    table["largest_component_share_loss_percent"] = table["largest_component_share_loss"] * 100
    table.to_csv(path, index=False, encoding="utf-8-sig")


def create_segment_story(segment_resilience: pd.DataFrame, segment_impact: pd.DataFrame, path: Path) -> None:
    end = final_rows(segment_resilience, "removed_segments")
    order = ["bridge_frequency", "segment_frequency", "random_segment_mean"]
    end = end.set_index("strategy").loc[order].reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    axes[0].bar(
        [STRATEGY_LABELS[value] for value in end["strategy"]],
        end["reachable_share_loss"] * 100,
        color=["#7c3aed", "#a78bfa", "#ddd6fe"],
    )
    axes[0].set_title("Removing 200 segments")
    axes[0].set_ylabel("Accessibility loss (%)")
    axes[0].grid(axis="y", alpha=0.25)
    annotate_bars(axes[0])

    top = segment_impact.head(8).iloc[::-1]
    labels = [f"{row.source_station_id}-{row.target_station_id}" for row in top.itertuples(index=False)]
    axes[1].barh(labels, top["reachable_share_loss"] * 100, color="#9333ea")
    axes[1].set_title("Worst single segments")
    axes[1].set_xlabel("Accessibility loss (%)")
    axes[1].grid(axis="x", alpha=0.25)
    fig.suptitle("Segments matter locally, but less than station failures", fontsize=15, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def create_backup_story(mitigation: pd.DataFrame, path: Path) -> None:
    before = mitigation[mitigation["scenario"] == "before_backup_links"].iloc[0]
    after = mitigation[mitigation["scenario"] == "after_backup_links"].iloc[0]
    labels = ["Connected\ncomponents", "Largest component\nshare (%)", "Reachable\nshare (%)"]
    before_values = [
        before["connected_components"],
        before["largest_component_share"] * 100,
        before["mean_reachable_share"] * 100,
    ]
    after_values = [
        after["connected_components"],
        after["largest_component_share"] * 100,
        after["mean_reachable_share"] * 100,
    ]

    fig, axes = plt.subplots(1, 3, figsize=(11, 4))
    for ax, label, before_value, after_value in zip(axes, labels, before_values, after_values):
        ax.bar(["before", "after"], [before_value, after_value], color=["#f97316", "#16a34a"])
        ax.set_title(label)
        ax.grid(axis="y", alpha=0.25)
        for index, value in enumerate([before_value, after_value]):
            ax.text(index, value, f"{value:.2f}", ha="center", va="bottom", fontsize=9)
    fig.suptitle("Backup links reconnect pieces, but average accessibility changes only a little", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def final_rows(df: pd.DataFrame, removed_column: str) -> pd.DataFrame:
    idx = df.groupby("strategy")[removed_column].idxmax()
    return df.loc[idx].copy()


def annotate_bars(ax) -> None:
    for patch in ax.patches:
        height = patch.get_height()
        if height <= 0:
            continue
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            height,
            f"{height:.2f}%",
            ha="center",
            va="bottom",
            fontsize=8,
        )


if __name__ == "__main__":
    main()

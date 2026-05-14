"""Run lightweight sensitivity experiments for the transit resilience project."""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from transit_resilience_analysis import (
    accessibility_snapshot,
    attach_station_attributes,
    build_station_graphs,
    build_unified_station_mapping,
    make_station_table,
    network_summary,
    read_csv_frame,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run radius and accessibility-cutoff sensitivity experiments."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("israel-public-transportation"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/sensitivity"))
    parser.add_argument("--radii-meters", type=float, nargs="+", default=[50.0, 80.0, 120.0])
    parser.add_argument("--cutoffs-minutes", type=float, nargs="+", default=[30.0, 60.0, 90.0])
    parser.add_argument("--accessibility-sample", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def sample_origins(graph: nx.Graph, sample_size: int, seed: int) -> list[str]:
    if graph.number_of_nodes() == 0:
        return []
    largest = list(max(nx.connected_components(graph), key=len))
    rng = random.Random(seed)
    rng.shuffle(largest)
    return largest[: min(sample_size, len(largest))]


def print_runtime(message: str, started: float) -> None:
    elapsed = time.perf_counter() - started
    print(f"[{elapsed:7.1f}s] {message}", flush=True)


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print_runtime("Loading stops metadata", started)
    stops = read_csv_frame(args.data_dir / "stops.txt")

    radius_rows = []
    cutoff_rows = []

    for radius in args.radii_meters:
        print_runtime(f"Building graph for merge radius {radius:g}m", started)
        station_by_stop = build_unified_station_mapping(stops, radius)
        directed, undirected, stop_use_counts, station_use_counts, build_stats = build_station_graphs(
            args.data_dir,
            station_by_stop,
        )
        station_table = make_station_table(stops, station_by_stop, stop_use_counts, station_use_counts)
        station_table = station_table[station_table["station_id"].isin(undirected.nodes)].copy()
        attach_station_attributes(directed, station_table)
        attach_station_attributes(undirected, station_table)

        summary = network_summary(directed, undirected)
        radius_rows.append(
            {
                "merge_radius_meters": radius,
                **build_stats.__dict__,
                **summary,
            }
        )

        origins = sample_origins(undirected, args.accessibility_sample, args.seed)
        for cutoff_minutes in args.cutoffs_minutes:
            snapshot = accessibility_snapshot(
                undirected,
                origins,
                cutoff_minutes * 60,
                reference_node_count=undirected.number_of_nodes(),
            )
            cutoff_rows.append(
                {
                    "merge_radius_meters": radius,
                    "cutoff_minutes": cutoff_minutes,
                    **snapshot,
                }
            )

    radius_df = pd.DataFrame(radius_rows)
    cutoff_df = pd.DataFrame(cutoff_rows)
    radius_df.to_csv(args.output_dir / "radius_sensitivity.csv", index=False, encoding="utf-8-sig")
    cutoff_df.to_csv(args.output_dir / "cutoff_sensitivity.csv", index=False, encoding="utf-8-sig")

    with (args.output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "radii_meters": args.radii_meters,
                "cutoffs_minutes": args.cutoffs_minutes,
                "accessibility_sample": args.accessibility_sample,
                "seed": args.seed,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )

    write_figures(args.output_dir, radius_df, cutoff_df)
    print_runtime("Done", started)
    print(f"Tables and figures: {args.output_dir}")


def write_figures(output_dir: Path, radius_df: pd.DataFrame, cutoff_df: pd.DataFrame) -> None:
    plt.figure(figsize=(7, 5))
    plt.plot(radius_df["merge_radius_meters"], radius_df["station_nodes"], marker="o")
    plt.xlabel("Merge radius (meters)")
    plt.ylabel("Unified stations")
    plt.title("Unified Station Count by Merge Radius")
    plt.tight_layout()
    plt.savefig(output_dir / "radius_station_count.png", dpi=180)
    plt.close()

    plt.figure(figsize=(7, 5))
    for radius, group in cutoff_df.groupby("merge_radius_meters"):
        group = group.sort_values("cutoff_minutes")
        plt.plot(
            group["cutoff_minutes"],
            group["mean_reachable_share"],
            marker="o",
            label=f"{radius:g}m",
        )
    plt.xlabel("Accessibility cutoff (minutes)")
    plt.ylabel("Mean reachable share")
    plt.title("Accessibility by Time Cutoff and Merge Radius")
    plt.ylim(0, 1.02)
    plt.legend(title="Radius")
    plt.tight_layout()
    plt.savefig(output_dir / "cutoff_accessibility.png", dpi=180)
    plt.close()


if __name__ == "__main__":
    main()

"""Rail-only resilience analysis for the Israel Ministry of Transport GTFS feed.

The graph definition deliberately matches the repository's primary analysis:

* node: an active Israel Railways stop (GTFS route_type=2)
* directed edge: consecutive stops in a scheduled train trip
* edge weight: number of scheduled trips using that stop-to-stop link

This is a scheduled-service graph, not a physical track-infrastructure graph.
Express services can therefore create edges between non-adjacent physical stations.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns

try:
    from bidi.algorithm import get_display
except ImportError:  # Figures remain usable; Hebrew text may render left-to-right.
    get_display = lambda value: value


RAIL_ROUTE_TYPE = "2"
DEFAULT_SEED = 42


@dataclass(frozen=True)
class RailBuildSummary:
    source_stop_time_rows: int
    rail_stop_time_rows: int
    rail_route_records: int
    unique_route_descriptions: int
    scheduled_rail_trips: int
    active_rail_stations: int
    directed_service_edges: int
    undirected_service_edges: int
    service_start_date: str
    service_end_date: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir", type=Path, default=Path("israel-public-transportation")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/rail"))
    parser.add_argument("--random-trials", type=int, default=500)
    parser.add_argument("--max-removals", type=int, default=15)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def display_text(value: object) -> str:
    return get_display(str(value))


def read_gtfs(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size < 100:
        raise FileNotFoundError(f"Missing or unhydrated GTFS file: {path}")
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig")


def route_type_label(route_type: str) -> str:
    return {
        "0": "tram/light rail",
        "2": "rail",
        "3": "bus",
        "5": "cable tram",
        "8": "trolleybus/taxi-coded",
        "715": "demand/other bus",
    }.get(str(route_type), "other")


def mode_inventory(routes: pd.DataFrame, trips: pd.DataFrame) -> pd.DataFrame:
    route_counts = routes.groupby("route_type").size().rename("route_records")
    trip_counts = (
        trips.merge(routes[["route_id", "route_type"]], on="route_id", how="left")
        .groupby("route_type")
        .size()
        .rename("scheduled_trips")
    )
    inventory = pd.concat([route_counts, trip_counts], axis=1).fillna(0).reset_index()
    inventory["route_type_label"] = inventory["route_type"].map(route_type_label)
    inventory["route_records"] = inventory["route_records"].astype(int)
    inventory["scheduled_trips"] = inventory["scheduled_trips"].astype(int)
    return inventory[["route_type", "route_type_label", "route_records", "scheduled_trips"]]


def service_date_range(
    rail_trips: pd.DataFrame, calendar: pd.DataFrame
) -> tuple[str, str]:
    relevant = calendar[calendar["service_id"].isin(rail_trips["service_id"])]
    if relevant.empty:
        return "", ""

    def iso_date(raw: str) -> str:
        raw = str(raw)
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}" if len(raw) == 8 else raw

    return iso_date(relevant["start_date"].min()), iso_date(relevant["end_date"].max())


def collect_rail_stop_times(
    stop_times_path: Path, rail_trip_ids: set[str]
) -> tuple[dict[str, list[tuple[int, str]]], Counter[str], int, int]:
    """Stream the national file but retain only the small rail subset."""
    sequences: dict[str, list[tuple[int, str]]] = defaultdict(list)
    stop_use_counts: Counter[str] = Counter()
    all_rows = 0
    rail_rows = 0
    with stop_times_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"trip_id", "stop_id", "stop_sequence"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"stop_times.txt is missing fields: {sorted(required)}")
        for row in reader:
            all_rows += 1
            trip_id = row["trip_id"]
            if trip_id not in rail_trip_ids:
                continue
            rail_rows += 1
            stop_id = row["stop_id"]
            try:
                sequence = int(float(row["stop_sequence"]))
            except ValueError:
                continue
            sequences[trip_id].append((sequence, stop_id))
            stop_use_counts[stop_id] += 1
    return sequences, stop_use_counts, all_rows, rail_rows


def build_graphs(
    sequences: dict[str, list[tuple[int, str]]]
) -> tuple[nx.DiGraph, nx.Graph]:
    edge_counts: Counter[tuple[str, str]] = Counter()
    nodes: set[str] = set()
    for trip_sequence in sequences.values():
        ordered = [stop for _, stop in sorted(trip_sequence)]
        nodes.update(ordered)
        for source, target in zip(ordered, ordered[1:]):
            if source != target:
                edge_counts[(source, target)] += 1

    directed = nx.DiGraph()
    directed.add_nodes_from(nodes)
    for (source, target), weight in edge_counts.items():
        directed.add_edge(source, target, weight=int(weight))

    undirected = nx.Graph()
    undirected.add_nodes_from(nodes)
    for source, target, data in directed.edges(data=True):
        weight = int(data["weight"])
        if undirected.has_edge(source, target):
            undirected[source][target]["weight"] += weight
        else:
            undirected.add_edge(source, target, weight=weight)
    return directed, undirected


def attach_stop_metadata(
    directed: nx.DiGraph, undirected: nx.Graph, stops: pd.DataFrame
) -> pd.DataFrame:
    active = stops[stops["stop_id"].isin(undirected.nodes)].copy()
    active["stop_lat"] = pd.to_numeric(active["stop_lat"], errors="coerce")
    active["stop_lon"] = pd.to_numeric(active["stop_lon"], errors="coerce")
    active = active.set_index("stop_id", drop=False)
    for stop_id in undirected.nodes:
        if stop_id not in active.index:
            continue
        row = active.loc[stop_id]
        attributes = {
            "stop_name": row.get("stop_name", ""),
            "stop_code": row.get("stop_code", ""),
            "lat": float(row["stop_lat"]),
            "lon": float(row["stop_lon"]),
        }
        directed.nodes[stop_id].update(attributes)
        undirected.nodes[stop_id].update(attributes)
    return active.reset_index(drop=True)


def compute_metrics(
    directed: nx.DiGraph,
    undirected: nx.Graph,
    stop_use_counts: Counter[str],
    active_stops: pd.DataFrame,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    degree = dict(undirected.degree())
    weighted_degree = dict(undirected.degree(weight="weight"))
    pagerank = nx.pagerank(directed, weight="weight")
    betweenness = nx.betweenness_centrality(undirected, normalized=True, weight=None)
    harmonic_raw = nx.harmonic_centrality(undirected)
    harmonic_denominator = max(1, undirected.number_of_nodes() - 1)
    harmonic = {node: value / harmonic_denominator for node, value in harmonic_raw.items()}
    articulation = set(nx.articulation_points(undirected))
    bridges = set(nx.bridges(undirected))

    communities = nx.community.louvain_communities(
        undirected, weight="weight", seed=seed
    )
    community_by_node: dict[str, int] = {}
    for community_id, members in enumerate(
        sorted(communities, key=len, reverse=True), start=1
    ):
        for node in members:
            community_by_node[node] = community_id

    metadata = active_stops.set_index("stop_id")
    rows = []
    for node in undirected.nodes:
        row = metadata.loc[node]
        rows.append(
            {
                "stop_id": node,
                "stop_code": row.get("stop_code", ""),
                "stop_name": row.get("stop_name", ""),
                "stop_lat": float(row["stop_lat"]),
                "stop_lon": float(row["stop_lon"]),
                "scheduled_stop_calls": int(stop_use_counts[node]),
                "degree": int(degree[node]),
                "weighted_degree": int(weighted_degree[node]),
                "in_degree": int(directed.in_degree(node)),
                "out_degree": int(directed.out_degree(node)),
                "pagerank": float(pagerank[node]),
                "betweenness": float(betweenness[node]),
                "harmonic": float(harmonic[node]),
                "is_articulation_point": node in articulation,
                "community_id": int(community_by_node[node]),
            }
        )
    metrics = pd.DataFrame(rows)

    bridge_rows = []
    names = metrics.set_index("stop_id")["stop_name"].to_dict()
    for source, target in sorted(bridges):
        bridge_rows.append(
            {
                "from_stop_id": source,
                "from_stop_name": names[source],
                "to_stop_id": target,
                "to_stop_name": names[target],
                "scheduled_trip_segments": int(undirected[source][target]["weight"]),
            }
        )
    return metrics, pd.DataFrame(bridge_rows)


def graph_state(graph: nx.Graph, removed: Iterable[str]) -> dict[str, float | int]:
    remaining = set(graph.nodes).difference(removed)
    original_nodes = graph.number_of_nodes()
    if not remaining:
        return {
            "remaining_stations": 0,
            "components": 0,
            "largest_component_nodes": 0,
            "largest_component_share_of_remaining": 0.0,
            "serviceable_share_of_original": 0.0,
        }
    subgraph = graph.subgraph(remaining)
    component_sizes = [len(component) for component in nx.connected_components(subgraph)]
    largest = max(component_sizes)
    return {
        "remaining_stations": len(remaining),
        "components": len(component_sizes),
        "largest_component_nodes": largest,
        "largest_component_share_of_remaining": largest / len(remaining),
        "serviceable_share_of_original": largest / original_nodes,
    }


def single_station_damage(graph: nx.Graph, metrics: pd.DataFrame) -> pd.DataFrame:
    names = metrics.set_index("stop_id")["stop_name"].to_dict()
    rows = []
    for node in graph.nodes:
        state = graph_state(graph, [node])
        rows.append(
            {
                "stop_id": node,
                "stop_name": names[node],
                **state,
                "stations_outside_largest_component": int(
                    state["remaining_stations"] - state["largest_component_nodes"]
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["stations_outside_largest_component", "components", "stop_name"],
        ascending=[False, False, True],
    )


def resilience_curves(
    graph: nx.Graph,
    metrics: pd.DataFrame,
    damage: pd.DataFrame,
    max_removals: int,
    random_trials: int,
    seed: int,
) -> pd.DataFrame:
    damage_rank = damage.set_index("stop_id")["stations_outside_largest_component"]
    ranked = metrics.copy()
    ranked["single_station_damage"] = ranked["stop_id"].map(damage_rank)
    rankings = {
        "degree": ranked.sort_values(
            ["degree", "weighted_degree"], ascending=False
        )["stop_id"].tolist(),
        "weighted_degree": ranked.sort_values("weighted_degree", ascending=False)[
            "stop_id"
        ].tolist(),
        "pagerank": ranked.sort_values("pagerank", ascending=False)["stop_id"].tolist(),
        "betweenness": ranked.sort_values("betweenness", ascending=False)[
            "stop_id"
        ].tolist(),
        "articulation_priority": ranked.sort_values(
            ["is_articulation_point", "single_station_damage", "degree"],
            ascending=False,
        )["stop_id"].tolist(),
    }
    max_removals = min(max_removals, graph.number_of_nodes() - 1)
    rows = []
    for strategy, ranking in rankings.items():
        for removed_count in range(max_removals + 1):
            rows.append(
                {
                    "strategy": strategy,
                    "removed_stations": removed_count,
                    **graph_state(graph, ranking[:removed_count]),
                }
            )

    rng = random.Random(seed)
    nodes = list(graph.nodes)
    random_states: dict[int, list[dict[str, float | int]]] = defaultdict(list)
    for _ in range(random_trials):
        ordering = rng.sample(nodes, len(nodes))
        for removed_count in range(max_removals + 1):
            random_states[removed_count].append(
                graph_state(graph, ordering[:removed_count])
            )
    for removed_count, states in random_states.items():
        row: dict[str, object] = {
            "strategy": "random_mean",
            "removed_stations": removed_count,
        }
        for field in states[0]:
            row[field] = float(np.mean([float(state[field]) for state in states]))
        rows.append(row)
    return pd.DataFrame(rows)


def network_summary(
    graph: nx.Graph,
    directed: nx.DiGraph,
    metrics: pd.DataFrame,
    communities: int,
) -> dict[str, float | int]:
    components = list(nx.connected_components(graph))
    largest = graph.subgraph(max(components, key=len)).copy()
    return {
        "active_stations": graph.number_of_nodes(),
        "directed_service_edges": directed.number_of_edges(),
        "undirected_service_edges": graph.number_of_edges(),
        "connected_components": len(components),
        "largest_component_stations": largest.number_of_nodes(),
        "largest_component_share": largest.number_of_nodes() / graph.number_of_nodes(),
        "average_degree": sum(dict(graph.degree()).values()) / graph.number_of_nodes(),
        "density": nx.density(graph),
        "average_clustering": nx.average_clustering(graph),
        "average_shortest_path_hops_lcc": nx.average_shortest_path_length(largest),
        "diameter_hops_lcc": nx.diameter(largest),
        "articulation_points": int(metrics["is_articulation_point"].sum()),
        "bridges": int(sum(1 for _ in nx.bridges(graph))),
        "louvain_communities": communities,
    }


def write_tables(
    output_dir: Path,
    inventory: pd.DataFrame,
    metrics: pd.DataFrame,
    bridges: pd.DataFrame,
    damage: pd.DataFrame,
    resilience: pd.DataFrame,
    directed: nx.DiGraph,
) -> None:
    tables = output_dir / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(tables / "mode_inventory.csv", index=False, encoding="utf-8-sig")
    metrics.sort_values("betweenness", ascending=False).to_csv(
        tables / "rail_station_metrics.csv", index=False, encoding="utf-8-sig"
    )
    metrics.nlargest(15, "betweenness").to_csv(
        tables / "top_betweenness_stations.csv", index=False, encoding="utf-8-sig"
    )
    metrics.nlargest(15, "weighted_degree").to_csv(
        tables / "top_weighted_degree_stations.csv", index=False, encoding="utf-8-sig"
    )
    bridges.to_csv(tables / "rail_bridges.csv", index=False, encoding="utf-8-sig")
    damage.to_csv(
        tables / "single_station_damage.csv", index=False, encoding="utf-8-sig"
    )
    resilience.to_csv(
        tables / "rail_resilience_curves.csv", index=False, encoding="utf-8-sig"
    )
    edge_rows = []
    for source, target, data in directed.edges(data=True):
        edge_rows.append(
            {
                "from_stop_id": source,
                "to_stop_id": target,
                "scheduled_trip_segments": int(data["weight"]),
            }
        )
    pd.DataFrame(edge_rows).sort_values(
        "scheduled_trip_segments", ascending=False
    ).to_csv(tables / "rail_service_edges.csv", index=False, encoding="utf-8-sig")


def plot_network_map(graph: nx.Graph, metrics: pd.DataFrame, path: Path) -> None:
    indexed = metrics.set_index("stop_id")
    positions = {
        node: (float(indexed.loc[node, "stop_lon"]), float(indexed.loc[node, "stop_lat"]))
        for node in graph.nodes
    }
    segments = [[positions[source], positions[target]] for source, target in graph.edges]
    fig, axis = plt.subplots(figsize=(8, 10))
    axis.add_collection(LineCollection(segments, colors="#94a3b8", linewidths=0.8, alpha=0.5))
    values = indexed.loc[list(graph.nodes), "betweenness"].to_numpy(float)
    weights = indexed.loc[list(graph.nodes), "weighted_degree"].to_numpy(float)
    sizes = 22 + 180 * np.sqrt(weights / max(weights.max(), 1))
    scatter = axis.scatter(
        [positions[node][0] for node in graph.nodes],
        [positions[node][1] for node in graph.nodes],
        c=values,
        s=sizes,
        cmap="magma_r",
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    label_offsets = [(8, 12), (8, -13), (-8, 12), (8, -13), (-8, 12), (8, -13), (8, 12)]
    for node, offset in zip(indexed.nlargest(7, "betweenness").index, label_offsets):
        x_pos, y_pos = positions[node]
        axis.annotate(
            display_text(indexed.loc[node, "stop_name"]),
            (x_pos, y_pos),
            xytext=offset,
            textcoords="offset points",
            fontsize=7,
            ha="left" if offset[0] > 0 else "right",
            arrowprops={"arrowstyle": "-", "color": "#64748b", "lw": 0.5},
        )
    fig.colorbar(scatter, ax=axis, label="Betweenness centrality")
    axis.set_title("Israel Railways scheduled-service network")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")
    axis.autoscale()
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)


def plot_top_stations(metrics: pd.DataFrame, path: Path) -> None:
    top = metrics.nlargest(12, "betweenness").sort_values("betweenness")
    fig, axis = plt.subplots(figsize=(9, 6))
    axis.barh(
        [display_text(name) for name in top["stop_name"]],
        top["betweenness"],
        color="#2563eb",
    )
    axis.set_xlabel("Betweenness centrality")
    axis.set_title("Rail stations most often bridging shortest service paths")
    axis.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_single_station_damage(damage: pd.DataFrame, path: Path) -> None:
    top = damage[damage["stations_outside_largest_component"] > 0].head(15)
    top = top.sort_values("stations_outside_largest_component")
    fig, axis = plt.subplots(figsize=(9, 6))
    axis.barh(
        [display_text(name) for name in top["stop_name"]],
        top["stations_outside_largest_component"],
        color="#dc2626",
    )
    axis.set_xlabel("Other stations separated from the largest component")
    axis.set_title("Damage caused by closing one rail station")
    axis.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_resilience(resilience: pd.DataFrame, path: Path) -> None:
    colors = {
        "degree": "#0f766e",
        "weighted_degree": "#2563eb",
        "pagerank": "#7c3aed",
        "betweenness": "#dc2626",
        "articulation_priority": "#ea580c",
        "random_mean": "#64748b",
    }
    fig, axis = plt.subplots(figsize=(9, 6))
    for strategy, group in resilience.groupby("strategy", sort=False):
        axis.plot(
            group["removed_stations"],
            100 * group["serviceable_share_of_original"],
            marker="o" if strategy != "random_mean" else None,
            markersize=3,
            linewidth=2,
            linestyle="--" if strategy == "random_mean" else "-",
            color=colors.get(strategy),
            label=strategy.replace("_", " "),
        )
    axis.set_xlabel("Stations removed")
    axis.set_ylabel("Largest connected component (% of original stations)")
    axis.set_title("Rail-network resilience: targeted closures vs random failures")
    axis.set_ylim(0, 102)
    axis.grid(alpha=0.2)
    axis.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_centrality_correlation(metrics: pd.DataFrame, path: Path) -> None:
    columns = ["degree", "weighted_degree", "pagerank", "betweenness", "harmonic"]
    correlation = metrics[columns].corr(method="spearman")
    fig, axis = plt.subplots(figsize=(7, 6))
    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="vlag",
        vmin=-1,
        vmax=1,
        square=True,
        ax=axis,
    )
    axis.set_title("Spearman correlation between rail centrality metrics")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    figures = args.output_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    print("Loading GTFS metadata", flush=True)
    routes = read_gtfs(args.data_dir / "routes.txt")
    trips = read_gtfs(args.data_dir / "trips.txt")
    stops = read_gtfs(args.data_dir / "stops.txt")
    calendar = read_gtfs(args.data_dir / "calendar.txt")
    inventory = mode_inventory(routes, trips)

    rail_routes = routes[routes["route_type"] == RAIL_ROUTE_TYPE].copy()
    rail_trips = trips[trips["route_id"].isin(rail_routes["route_id"])].copy()
    if rail_routes.empty or rail_trips.empty:
        raise RuntimeError("The GTFS feed contains no route_type=2 rail service")
    start_date, end_date = service_date_range(rail_trips, calendar)

    print("Streaming rail rows from stop_times.txt", flush=True)
    sequences, stop_calls, source_rows, rail_rows = collect_rail_stop_times(
        args.data_dir / "stop_times.txt", set(rail_trips["trip_id"])
    )
    directed, undirected = build_graphs(sequences)
    active_stops = attach_stop_metadata(directed, undirected, stops)

    print("Computing exact rail centrality and resilience metrics", flush=True)
    metrics, bridges = compute_metrics(
        directed, undirected, stop_calls, active_stops, args.seed
    )
    damage = single_station_damage(undirected, metrics)
    resilience = resilience_curves(
        undirected,
        metrics,
        damage,
        args.max_removals,
        args.random_trials,
        args.seed,
    )
    communities = metrics["community_id"].nunique()
    summary = network_summary(undirected, directed, metrics, communities)
    build_summary = RailBuildSummary(
        source_stop_time_rows=source_rows,
        rail_stop_time_rows=rail_rows,
        rail_route_records=len(rail_routes),
        unique_route_descriptions=rail_routes["route_long_name"].nunique(),
        scheduled_rail_trips=len(rail_trips),
        active_rail_stations=undirected.number_of_nodes(),
        directed_service_edges=directed.number_of_edges(),
        undirected_service_edges=undirected.number_of_edges(),
        service_start_date=start_date,
        service_end_date=end_date,
    )

    write_tables(
        args.output_dir, inventory, metrics, bridges, damage, resilience, directed
    )
    with (args.output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {"build": asdict(build_summary), "network": summary},
            handle,
            ensure_ascii=False,
            indent=2,
        )

    plot_network_map(undirected, metrics, figures / "rail_network_map.png")
    plot_top_stations(metrics, figures / "top_betweenness_stations.png")
    plot_single_station_damage(damage, figures / "single_station_damage.png")
    plot_resilience(resilience, figures / "rail_resilience_curve.png")
    plot_centrality_correlation(metrics, figures / "centrality_correlation.png")

    elapsed = time.perf_counter() - started
    print(
        f"Done in {elapsed:.1f}s: {undirected.number_of_nodes()} stations, "
        f"{directed.number_of_edges()} directed service edges. Outputs: {args.output_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()

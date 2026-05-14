"""Accessibility and resilience analysis for Israel public-transport GTFS data.

This script builds a unified-station graph from GTFS stop sequences, compares
centrality rankings with measured disruption impact, and recommends simple
geographic backup links after targeted disruptions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd


ROUTE_TYPE_LABELS = {
    "0": "tram/light rail",
    "1": "subway",
    "2": "rail",
    "3": "bus",
    "4": "ferry",
    "5": "cable tram",
    "6": "aerial lift",
    "7": "funicular",
    "8": "trolleybus",
    "715": "demand/other bus",
}


@dataclass(frozen=True)
class GraphBuildStats:
    stop_times_rows: int
    active_stops: int
    station_nodes: int
    active_trips: int
    directed_edges: int
    undirected_edges: int
    skipped_same_station_segments: int
    non_contiguous_trip_rows: int
    out_of_order_stop_sequences: int
    min_stops_per_trip: int
    mean_stops_per_trip: float
    max_stops_per_trip: int
    timed_edge_observations: int
    fallback_impedance_seconds: float


class UnionFind:
    def __init__(self, values: Iterable[str]) -> None:
        self.parent = {value: value for value in values}
        self.rank = {value: 0 for value in values}

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        if self.rank[root_left] == self.rank[root_right]:
            self.rank[root_left] += 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze accessibility resilience in Israel public transport GTFS data."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("israel-public-transportation"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--merge-radius-meters", type=float, default=80.0)
    parser.add_argument("--betweenness-samples", type=int, default=64)
    parser.add_argument("--accessibility-sample", type=int, default=64)
    parser.add_argument("--accessibility-cutoff-minutes", type=float, default=60.0)
    parser.add_argument("--resilience-removals", type=int, default=250)
    parser.add_argument("--resilience-steps", type=int, default=12)
    parser.add_argument("--random-trials", type=int, default=3)
    parser.add_argument("--single-disruption-candidates", type=int, default=80)
    parser.add_argument("--single-segment-candidates", type=int, default=80)
    parser.add_argument("--mitigation-removals", type=int, default=10)
    parser.add_argument("--backup-links", type=int, default=10)
    parser.add_argument("--backup-link-distance-meters", type=float, default=500.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--write-graph", action="store_true")
    return parser.parse_args()


def require_real_file(path: Path) -> None:
    if not path.exists():
        message = f"Missing required file: {path}"
        if path.name in {"stop_times.txt", "shapes.txt"}:
            message += (
                "\nThis repository stores the large GTFS files through Git LFS history. "
                f"Restore the pointer first, for example:\n"
                f"  git checkout 733a885 -- {path.as_posix()}\n"
                f"  git lfs pull --include=\"{path.as_posix()}\""
            )
        raise FileNotFoundError(message)
    with path.open("rb") as handle:
        prefix = handle.read(80)
    if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise RuntimeError(
            f"{path} is still a Git LFS pointer. Run:\n"
            f"  git lfs pull --include=\"{path.as_posix()}\""
        )


def read_csv_frame(path: Path) -> pd.DataFrame:
    require_real_file(path)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def gtfs_rows(path: Path) -> Iterable[dict[str, str]]:
    require_real_file(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def safe_float(value: object) -> float | None:
    try:
        if value is None or value == "":
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def parse_gtfs_time(value: str | None) -> int | None:
    if not value:
        return None
    parts = value.split(":")
    if len(parts) != 3:
        return None
    try:
        hours, minutes, seconds = (int(part) for part in parts)
    except ValueError:
        return None
    return hours * 3600 + minutes * 60 + seconds


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def stop_sort_key(stop_id: str) -> tuple[int, int | str]:
    return (0, int(stop_id)) if stop_id.isdigit() else (1, stop_id)


def build_unified_station_mapping(stops: pd.DataFrame, radius_meters: float) -> dict[str, str]:
    stop_ids = stops["stop_id"].astype(str).tolist()
    stop_id_set = set(stop_ids)
    union_find = UnionFind(stop_ids)

    for row in stops.itertuples(index=False):
        stop_id = str(row.stop_id)
        parent_station = str(getattr(row, "parent_station", "") or "")
        if parent_station and parent_station in stop_id_set:
            union_find.union(stop_id, parent_station)

    if radius_meters > 0:
        cell_degrees = max(radius_meters / 111_320.0, 0.00001)
        buckets: dict[tuple[int, int], list[tuple[str, float, float]]] = defaultdict(list)
        for row in stops.itertuples(index=False):
            stop_id = str(row.stop_id)
            lat = safe_float(getattr(row, "stop_lat", ""))
            lon = safe_float(getattr(row, "stop_lon", ""))
            if lat is None or lon is None:
                continue
            cell = (math.floor(lat / cell_degrees), math.floor(lon / cell_degrees))
            for d_lat in (-1, 0, 1):
                for d_lon in (-1, 0, 1):
                    for other_id, other_lat, other_lon in buckets[
                        (cell[0] + d_lat, cell[1] + d_lon)
                    ]:
                        distance = haversine_meters(lat, lon, other_lat, other_lon)
                        if distance <= radius_meters:
                            union_find.union(stop_id, other_id)
            buckets[cell].append((stop_id, lat, lon))

    members_by_root: dict[str, list[str]] = defaultdict(list)
    for stop_id in stop_ids:
        members_by_root[union_find.find(stop_id)].append(stop_id)

    station_id_by_root = {
        root: min(members, key=stop_sort_key) for root, members in members_by_root.items()
    }
    return {
        stop_id: station_id_by_root[union_find.find(stop_id)]
        for stop_id in stop_ids
    }


def build_station_graphs(
    data_dir: Path,
    station_by_stop: dict[str, str],
) -> tuple[nx.DiGraph, nx.Graph, Counter[str], Counter[str], GraphBuildStats]:
    stop_times_path = data_dir / "stop_times.txt"
    edge_frequency: Counter[tuple[str, str]] = Counter()
    edge_time_total: Counter[tuple[str, str]] = Counter()
    edge_time_count: Counter[tuple[str, str]] = Counter()
    stop_use_counts: Counter[str] = Counter()
    station_use_counts: Counter[str] = Counter()
    stops_per_trip: Counter[str] = Counter()

    previous_trip_id: str | None = None
    previous_stop_id: str | None = None
    previous_station_id: str | None = None
    previous_departure_seconds: int | None = None
    previous_stop_sequence: int | None = None
    finished_trips: set[str] = set()

    rows_seen = 0
    skipped_same_station_segments = 0
    non_contiguous_trip_rows = 0
    out_of_order_stop_sequences = 0

    for row in gtfs_rows(stop_times_path):
        rows_seen += 1
        trip_id = row["trip_id"]
        stop_id = row["stop_id"]
        station_id = station_by_stop.get(stop_id, stop_id)
        stop_sequence = parse_int(row.get("stop_sequence", ""))
        arrival_seconds = parse_gtfs_time(row.get("arrival_time"))
        departure_seconds = parse_gtfs_time(row.get("departure_time")) or arrival_seconds

        if trip_id != previous_trip_id:
            if previous_trip_id is not None:
                finished_trips.add(previous_trip_id)
            if trip_id in finished_trips:
                non_contiguous_trip_rows += 1

        stop_use_counts[stop_id] += 1
        station_use_counts[station_id] += 1
        stops_per_trip[trip_id] += 1

        if previous_trip_id == trip_id and previous_station_id is not None:
            if (
                previous_stop_sequence is not None
                and stop_sequence is not None
                and stop_sequence < previous_stop_sequence
            ):
                out_of_order_stop_sequences += 1

            if previous_station_id == station_id:
                skipped_same_station_segments += 1
            else:
                edge = (previous_station_id, station_id)
                edge_frequency[edge] += 1
                if previous_departure_seconds is not None and arrival_seconds is not None:
                    duration = arrival_seconds - previous_departure_seconds
                    if 0 <= duration <= 6 * 3600:
                        edge_time_total[edge] += duration
                        edge_time_count[edge] += 1

        previous_trip_id = trip_id
        previous_stop_id = stop_id
        previous_station_id = station_id
        previous_departure_seconds = departure_seconds
        previous_stop_sequence = stop_sequence

    directed = nx.DiGraph()
    directed.add_nodes_from(station_use_counts)

    edge_means = [
        edge_time_total[edge] / edge_time_count[edge]
        for edge in edge_time_count
        if edge_time_count[edge] > 0
    ]
    fallback_impedance = statistics.median(edge_means) if edge_means else 1.0

    for edge, frequency in edge_frequency.items():
        source, target = edge
        observations = edge_time_count[edge]
        mean_travel = (
            edge_time_total[edge] / observations if observations else fallback_impedance
        )
        directed.add_edge(
            source,
            target,
            frequency=int(frequency),
            travel_time_observations=int(observations),
            mean_travel_seconds=float(mean_travel),
            impedance_seconds=float(max(mean_travel, 1.0)),
        )

    undirected = nx.Graph()
    undirected.add_nodes_from(station_use_counts)
    for source, target, data in directed.edges(data=True):
        if undirected.has_edge(source, target):
            existing = undirected[source][target]
            existing["frequency"] += data["frequency"]
            existing["travel_time_observations"] += data["travel_time_observations"]
            existing["_time_total"] += (
                data["mean_travel_seconds"] * data["travel_time_observations"]
            )
        else:
            undirected.add_edge(
                source,
                target,
                frequency=data["frequency"],
                travel_time_observations=data["travel_time_observations"],
                _time_total=data["mean_travel_seconds"] * data["travel_time_observations"],
            )

    for _, _, data in undirected.edges(data=True):
        observations = data["travel_time_observations"]
        mean_travel = data["_time_total"] / observations if observations else fallback_impedance
        data["mean_travel_seconds"] = float(mean_travel)
        data["impedance_seconds"] = float(max(mean_travel, 1.0))
        del data["_time_total"]

    trip_counts = list(stops_per_trip.values())
    stats = GraphBuildStats(
        stop_times_rows=rows_seen,
        active_stops=len(stop_use_counts),
        station_nodes=len(station_use_counts),
        active_trips=len(stops_per_trip),
        directed_edges=directed.number_of_edges(),
        undirected_edges=undirected.number_of_edges(),
        skipped_same_station_segments=skipped_same_station_segments,
        non_contiguous_trip_rows=non_contiguous_trip_rows,
        out_of_order_stop_sequences=out_of_order_stop_sequences,
        min_stops_per_trip=min(trip_counts) if trip_counts else 0,
        mean_stops_per_trip=sum(trip_counts) / len(trip_counts) if trip_counts else 0.0,
        max_stops_per_trip=max(trip_counts) if trip_counts else 0,
        timed_edge_observations=sum(edge_time_count.values()),
        fallback_impedance_seconds=float(fallback_impedance),
    )
    return directed, undirected, stop_use_counts, station_use_counts, stats


def parse_int(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def make_station_table(
    stops: pd.DataFrame,
    station_by_stop: dict[str, str],
    stop_use_counts: Counter[str],
    station_use_counts: Counter[str],
) -> pd.DataFrame:
    rows = []
    stops_by_id = stops.set_index("stop_id", drop=False)
    stops_in_station: dict[str, list[str]] = defaultdict(list)
    for stop_id, station_id in station_by_stop.items():
        stops_in_station[station_id].append(stop_id)

    for station_id, stop_ids in stops_in_station.items():
        active_stop_ids = [stop_id for stop_id in stop_ids if stop_use_counts[stop_id] > 0]
        ranking_pool = active_stop_ids or stop_ids
        main_stop_id = max(
            ranking_pool,
            key=lambda stop_id: (stop_use_counts[stop_id], -stop_sort_key(stop_id)[0]),
        )
        main = stops_by_id.loc[main_stop_id]
        latitudes = []
        longitudes = []
        for stop_id in stop_ids:
            row = stops_by_id.loc[stop_id]
            lat = safe_float(row.get("stop_lat", ""))
            lon = safe_float(row.get("stop_lon", ""))
            if lat is not None and lon is not None:
                latitudes.append(lat)
                longitudes.append(lon)
        rows.append(
            {
                "station_id": station_id,
                "station_name": main.get("stop_name", ""),
                "main_stop_id": main_stop_id,
                "main_stop_code": main.get("stop_code", ""),
                "station_lat": sum(latitudes) / len(latitudes) if latitudes else "",
                "station_lon": sum(longitudes) / len(longitudes) if longitudes else "",
                "stop_count": len(stop_ids),
                "active_stop_count": len(active_stop_ids),
                "stop_use_count": int(station_use_counts[station_id]),
                "member_stop_ids": ";".join(sorted(stop_ids, key=stop_sort_key)[:20]),
            }
        )
    return pd.DataFrame(rows)


def attach_station_attributes(graph: nx.Graph, station_table: pd.DataFrame) -> None:
    attrs = station_table.set_index("station_id").to_dict("index")
    nx.set_node_attributes(graph, attrs)


def network_summary(directed: nx.DiGraph, undirected: nx.Graph) -> dict[str, object]:
    if undirected.number_of_nodes() == 0:
        return {}
    component_sizes = sorted((len(c) for c in nx.connected_components(undirected)), reverse=True)
    weak_sizes = sorted((len(c) for c in nx.weakly_connected_components(directed)), reverse=True)
    strong_sizes = sorted((len(c) for c in nx.strongly_connected_components(directed)), reverse=True)
    articulation_points = list(nx.articulation_points(undirected))
    bridges = list(nx.bridges(undirected))
    return {
        "station_nodes": undirected.number_of_nodes(),
        "directed_edges": directed.number_of_edges(),
        "undirected_edges": undirected.number_of_edges(),
        "connected_components": len(component_sizes),
        "largest_component_nodes": component_sizes[0],
        "largest_component_share": component_sizes[0] / undirected.number_of_nodes(),
        "weakly_connected_components": len(weak_sizes),
        "strongly_connected_components": len(strong_sizes),
        "largest_strong_component_nodes": strong_sizes[0],
        "average_degree": mean(dict(undirected.degree()).values()),
        "density": nx.density(undirected),
        "articulation_points": len(articulation_points),
        "bridges": len(bridges),
    }


def compute_metrics(
    directed: nx.DiGraph,
    undirected: nx.Graph,
    station_table: pd.DataFrame,
    station_use_counts: Counter[str],
    betweenness_samples: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    n = undirected.number_of_nodes()
    degree = dict(undirected.degree())
    weighted_degree = dict(undirected.degree(weight="frequency"))
    in_degree = dict(directed.in_degree())
    out_degree = dict(directed.out_degree())
    in_weight = dict(directed.in_degree(weight="frequency"))
    out_weight = dict(directed.out_degree(weight="frequency"))
    pagerank = nx.pagerank(directed, weight="frequency") if n else {}

    if betweenness_samples > 0 and n:
        component_nodes = max(nx.connected_components(undirected), key=len)
        component = undirected.subgraph(component_nodes).copy()
        k = min(betweenness_samples, component.number_of_nodes())
        betweenness = nx.betweenness_centrality(
            component,
            k=k,
            seed=seed,
            weight="impedance_seconds",
            normalized=True,
        )
    else:
        betweenness = {}

    articulation = set(nx.articulation_points(undirected)) if n else set()
    community_by_station, community_summary = detect_communities(undirected, station_table, seed)

    rows = []
    for station_id in undirected.nodes:
        rows.append(
            {
                "station_id": station_id,
                "stop_use_count": int(station_use_counts[station_id]),
                "degree": degree.get(station_id, 0),
                "degree_centrality": degree.get(station_id, 0) / (n - 1) if n > 1 else 0,
                "weighted_degree": weighted_degree.get(station_id, 0),
                "in_degree": in_degree.get(station_id, 0),
                "out_degree": out_degree.get(station_id, 0),
                "in_weight": in_weight.get(station_id, 0),
                "out_weight": out_weight.get(station_id, 0),
                "pagerank": pagerank.get(station_id, 0.0),
                "approx_betweenness": betweenness.get(station_id, 0.0),
                "is_articulation_point": station_id in articulation,
                "community_id": community_by_station.get(station_id),
            }
        )
    metrics = pd.DataFrame(rows).merge(station_table, on="station_id", how="left")
    if not community_summary.empty:
        community_sizes = community_summary.set_index("community_id")["stations"].to_dict()
        metrics["community_size"] = metrics["community_id"].map(community_sizes)
    return metrics, community_summary


def detect_communities(
    graph: nx.Graph,
    station_table: pd.DataFrame,
    seed: int,
) -> tuple[dict[str, int], pd.DataFrame]:
    if graph.number_of_nodes() == 0:
        return {}, pd.DataFrame()
    communities = nx.algorithms.community.louvain_communities(
        graph,
        weight="frequency",
        seed=seed,
    )
    communities = sorted(communities, key=len, reverse=True)
    community_by_station = {}
    for community_id, nodes in enumerate(communities, start=1):
        for station_id in nodes:
            community_by_station[station_id] = community_id

    station_names = station_table.set_index("station_id")["station_name"].to_dict()
    rows = []
    for community_id, nodes in enumerate(communities, start=1):
        subgraph = graph.subgraph(nodes)
        weighted_degree = dict(subgraph.degree(weight="frequency"))
        top_station = max(nodes, key=lambda node: weighted_degree.get(node, 0))
        rows.append(
            {
                "community_id": community_id,
                "stations": len(nodes),
                "internal_edges": subgraph.number_of_edges(),
                "total_internal_frequency": int(
                    sum(data.get("frequency", 0) for _, _, data in subgraph.edges(data=True))
                ),
                "top_station_id": top_station,
                "top_station_name": station_names.get(top_station, ""),
                "top_station_weighted_degree": weighted_degree.get(top_station, 0),
            }
        )
    return community_by_station, pd.DataFrame(rows)


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def linspace_int(start: int, stop: int, count: int) -> list[int]:
    if count <= 1:
        return [stop]
    return [round(start + (stop - start) * index / (count - 1)) for index in range(count)]


def component_summary(
    graph: nx.Graph,
    reference_node_count: int | None = None,
) -> tuple[int, int, float]:
    if graph.number_of_nodes() == 0:
        return 0, 0, 0.0
    sizes = sorted((len(component) for component in nx.connected_components(graph)), reverse=True)
    denominator = reference_node_count or graph.number_of_nodes()
    return len(sizes), sizes[0], sizes[0] / denominator if denominator else 0.0


def sample_origin_stations(
    graph: nx.Graph,
    metrics: pd.DataFrame,
    sample_size: int,
    seed: int,
) -> list[str]:
    if graph.number_of_nodes() == 0 or sample_size <= 0:
        return []
    largest = list(max(nx.connected_components(graph), key=len))
    rng = random.Random(seed)
    rng.shuffle(largest)
    return largest[: min(sample_size, len(largest))]


def accessibility_snapshot(
    graph: nx.Graph,
    origins: list[str],
    cutoff_seconds: float,
    weight: str = "impedance_seconds",
    reference_node_count: int | None = None,
) -> dict[str, float | int]:
    reference_n = reference_node_count or graph.number_of_nodes()
    components, largest_nodes, largest_share = component_summary(graph, reference_n)
    reachable_counts = []
    reachable_shares = []
    path_means = []
    evaluated = 0
    missing_origins = 0
    n = graph.number_of_nodes()

    for origin in origins:
        evaluated += 1
        if origin not in graph:
            missing_origins += 1
            reachable_counts.append(0)
            reachable_shares.append(0.0)
            continue
        lengths = nx.single_source_dijkstra_path_length(
            graph,
            origin,
            cutoff=cutoff_seconds,
            weight=weight,
        )
        lengths.pop(origin, None)
        reachable_counts.append(len(lengths))
        reachable_shares.append(len(lengths) / (reference_n - 1) if reference_n > 1 else 0.0)
        if lengths:
            path_means.append(sum(lengths.values()) / len(lengths))

    return {
        "station_nodes": n,
        "reference_station_nodes": reference_n,
        "connected_components": components,
        "largest_component_nodes": largest_nodes,
        "largest_component_share": largest_share,
        "origins_evaluated": evaluated,
        "origins_missing": missing_origins,
        "mean_reachable_stations": mean(reachable_counts),
        "mean_reachable_share": mean(reachable_shares),
        "mean_path_seconds_to_reachable": mean(path_means),
    }


def ranking_lists(metrics: pd.DataFrame) -> dict[str, list[str]]:
    articulation_rank = metrics.sort_values(
        ["is_articulation_point", "degree", "weighted_degree"],
        ascending=[False, False, False],
    )["station_id"].tolist()
    return {
        "weighted_degree": metrics.sort_values("weighted_degree", ascending=False)[
            "station_id"
        ].tolist(),
        "pagerank": metrics.sort_values("pagerank", ascending=False)["station_id"].tolist(),
        "approx_betweenness": metrics.sort_values("approx_betweenness", ascending=False)[
            "station_id"
        ].tolist(),
        "articulation_degree": articulation_rank,
    }


def resilience_curve(
    graph: nx.Graph,
    rankings: dict[str, list[str]],
    origins: list[str],
    cutoff_seconds: float,
    max_removals: int,
    steps: int,
    random_trials: int,
    seed: int,
) -> pd.DataFrame:
    reference_node_count = graph.number_of_nodes()
    baseline = accessibility_snapshot(
        graph,
        origins,
        cutoff_seconds,
        reference_node_count=reference_node_count,
    )
    baseline_reachable_share = float(baseline["mean_reachable_share"])
    baseline_largest_share = float(baseline["largest_component_share"])
    max_removals = min(max_removals, max(graph.number_of_nodes() - 1, 0))
    removal_counts = sorted(set(linspace_int(0, max_removals, steps)))
    rows = []

    for strategy, ordered_nodes in rankings.items():
        for removed_count in removal_counts:
            subgraph = graph.copy()
            subgraph.remove_nodes_from(ordered_nodes[:removed_count])
            snapshot = accessibility_snapshot(
                subgraph,
                origins,
                cutoff_seconds,
                reference_node_count=reference_node_count,
            )
            rows.append(
                {
                    "strategy": strategy,
                    "removed_stations": removed_count,
                    **snapshot,
                    "largest_component_share_loss": baseline_largest_share
                    - float(snapshot["largest_component_share"]),
                    "reachable_share_loss": baseline_reachable_share
                    - float(snapshot["mean_reachable_share"]),
                }
            )

    rng = random.Random(seed)
    nodes = list(graph.nodes)
    for removed_count in removal_counts:
        trial_rows = []
        for _ in range(random_trials):
            subgraph = graph.copy()
            subgraph.remove_nodes_from(rng.sample(nodes, removed_count))
            trial_rows.append(
                accessibility_snapshot(
                    subgraph,
                    origins,
                    cutoff_seconds,
                    reference_node_count=reference_node_count,
                )
            )
        averaged = average_snapshots(trial_rows)
        rows.append(
            {
                "strategy": "random_mean",
                "removed_stations": removed_count,
                **averaged,
                "largest_component_share_loss": baseline_largest_share
                - float(averaged["largest_component_share"]),
                "reachable_share_loss": baseline_reachable_share
                - float(averaged["mean_reachable_share"]),
            }
        )
    return pd.DataFrame(rows)


def average_snapshots(snapshots: list[dict[str, float | int]]) -> dict[str, float]:
    if not snapshots:
        return {}
    keys = snapshots[0].keys()
    return {key: mean(float(snapshot[key]) for snapshot in snapshots) for key in keys}


def single_station_disruptions(
    graph: nx.Graph,
    metrics: pd.DataFrame,
    rankings: dict[str, list[str]],
    origins: list[str],
    cutoff_seconds: float,
    candidates_per_strategy: int,
) -> pd.DataFrame:
    reference_node_count = graph.number_of_nodes()
    baseline = accessibility_snapshot(
        graph,
        origins,
        cutoff_seconds,
        reference_node_count=reference_node_count,
    )
    candidates = []
    for ordered_nodes in rankings.values():
        candidates.extend(ordered_nodes[:candidates_per_strategy])
    candidates = list(dict.fromkeys(candidates))

    rows = []
    for station_id in candidates:
        subgraph = graph.copy()
        subgraph.remove_node(station_id)
        snapshot = accessibility_snapshot(
            subgraph,
            origins,
            cutoff_seconds,
            reference_node_count=reference_node_count,
        )
        rows.append(
            {
                "station_id": station_id,
                **snapshot,
                "largest_component_nodes_loss": int(baseline["largest_component_nodes"])
                - int(snapshot["largest_component_nodes"]),
                "largest_component_share_loss": float(baseline["largest_component_share"])
                - float(snapshot["largest_component_share"]),
                "reachable_share_loss": float(baseline["mean_reachable_share"])
                - float(snapshot["mean_reachable_share"]),
                "mean_path_seconds_increase": float(
                    snapshot["mean_path_seconds_to_reachable"]
                )
                - float(baseline["mean_path_seconds_to_reachable"]),
            }
        )
    impact = pd.DataFrame(rows)
    columns = [
        "station_id",
        "station_name",
        "main_stop_code",
        "degree",
        "weighted_degree",
        "pagerank",
        "approx_betweenness",
        "is_articulation_point",
    ]
    enriched = impact.merge(metrics[columns], on="station_id", how="left")
    return enriched.sort_values(
        ["reachable_share_loss", "largest_component_share_loss"],
        ascending=False,
    )


def single_segment_disruptions(
    graph: nx.Graph,
    station_table: pd.DataFrame,
    origins: list[str],
    cutoff_seconds: float,
    candidates_per_group: int,
) -> pd.DataFrame:
    reference_node_count = graph.number_of_nodes()
    baseline = accessibility_snapshot(
        graph,
        origins,
        cutoff_seconds,
        reference_node_count=reference_node_count,
    )
    station_names = station_table.set_index("station_id")["station_name"].to_dict()
    bridges = {normalized_edge(source, target) for source, target in nx.bridges(graph)}

    all_edges = list(graph.edges(data=True))
    by_frequency = sorted(
        all_edges,
        key=lambda edge: edge[2].get("frequency", 0),
        reverse=True,
    )[:candidates_per_group]
    bridge_edges = sorted(
        [edge for edge in all_edges if normalized_edge(edge[0], edge[1]) in bridges],
        key=lambda edge: edge[2].get("frequency", 0),
        reverse=True,
    )[:candidates_per_group]

    candidates = []
    seen = set()
    for source, target, data in [*by_frequency, *bridge_edges]:
        key = normalized_edge(source, target)
        if key in seen:
            continue
        candidates.append((source, target, data))
        seen.add(key)

    rows = []
    for source, target, data in candidates:
        subgraph = graph.copy()
        subgraph.remove_edge(source, target)
        snapshot = accessibility_snapshot(
            subgraph,
            origins,
            cutoff_seconds,
            reference_node_count=reference_node_count,
        )
        rows.append(
            {
                "source_station_id": source,
                "target_station_id": target,
                "source_station_name": station_names.get(source, ""),
                "target_station_name": station_names.get(target, ""),
                "frequency": data.get("frequency", 0),
                "mean_travel_seconds": data.get("mean_travel_seconds", 0.0),
                "is_bridge": normalized_edge(source, target) in bridges,
                **snapshot,
                "largest_component_nodes_loss": int(baseline["largest_component_nodes"])
                - int(snapshot["largest_component_nodes"]),
                "largest_component_share_loss": float(baseline["largest_component_share"])
                - float(snapshot["largest_component_share"]),
                "reachable_share_loss": float(baseline["mean_reachable_share"])
                - float(snapshot["mean_reachable_share"]),
                "mean_path_seconds_increase": float(
                    snapshot["mean_path_seconds_to_reachable"]
                )
                - float(baseline["mean_path_seconds_to_reachable"]),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["reachable_share_loss", "largest_component_share_loss"],
        ascending=False,
    )


def normalized_edge(source: str, target: str) -> tuple[str, str]:
    return tuple(sorted((source, target), key=stop_sort_key))


def recommend_backup_links(
    graph: nx.Graph,
    station_table: pd.DataFrame,
    removed_nodes: list[str],
    max_links: int,
    max_distance_meters: float,
) -> tuple[pd.DataFrame, nx.Graph]:
    scenario = graph.copy()
    scenario.remove_nodes_from(removed_nodes)
    station_index = station_table.set_index("station_id", drop=False)
    selected = []

    for step in range(1, max_links + 1):
        components = list(nx.connected_components(scenario))
        if len(components) <= 1:
            break
        component_by_node = {}
        component_size = {}
        for component_id, nodes in enumerate(components):
            size = len(nodes)
            component_size[component_id] = size
            for node in nodes:
                component_by_node[node] = component_id

        candidates = nearby_component_link_candidates(
            scenario,
            station_index,
            component_by_node,
            component_size,
            max_distance_meters,
        )
        if not candidates:
            break
        best = candidates[0]
        scenario.add_edge(
            best["source_station_id"],
            best["target_station_id"],
            frequency=0,
            mean_travel_seconds=best["walking_seconds"],
            impedance_seconds=best["walking_seconds"],
            backup_link=True,
        )
        selected.append({"step": step, **best})
    return pd.DataFrame(selected), scenario


def nearby_component_link_candidates(
    graph: nx.Graph,
    station_index: pd.DataFrame,
    component_by_node: dict[str, int],
    component_size: dict[int, int],
    max_distance_meters: float,
) -> list[dict[str, object]]:
    cell_degrees = max(max_distance_meters / 111_320.0, 0.00001)
    buckets: dict[tuple[int, int], list[tuple[str, float, float]]] = defaultdict(list)
    candidates = []

    for station_id in graph.nodes:
        if station_id not in station_index.index:
            continue
        row = station_index.loc[station_id]
        lat = safe_float(row.get("station_lat", ""))
        lon = safe_float(row.get("station_lon", ""))
        if lat is None or lon is None:
            continue
        cell = (math.floor(lat / cell_degrees), math.floor(lon / cell_degrees))
        for d_lat in (-1, 0, 1):
            for d_lon in (-1, 0, 1):
                for other_id, other_lat, other_lon in buckets[
                    (cell[0] + d_lat, cell[1] + d_lon)
                ]:
                    if graph.has_edge(station_id, other_id):
                        continue
                    source_component = component_by_node[station_id]
                    target_component = component_by_node[other_id]
                    if source_component == target_component:
                        continue
                    distance = haversine_meters(lat, lon, other_lat, other_lon)
                    if distance > max_distance_meters:
                        continue
                    source_size = component_size[source_component]
                    target_size = component_size[target_component]
                    candidates.append(
                        {
                            "source_station_id": station_id,
                            "target_station_id": other_id,
                            "source_station_name": station_index.loc[
                                station_id, "station_name"
                            ],
                            "target_station_name": station_index.loc[
                                other_id, "station_name"
                            ],
                            "distance_meters": distance,
                            "walking_seconds": max(distance / 1.2, 1.0),
                            "source_component_size": source_size,
                            "target_component_size": target_size,
                            "connectivity_benefit_score": min(source_size, target_size),
                        }
                    )
        buckets[cell].append((station_id, lat, lon))

    return sorted(
        candidates,
        key=lambda row: (
            -int(row["connectivity_benefit_score"]),
            float(row["distance_meters"]),
        ),
    )


def route_type_table(routes: pd.DataFrame) -> pd.DataFrame:
    counts = routes["route_type"].value_counts().rename_axis("route_type").reset_index(name="routes")
    counts["route_type_label"] = counts["route_type"].map(ROUTE_TYPE_LABELS).fillna("unknown")
    return counts[["route_type", "route_type_label", "routes"]]


def write_outputs(
    output_dir: Path,
    build_stats: GraphBuildStats,
    summary: dict[str, object],
    baseline_accessibility: dict[str, object],
    route_types: pd.DataFrame,
    station_table: pd.DataFrame,
    metrics: pd.DataFrame,
    community_summary: pd.DataFrame,
    resilience: pd.DataFrame,
    single_impacts: pd.DataFrame,
    segment_impacts: pd.DataFrame,
    backup_links: pd.DataFrame,
    mitigation_before: dict[str, object],
    mitigation_after: dict[str, object],
) -> None:
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame([asdict(build_stats)]).to_csv(
        tables_dir / "graph_build_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame([summary]).to_csv(
        tables_dir / "network_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame([baseline_accessibility]).to_csv(
        tables_dir / "baseline_accessibility.csv",
        index=False,
        encoding="utf-8-sig",
    )
    route_types.to_csv(tables_dir / "route_type_distribution.csv", index=False, encoding="utf-8-sig")
    station_table.to_csv(tables_dir / "unified_stations.csv", index=False, encoding="utf-8-sig")
    metrics.sort_values("weighted_degree", ascending=False).to_csv(
        tables_dir / "station_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    community_summary.to_csv(tables_dir / "community_summary.csv", index=False, encoding="utf-8-sig")
    resilience.to_csv(tables_dir / "resilience_curve.csv", index=False, encoding="utf-8-sig")
    single_impacts.to_csv(
        tables_dir / "single_station_disruption_impact.csv",
        index=False,
        encoding="utf-8-sig",
    )
    segment_impacts.to_csv(
        tables_dir / "single_segment_disruption_impact.csv",
        index=False,
        encoding="utf-8-sig",
    )
    backup_links.to_csv(tables_dir / "recommended_backup_links.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"scenario": "before_backup_links", **mitigation_before},
            {"scenario": "after_backup_links", **mitigation_after},
        ]
    ).to_csv(tables_dir / "mitigation_summary.csv", index=False, encoding="utf-8-sig")

    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "build_stats": asdict(build_stats),
                "network_summary": summary,
                "baseline_accessibility": baseline_accessibility,
                "mitigation_before": mitigation_before,
                "mitigation_after": mitigation_after,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )


def write_figures(
    output_dir: Path,
    metrics: pd.DataFrame,
    resilience: pd.DataFrame,
    single_impacts: pd.DataFrame,
    segment_impacts: pd.DataFrame,
    backup_links: pd.DataFrame,
) -> None:
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    plot_station_map(metrics, figures_dir / "unified_station_map.png")
    plot_resilience(resilience, figures_dir / "resilience_curve.png")
    plot_disruption_impacts(single_impacts, figures_dir / "single_station_impact.png")
    plot_segment_impacts(segment_impacts, figures_dir / "single_segment_impact.png")
    plot_backup_links(metrics, backup_links, figures_dir / "backup_links_map.png")


def plot_station_map(metrics: pd.DataFrame, path: Path) -> None:
    coords = metrics.copy()
    coords["station_lat"] = pd.to_numeric(coords["station_lat"], errors="coerce")
    coords["station_lon"] = pd.to_numeric(coords["station_lon"], errors="coerce")
    coords = coords.dropna(subset=["station_lat", "station_lon"])
    if coords.empty:
        return
    size_base = coords["weighted_degree"].astype(float)
    point_sizes = 2 + 40 * (size_base / max(size_base.max(), 1))
    plt.figure(figsize=(7, 9))
    plt.scatter(
        coords["station_lon"],
        coords["station_lat"],
        s=point_sizes,
        c=size_base,
        cmap="viridis",
        alpha=0.65,
        linewidths=0,
    )
    plt.colorbar(label="Weighted degree")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Unified Stations in Israel Public Transport")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_resilience(resilience: pd.DataFrame, path: Path) -> None:
    if resilience.empty:
        return
    plt.figure(figsize=(9, 6))
    for strategy, group in resilience.groupby("strategy"):
        group = group.sort_values("removed_stations")
        plt.plot(
            group["removed_stations"],
            group["mean_reachable_share"],
            marker="o",
            linewidth=1.6,
            label=strategy,
        )
    plt.xlabel("Removed stations")
    plt.ylabel("Mean reachable share within cutoff")
    plt.title("Accessibility Resilience Under Station Removal")
    plt.ylim(0, 1.02)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_disruption_impacts(single_impacts: pd.DataFrame, path: Path) -> None:
    if single_impacts.empty:
        return
    top = single_impacts.head(15).iloc[::-1]
    labels = top["station_id"].astype(str)
    values = top["reachable_share_loss"].astype(float)
    plt.figure(figsize=(8, 6))
    plt.barh(labels, values, color="#b91c1c")
    plt.xlabel("Reachable share loss")
    plt.ylabel("Station")
    plt.title("Largest Single-Station Accessibility Impacts")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_segment_impacts(segment_impacts: pd.DataFrame, path: Path) -> None:
    if segment_impacts.empty:
        return
    top = segment_impacts.head(15).iloc[::-1]
    labels = top["source_station_id"].astype(str) + "-" + top["target_station_id"].astype(str)
    values = top["reachable_share_loss"].astype(float)
    plt.figure(figsize=(8, 6))
    plt.barh(labels, values, color="#9333ea")
    plt.xlabel("Reachable share loss")
    plt.ylabel("Segment")
    plt.title("Largest Single-Segment Accessibility Impacts")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_backup_links(metrics: pd.DataFrame, backup_links: pd.DataFrame, path: Path) -> None:
    if backup_links.empty:
        return
    station_lookup = metrics.set_index("station_id")
    plt.figure(figsize=(7, 9))
    coords = metrics.copy()
    coords["station_lat"] = pd.to_numeric(coords["station_lat"], errors="coerce")
    coords["station_lon"] = pd.to_numeric(coords["station_lon"], errors="coerce")
    coords = coords.dropna(subset=["station_lat", "station_lon"])
    plt.scatter(coords["station_lon"], coords["station_lat"], s=2, color="#94a3b8", alpha=0.35)
    for row in backup_links.itertuples(index=False):
        source = station_lookup.loc[row.source_station_id]
        target = station_lookup.loc[row.target_station_id]
        plt.plot(
            [float(source.station_lon), float(target.station_lon)],
            [float(source.station_lat), float(target.station_lat)],
            color="#dc2626",
            linewidth=1.8,
            alpha=0.8,
        )
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Recommended Backup Links")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def print_runtime(message: str, started: float) -> None:
    elapsed = time.perf_counter() - started
    print(f"[{elapsed:7.1f}s] {message}", flush=True)


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    cutoff_seconds = args.accessibility_cutoff_minutes * 60
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print_runtime("Loading GTFS metadata", started)
    stops = read_csv_frame(args.data_dir / "stops.txt")
    routes = read_csv_frame(args.data_dir / "routes.txt")

    print_runtime("Merging nearby stops into unified station nodes", started)
    station_by_stop = build_unified_station_mapping(stops, args.merge_radius_meters)

    print_runtime("Building station graph from stop_times.txt", started)
    directed, undirected, stop_use_counts, station_use_counts, build_stats = build_station_graphs(
        args.data_dir,
        station_by_stop,
    )

    print_runtime("Attaching station metadata", started)
    station_table = make_station_table(stops, station_by_stop, stop_use_counts, station_use_counts)
    station_table = station_table[station_table["station_id"].isin(undirected.nodes)].copy()
    attach_station_attributes(directed, station_table)
    attach_station_attributes(undirected, station_table)

    print_runtime("Computing centrality and community baselines", started)
    metrics, community_summary = compute_metrics(
        directed,
        undirected,
        station_table,
        station_use_counts,
        args.betweenness_samples,
        args.seed,
    )

    print_runtime("Sampling origins and measuring baseline accessibility", started)
    origins = sample_origin_stations(undirected, metrics, args.accessibility_sample, args.seed)
    reference_node_count = undirected.number_of_nodes()
    baseline_accessibility = accessibility_snapshot(
        undirected,
        origins,
        cutoff_seconds,
        reference_node_count=reference_node_count,
    )
    rankings = ranking_lists(metrics)

    print_runtime("Running targeted and random disruption simulations", started)
    resilience = resilience_curve(
        undirected,
        rankings,
        origins,
        cutoff_seconds,
        args.resilience_removals,
        args.resilience_steps,
        args.random_trials,
        args.seed,
    )
    single_impacts = single_station_disruptions(
        undirected,
        metrics,
        rankings,
        origins,
        cutoff_seconds,
        args.single_disruption_candidates,
    )
    segment_impacts = single_segment_disruptions(
        undirected,
        station_table,
        origins,
        cutoff_seconds,
        args.single_segment_candidates,
    )

    print_runtime("Ranking candidate backup links", started)
    removed_for_mitigation = rankings["articulation_degree"][: args.mitigation_removals]
    mitigation_before_graph = undirected.copy()
    mitigation_before_graph.remove_nodes_from(removed_for_mitigation)
    mitigation_before = accessibility_snapshot(
        mitigation_before_graph,
        origins,
        cutoff_seconds,
        reference_node_count=reference_node_count,
    )
    backup_links, mitigation_after_graph = recommend_backup_links(
        undirected,
        station_table,
        removed_for_mitigation,
        args.backup_links,
        args.backup_link_distance_meters,
    )
    mitigation_after = accessibility_snapshot(
        mitigation_after_graph,
        origins,
        cutoff_seconds,
        reference_node_count=reference_node_count,
    )

    print_runtime("Writing tables and figures", started)
    summary = network_summary(directed, undirected)
    route_types = route_type_table(routes)
    write_outputs(
        args.output_dir,
        build_stats,
        summary,
        baseline_accessibility,
        route_types,
        station_table,
        metrics,
        community_summary,
        resilience,
        single_impacts,
        segment_impacts,
        backup_links,
        mitigation_before,
        mitigation_after,
    )
    write_figures(
        args.output_dir,
        metrics,
        resilience,
        single_impacts,
        segment_impacts,
        backup_links,
    )

    if args.write_graph:
        nx.write_graphml(undirected, args.output_dir / "station_graph.graphml")

    print_runtime("Done", started)
    print(f"Tables:  {args.output_dir / 'tables'}")
    print(f"Figures: {args.output_dir / 'figures'}")


if __name__ == "__main__":
    main()

"""Build and analyze a public-transport stop graph from GTFS files.

The project models stops as graph nodes and consecutive stops in a trip as
edges. Edge weights count how many scheduled trip segments use that stop pair.
The implementation streams stop_times.txt because Israel's GTFS feed is large.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
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
    active_trips: int
    directed_edges: int
    min_stops_per_trip: int
    mean_stops_per_trip: float
    max_stops_per_trip: int


@dataclass(frozen=True)
class NetworkSummary:
    active_stops: int
    directed_edges: int
    undirected_edges: int
    connected_components: int
    largest_component_nodes: int
    largest_component_share: float
    weakly_connected_components: int
    strongly_connected_components: int
    largest_strong_component_nodes: int
    average_degree: float
    density: float
    articulation_points: int
    bridges: int
    average_clustering: float | None = None
    transitivity: float | None = None
    approx_average_shortest_path: float | None = None
    approx_diameter: int | None = None
    louvain_communities: int | None = None
    largest_louvain_community_nodes: int | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze critical stations in Israel public transportation GTFS data."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("israel-public-transportation"),
        help="Directory containing GTFS txt files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory where tables, figures, and graph files will be written.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=30,
        help="Number of top stops/edges to export in ranking tables.",
    )
    parser.add_argument(
        "--betweenness-samples",
        type=int,
        default=128,
        help=(
            "Number of sampled source nodes for approximate betweenness. "
            "Use 0 to skip betweenness."
        ),
    )
    parser.add_argument(
        "--harmonic-samples",
        type=int,
        default=512,
        help=(
            "Number of sampled source nodes for approximate harmonic centrality. "
            "Use 0 to skip harmonic centrality."
        ),
    )
    parser.add_argument(
        "--path-source-samples",
        type=int,
        default=128,
        help="Number of source nodes sampled for global shortest-path statistics.",
    )
    parser.add_argument(
        "--clustering-trials",
        type=int,
        default=2000,
        help="Trials for approximate average clustering estimates.",
    )
    parser.add_argument(
        "--resilience-removals",
        type=int,
        default=500,
        help="Maximum number of stops removed in resilience simulations.",
    )
    parser.add_argument(
        "--resilience-steps",
        type=int,
        default=25,
        help="Number of removal points in resilience curves.",
    )
    parser.add_argument(
        "--random-trials",
        type=int,
        default=5,
        help="Number of random-removal trials for resilience baseline.",
    )
    parser.add_argument(
        "--accessibility-pairs",
        type=int,
        default=300,
        help="Number of sampled origin-destination stop pairs for accessibility damage.",
    )
    parser.add_argument(
        "--accessibility-removals",
        type=int,
        default=500,
        help="Maximum number of removed stops in accessibility-damage simulations.",
    )
    parser.add_argument(
        "--accessibility-steps",
        type=int,
        default=10,
        help="Number of removal points for accessibility-damage simulations.",
    )
    parser.add_argument(
        "--skip-model-comparison",
        action="store_true",
        help="Skip ER/configuration/BA/Watts-Strogatz model comparison.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for approximate metrics and random-removal baseline.",
    )
    parser.add_argument(
        "--write-graph",
        action="store_true",
        help="Write the undirected weighted stop graph to GraphML.",
    )
    return parser.parse_args()


def read_csv_frame(path: Path) -> pd.DataFrame:
    require_real_file(path)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def require_real_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}\n"
            f"If this is stop_times.txt, download it first (see README):\n"
            f'  gdown <GOOGLE_DRIVE_FILE_ID> -O "{path.as_posix()}"'
        )
    with path.open("rb") as handle:
        prefix = handle.read(80)
    if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise RuntimeError(
            f"{path} is a leftover Git LFS pointer from an older clone. "
            f"This repository no longer uses Git LFS - delete the file and "
            f"download the real one (see README)."
        )


def gtfs_rows(path: Path) -> Iterable[dict[str, str]]:
    require_real_file(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def enrich_stop_row(
    stop_id: str,
    stops: pd.DataFrame,
    metrics: dict[str, float | int],
) -> dict[str, object]:
    if stop_id in stops.index:
        row = stops.loc[stop_id]
        base = {
            "stop_id": stop_id,
            "stop_code": row.get("stop_code", ""),
            "stop_name": row.get("stop_name", ""),
            "stop_lat": row.get("stop_lat", ""),
            "stop_lon": row.get("stop_lon", ""),
            "zone_id": row.get("zone_id", ""),
        }
    else:
        base = {
            "stop_id": stop_id,
            "stop_code": "",
            "stop_name": "",
            "stop_lat": "",
            "stop_lon": "",
            "zone_id": "",
        }
    base.update(metrics)
    return base


def build_stop_graphs(
    data_dir: Path,
) -> tuple[nx.DiGraph, nx.Graph, Counter[str], GraphBuildStats]:
    """Build directed and undirected stop graphs from GTFS stop_times.txt.

    The feed is expected to be ordered by trip_id and stop_sequence, as GTFS
    exports commonly are. With that ordering, consecutive rows from the same
    trip define a transit segment.
    """

    stop_times_path = data_dir / "stop_times.txt"
    edge_counts: Counter[tuple[str, str]] = Counter()
    stop_use_counts: Counter[str] = Counter()
    stops_per_trip: Counter[str] = Counter()

    previous_trip_id: str | None = None
    previous_stop_id: str | None = None
    rows_seen = 0

    for row in gtfs_rows(stop_times_path):
        rows_seen += 1
        trip_id = row["trip_id"]
        stop_id = row["stop_id"]

        stop_use_counts[stop_id] += 1
        stops_per_trip[trip_id] += 1

        if (
            previous_trip_id == trip_id
            and previous_stop_id is not None
            and previous_stop_id != stop_id
        ):
            edge_counts[(previous_stop_id, stop_id)] += 1

        previous_trip_id = trip_id
        previous_stop_id = stop_id

    directed = nx.DiGraph()
    directed.add_nodes_from(stop_use_counts)
    for (source, target), frequency in edge_counts.items():
        directed.add_edge(source, target, frequency=frequency)

    undirected = nx.Graph()
    undirected.add_nodes_from(stop_use_counts)
    for (source, target), frequency in edge_counts.items():
        if undirected.has_edge(source, target):
            undirected[source][target]["frequency"] += frequency
        else:
            undirected.add_edge(source, target, frequency=frequency)

    trip_counts = list(stops_per_trip.values())
    stats = GraphBuildStats(
        stop_times_rows=rows_seen,
        active_stops=len(stop_use_counts),
        active_trips=len(stops_per_trip),
        directed_edges=directed.number_of_edges(),
        min_stops_per_trip=min(trip_counts),
        mean_stops_per_trip=sum(trip_counts) / len(trip_counts),
        max_stops_per_trip=max(trip_counts),
    )
    return directed, undirected, stop_use_counts, stats


def attach_stop_attributes(graph: nx.Graph, stops: pd.DataFrame) -> None:
    for stop_id in graph.nodes:
        if stop_id not in stops.index:
            continue
        row = stops.loc[stop_id]
        attrs = {
            "stop_code": row.get("stop_code", ""),
            "stop_name": row.get("stop_name", ""),
            "stop_lat": safe_float(row.get("stop_lat", "")),
            "stop_lon": safe_float(row.get("stop_lon", "")),
            "zone_id": row.get("zone_id", ""),
        }
        nx.set_node_attributes(graph, {stop_id: attrs})


def safe_float(value: object) -> float | None:
    try:
        if value == "":
            return None
        number = float(value)
        if math.isnan(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def largest_component_subgraph(graph: nx.Graph) -> nx.Graph:
    largest_nodes = max(nx.connected_components(graph), key=len)
    return graph.subgraph(largest_nodes).copy()


def summarize_network(
    directed: nx.DiGraph,
    undirected: nx.Graph,
    path_source_samples: int,
    clustering_trials: int,
    seed: int,
) -> NetworkSummary:
    component_sizes = sorted((len(c) for c in nx.connected_components(undirected)), reverse=True)
    weak_sizes = sorted((len(c) for c in nx.weakly_connected_components(directed)), reverse=True)
    strong_sizes = sorted(
        (len(c) for c in nx.strongly_connected_components(directed)), reverse=True
    )

    articulation_count = sum(1 for _ in nx.articulation_points(undirected))
    bridge_count = sum(1 for _ in nx.bridges(undirected))
    path_stats = sampled_path_statistics(undirected, path_source_samples, seed)

    return NetworkSummary(
        active_stops=undirected.number_of_nodes(),
        directed_edges=directed.number_of_edges(),
        undirected_edges=undirected.number_of_edges(),
        connected_components=len(component_sizes),
        largest_component_nodes=component_sizes[0],
        largest_component_share=component_sizes[0] / undirected.number_of_nodes(),
        weakly_connected_components=len(weak_sizes),
        strongly_connected_components=len(strong_sizes),
        largest_strong_component_nodes=strong_sizes[0],
        average_degree=sum(dict(undirected.degree()).values()) / undirected.number_of_nodes(),
        density=nx.density(undirected),
        articulation_points=articulation_count,
        bridges=bridge_count,
        average_clustering=approx_average_clustering(
            undirected, clustering_trials, seed
        ),
        transitivity=nx.transitivity(undirected),
        approx_average_shortest_path=path_stats["approx_average_shortest_path"],
        approx_diameter=path_stats["approx_diameter"],
    )


def approx_average_clustering(graph: nx.Graph, trials: int, seed: int) -> float | None:
    if graph.number_of_nodes() == 0 or trials <= 0:
        return None
    trials = min(trials, graph.number_of_nodes())
    return nx.algorithms.approximation.average_clustering(
        graph, trials=trials, seed=seed
    )


def sampled_path_statistics(
    graph: nx.Graph, source_samples: int, seed: int
) -> dict[str, float | int | None]:
    if graph.number_of_nodes() == 0 or source_samples <= 0:
        return {"approx_average_shortest_path": None, "approx_diameter": None}

    component = largest_component_subgraph(graph)
    rng = random.Random(seed)
    nodes = list(component.nodes)
    sources = rng.sample(nodes, min(source_samples, len(nodes)))

    distance_sum = 0
    reached_pairs = 0
    max_distance = 0
    for source in sources:
        lengths = nx.single_source_shortest_path_length(component, source)
        for target, distance in lengths.items():
            if target == source:
                continue
            distance_sum += distance
            reached_pairs += 1
            max_distance = max(max_distance, distance)

    if reached_pairs == 0:
        return {"approx_average_shortest_path": None, "approx_diameter": None}
    return {
        "approx_average_shortest_path": distance_sum / reached_pairs,
        "approx_diameter": max_distance,
    }


def compute_stop_metrics(
    directed: nx.DiGraph,
    undirected: nx.Graph,
    stop_use_counts: Counter[str],
    betweenness_samples: int,
    harmonic_samples: int,
    seed: int,
) -> pd.DataFrame:
    n = undirected.number_of_nodes()
    degree = dict(undirected.degree())
    weighted_degree = dict(undirected.degree(weight="frequency"))
    in_degree = dict(directed.in_degree())
    out_degree = dict(directed.out_degree())
    in_weight = dict(directed.in_degree(weight="frequency"))
    out_weight = dict(directed.out_degree(weight="frequency"))

    pagerank = weighted_pagerank(directed, weight="frequency")

    betweenness: dict[str, float]
    if betweenness_samples > 0:
        component = largest_component_subgraph(undirected)
        k = min(betweenness_samples, component.number_of_nodes())
        betweenness = nx.betweenness_centrality(component, k=k, seed=seed, weight=None)
    else:
        betweenness = {}

    harmonic = approximate_harmonic_centrality(undirected, harmonic_samples, seed)
    articulation = set(nx.articulation_points(undirected))

    rows = []
    for stop_id in undirected.nodes:
        rows.append(
            {
                "stop_id": stop_id,
                "stop_use_count": stop_use_counts[stop_id],
                "degree": degree.get(stop_id, 0),
                "degree_centrality": degree.get(stop_id, 0) / (n - 1),
                "weighted_degree": weighted_degree.get(stop_id, 0),
                "in_degree": in_degree.get(stop_id, 0),
                "out_degree": out_degree.get(stop_id, 0),
                "in_weight": in_weight.get(stop_id, 0),
                "out_weight": out_weight.get(stop_id, 0),
                "pagerank": pagerank.get(stop_id, 0.0),
                "approx_betweenness": betweenness.get(stop_id, 0.0),
                "approx_harmonic": harmonic.get(stop_id, 0.0),
                "is_articulation_point": stop_id in articulation,
            }
        )

    return pd.DataFrame(rows)


def weighted_pagerank(
    graph: nx.DiGraph,
    weight: str = "weight",
    alpha: float = 0.85,
    max_iter: int = 100,
    tol: float = 1.0e-6,
) -> dict[str, float]:
    """Compute weighted PageRank without requiring SciPy."""

    nodes = list(graph.nodes)
    n = len(nodes)
    if n == 0:
        return {}

    rank = {node: 1.0 / n for node in nodes}
    out_weight = {
        node: sum(data.get(weight, 1.0) for _, _, data in graph.out_edges(node, data=True))
        for node in nodes
    }

    for _ in range(max_iter):
        previous = rank
        dangling_rank = sum(previous[node] for node in nodes if out_weight[node] == 0)
        base_score = (1.0 - alpha) / n + alpha * dangling_rank / n
        rank = {node: base_score for node in nodes}

        for source in nodes:
            total = out_weight[source]
            if total == 0:
                continue
            source_rank = previous[source]
            for _, target, data in graph.out_edges(source, data=True):
                rank[target] += alpha * source_rank * data.get(weight, 1.0) / total

        error = sum(abs(rank[node] - previous[node]) for node in nodes)
        if error < n * tol:
            return rank

    return rank


def approximate_harmonic_centrality(
    graph: nx.Graph, samples: int, seed: int
) -> dict[str, float]:
    if graph.number_of_nodes() == 0 or samples <= 0:
        return {}

    rng = random.Random(seed)
    nodes = list(graph.nodes)
    sources = rng.sample(nodes, min(samples, len(nodes)))
    scores: defaultdict[str, float] = defaultdict(float)

    for source in sources:
        lengths = nx.single_source_shortest_path_length(graph, source)
        for target, distance in lengths.items():
            if target == source or distance == 0:
                continue
            scores[target] += 1.0 / distance

    scale = graph.number_of_nodes() / len(sources)
    return {node: value * scale for node, value in scores.items()}


def compute_louvain_communities(
    graph: nx.Graph,
    stops: pd.DataFrame,
    metrics: pd.DataFrame,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    communities = nx.algorithms.community.louvain_communities(
        graph, weight="frequency", seed=seed
    )
    communities = sorted(communities, key=len, reverse=True)

    community_by_stop = {}
    for community_id, community_nodes in enumerate(communities, start=1):
        for stop_id in community_nodes:
            community_by_stop[stop_id] = community_id

    metrics = metrics.copy()
    metrics["community_id"] = metrics["stop_id"].map(community_by_stop)
    community_sizes = metrics["community_id"].value_counts().to_dict()
    metrics["community_size"] = metrics["community_id"].map(community_sizes)

    summary_rows = []
    indexed_metrics = metrics.set_index("stop_id", drop=False)
    for community_id, community_nodes in enumerate(communities, start=1):
        subgraph = graph.subgraph(community_nodes)
        community_metrics = indexed_metrics.loc[list(community_nodes)]
        top_stop = community_metrics.sort_values(
            "weighted_degree", ascending=False
        ).iloc[0]
        summary_rows.append(
            {
                "community_id": community_id,
                "stops": len(community_nodes),
                "internal_edges": subgraph.number_of_edges(),
                "total_internal_frequency": int(
                    sum(data.get("frequency", 0) for _, _, data in subgraph.edges(data=True))
                ),
                "top_stop_id": top_stop["stop_id"],
                "top_stop_name": top_stop["stop_name"]
                if "stop_name" in top_stop and not pd.isna(top_stop["stop_name"])
                else stops.loc[top_stop["stop_id"], "stop_name"]
                if top_stop["stop_id"] in stops.index
                else "",
                "top_stop_weighted_degree": top_stop["weighted_degree"],
            }
        )

    return metrics, pd.DataFrame(summary_rows)


def centrality_correlation_table(metrics: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "degree",
        "weighted_degree",
        "pagerank",
        "approx_betweenness",
        "approx_harmonic",
        "stop_use_count",
    ]
    return metrics[columns].corr(method="spearman").round(4)


def add_stop_metadata(metrics: pd.DataFrame, stops: pd.DataFrame) -> pd.DataFrame:
    metadata_columns = ["stop_code", "stop_name", "stop_lat", "stop_lon", "zone_id"]
    metadata = stops.reset_index(drop=True)[["stop_id", *metadata_columns]].copy()
    enriched = metrics.merge(metadata, how="left", on="stop_id")
    ordered_columns = [
        "stop_id",
        "stop_code",
        "stop_name",
        "stop_lat",
        "stop_lon",
        "zone_id",
        "stop_use_count",
        "degree",
        "degree_centrality",
        "weighted_degree",
        "in_degree",
        "out_degree",
        "in_weight",
        "out_weight",
        "pagerank",
        "approx_betweenness",
        "approx_harmonic",
        "is_articulation_point",
    ]
    for optional in ["community_id", "community_size"]:
        if optional in enriched.columns:
            ordered_columns.append(optional)
    return enriched[ordered_columns]


def bridges_table(graph: nx.Graph, stops: pd.DataFrame, top_n: int) -> pd.DataFrame:
    rows = []
    for source, target in nx.bridges(graph):
        frequency = graph[source][target].get("frequency", 0)
        source_name = stops.loc[source, "stop_name"] if source in stops.index else ""
        target_name = stops.loc[target, "stop_name"] if target in stops.index else ""
        rows.append(
            {
                "source_stop_id": source,
                "source_stop_name": source_name,
                "target_stop_id": target,
                "target_stop_name": target_name,
                "frequency": frequency,
            }
        )
    return pd.DataFrame(rows).sort_values("frequency", ascending=False).head(top_n)


def route_type_table(routes: pd.DataFrame) -> pd.DataFrame:
    counts = routes["route_type"].value_counts().rename_axis("route_type").reset_index(name="routes")
    counts["route_type_label"] = counts["route_type"].map(ROUTE_TYPE_LABELS).fillna("unknown")
    return counts[["route_type", "route_type_label", "routes"]]


def degree_distribution_table(graph: nx.Graph) -> pd.DataFrame:
    counts = Counter(dict(graph.degree()).values())
    rows = []
    n = graph.number_of_nodes()
    cumulative = 0
    for degree, nodes in sorted(counts.items()):
        cumulative += nodes
        rows.append(
            {
                "degree": degree,
                "nodes": nodes,
                "probability": nodes / n if n else 0,
                "cumulative_probability": cumulative / n if n else 0,
            }
        )
    return pd.DataFrame(rows)


def compare_network_models(
    graph: nx.Graph,
    path_source_samples: int,
    clustering_trials: int,
    seed: int,
) -> pd.DataFrame:
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    if n == 0:
        return pd.DataFrame()

    degree_sequence = [degree for _, degree in graph.degree()]
    avg_degree = 2 * m / n if n else 0
    max_even_k = n - 1 if (n - 1) % 2 == 0 else n - 2
    ws_k = max(0, min(max_even_k, max(2, int(round(avg_degree)))))
    if ws_k % 2 == 1:
        ws_k = max(0, ws_k - 1)
    ba_m = max(1, min(n - 1, int(round(m / n))))

    models: list[tuple[str, nx.Graph]] = [
        ("real_transit", graph.copy()),
        ("erdos_renyi_gnm", nx.gnm_random_graph(n, m, seed=seed)),
        (
            "configuration_degree_sequence",
            simple_configuration_graph(degree_sequence, seed),
        ),
        ("barabasi_albert", nx.barabasi_albert_graph(n, ba_m, seed=seed)),
    ]
    if ws_k >= 2:
        models.append(
            (
                "watts_strogatz_small_world",
                nx.watts_strogatz_graph(n, ws_k, 0.05, seed=seed),
            )
        )

    return pd.DataFrame(
        [
            graph_property_row(
                name,
                model,
                path_source_samples=path_source_samples,
                clustering_trials=clustering_trials,
                seed=seed,
            )
            for name, model in models
        ]
    )


def simple_configuration_graph(degree_sequence: list[int], seed: int) -> nx.Graph:
    multigraph = nx.configuration_model(degree_sequence, seed=seed)
    graph = nx.Graph(multigraph)
    graph.remove_edges_from(nx.selfloop_edges(graph))
    return graph


def graph_property_row(
    name: str,
    graph: nx.Graph,
    path_source_samples: int,
    clustering_trials: int,
    seed: int,
) -> dict[str, object]:
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    component_sizes = sorted((len(c) for c in nx.connected_components(graph)), reverse=True)
    largest_share = component_sizes[0] / n if n else 0
    path_stats = sampled_path_statistics(graph, path_source_samples, seed)
    return {
        "model": name,
        "nodes": n,
        "edges": m,
        "average_degree": 2 * m / n if n else 0,
        "density": nx.density(graph) if n > 1 else 0,
        "connected_components": len(component_sizes),
        "largest_component_share": largest_share,
        "average_clustering": approx_average_clustering(
            graph, clustering_trials, seed
        ),
        "transitivity": nx.transitivity(graph),
        "approx_average_shortest_path": path_stats["approx_average_shortest_path"],
        "approx_diameter": path_stats["approx_diameter"],
    }


def resilience_curve(
    graph: nx.Graph,
    rankings: dict[str, list[str]],
    max_removals: int,
    steps: int,
    random_trials: int,
    seed: int,
) -> pd.DataFrame:
    baseline_nodes = graph.number_of_nodes()
    max_removals = min(max_removals, baseline_nodes - 1)
    removal_counts = sorted(
        set(int(round(x)) for x in linspace_int(0, max_removals, steps))
    )
    rng = random.Random(seed)
    nodes = list(graph.nodes)
    rows = []

    for strategy, ordered_nodes in rankings.items():
        for removed_count in removal_counts:
            removed = set(ordered_nodes[:removed_count])
            largest_size = largest_component_after_removal(graph, removed)
            rows.append(
                {
                    "strategy": strategy,
                    "removed_stops": removed_count,
                    "largest_component_nodes": largest_size,
                    "largest_component_share": largest_size / baseline_nodes,
                }
            )

    for removed_count in removal_counts:
        shares = []
        sizes = []
        for _ in range(random_trials):
            removed = set(rng.sample(nodes, removed_count))
            size = largest_component_after_removal(graph, removed)
            sizes.append(size)
            shares.append(size / baseline_nodes)
        rows.append(
            {
                "strategy": "random_mean",
                "removed_stops": removed_count,
                "largest_component_nodes": sum(sizes) / len(sizes),
                "largest_component_share": sum(shares) / len(shares),
            }
        )

    return pd.DataFrame(rows)


def accessibility_damage_table(
    graph: nx.Graph,
    rankings: dict[str, list[str]],
    max_removals: int,
    steps: int,
    pair_samples: int,
    random_trials: int,
    seed: int,
) -> pd.DataFrame:
    if graph.number_of_nodes() == 0 or pair_samples <= 0:
        return pd.DataFrame()

    baseline_nodes = graph.number_of_nodes()
    max_removals = min(max_removals, baseline_nodes - 1)
    removal_counts = sorted(
        set(int(round(x)) for x in linspace_int(0, max_removals, steps))
    )
    pairs = sample_origin_destination_pairs(graph, pair_samples, seed)
    baseline_distances = pair_distances(graph, pairs)
    rng = random.Random(seed)
    nodes = list(graph.nodes)
    rows = []

    for strategy, ordered_nodes in rankings.items():
        for removed_count in removal_counts:
            removed = set(ordered_nodes[:removed_count])
            rows.append(
                accessibility_row(
                    strategy,
                    graph,
                    removed,
                    removed_count,
                    pairs,
                    baseline_distances,
                )
            )

    for removed_count in removal_counts:
        trial_rows = []
        for _ in range(random_trials):
            removed = set(rng.sample(nodes, removed_count))
            trial_rows.append(
                accessibility_row(
                    "random_mean",
                    graph,
                    removed,
                    removed_count,
                    pairs,
                    baseline_distances,
                )
            )
        rows.append(mean_accessibility_rows("random_mean", removed_count, trial_rows))

    return pd.DataFrame(rows)


def sample_origin_destination_pairs(
    graph: nx.Graph, pair_samples: int, seed: int
) -> list[tuple[str, str]]:
    component = largest_component_subgraph(graph)
    rng = random.Random(seed)
    nodes = list(component.nodes)
    pairs = []
    while len(pairs) < pair_samples and len(nodes) >= 2:
        source, target = rng.sample(nodes, 2)
        pairs.append((source, target))
    return pairs


def pair_distances(
    graph: nx.Graph, pairs: list[tuple[str, str]]
) -> dict[tuple[str, str], int | None]:
    pairs_by_source: defaultdict[str, list[str]] = defaultdict(list)
    for source, target in pairs:
        pairs_by_source[source].append(target)

    distances: dict[tuple[str, str], int | None] = {}
    for source, targets in pairs_by_source.items():
        if source not in graph:
            for target in targets:
                distances[(source, target)] = None
            continue
        lengths = nx.single_source_shortest_path_length(graph, source)
        for target in targets:
            distances[(source, target)] = lengths.get(target)
    return distances


def accessibility_row(
    strategy: str,
    graph: nx.Graph,
    removed: set[str],
    removed_count: int,
    pairs: list[tuple[str, str]],
    baseline_distances: dict[tuple[str, str], int | None],
) -> dict[str, object]:
    remaining = graph.copy()
    remaining.remove_nodes_from(removed)
    after_distances = pair_distances(remaining, pairs)

    reachable_distances = [
        distance for distance in after_distances.values() if distance is not None
    ]
    stretch_values = []
    detour_values = []
    for pair, after_distance in after_distances.items():
        before_distance = baseline_distances.get(pair)
        if before_distance in (None, 0) or after_distance is None:
            continue
        stretch_values.append(after_distance / before_distance)
        detour_values.append(after_distance - before_distance)

    sampled_pairs = len(pairs)
    reachable_pairs = len(reachable_distances)
    return {
        "strategy": strategy,
        "removed_stops": removed_count,
        "sampled_pairs": sampled_pairs,
        "reachable_pairs": reachable_pairs,
        "reachable_share": reachable_pairs / sampled_pairs if sampled_pairs else 0,
        "average_shortest_path": mean_or_none(reachable_distances),
        "average_stretch": mean_or_none(stretch_values),
        "average_detour_edges": mean_or_none(detour_values),
    }


def mean_accessibility_rows(
    strategy: str, removed_count: int, rows: list[dict[str, object]]
) -> dict[str, object]:
    if not rows:
        return {
            "strategy": strategy,
            "removed_stops": removed_count,
            "sampled_pairs": 0,
            "reachable_pairs": 0,
            "reachable_share": 0,
            "average_shortest_path": None,
            "average_stretch": None,
            "average_detour_edges": None,
        }
    return {
        "strategy": strategy,
        "removed_stops": removed_count,
        "sampled_pairs": rows[0]["sampled_pairs"],
        "reachable_pairs": mean_or_none([row["reachable_pairs"] for row in rows]),
        "reachable_share": mean_or_none([row["reachable_share"] for row in rows]),
        "average_shortest_path": mean_or_none(
            [row["average_shortest_path"] for row in rows]
        ),
        "average_stretch": mean_or_none([row["average_stretch"] for row in rows]),
        "average_detour_edges": mean_or_none(
            [row["average_detour_edges"] for row in rows]
        ),
    }


def mean_or_none(values: Iterable[float | int | None]) -> float | None:
    filtered = [float(value) for value in values if value is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)


def linspace_int(start: int, stop: int, count: int) -> list[int]:
    if count <= 1:
        return [stop]
    return [round(start + (stop - start) * i / (count - 1)) for i in range(count)]


def largest_component_after_removal(graph: nx.Graph, removed: set[str]) -> int:
    if not removed:
        return max(len(c) for c in nx.connected_components(graph))
    remaining = graph.copy()
    remaining.remove_nodes_from(removed)
    if remaining.number_of_nodes() == 0:
        return 0
    return max((len(c) for c in nx.connected_components(remaining)), default=0)


def write_summary_tables(
    output_dir: Path,
    build_stats: GraphBuildStats,
    summary: NetworkSummary,
    route_types: pd.DataFrame,
    community_summary: pd.DataFrame,
    centrality_correlation: pd.DataFrame,
    degree_distribution: pd.DataFrame,
    model_comparison: pd.DataFrame,
) -> None:
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([asdict(build_stats)]).to_csv(
        tables_dir / "gtfs_graph_build_summary.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame([asdict(summary)]).to_csv(
        tables_dir / "network_summary.csv", index=False, encoding="utf-8-sig"
    )
    route_types.to_csv(tables_dir / "route_type_distribution.csv", index=False, encoding="utf-8-sig")
    community_summary.to_csv(
        tables_dir / "community_summary.csv", index=False, encoding="utf-8-sig"
    )
    centrality_correlation.to_csv(
        tables_dir / "centrality_correlation_spearman.csv", encoding="utf-8-sig"
    )
    degree_distribution.to_csv(
        tables_dir / "degree_distribution.csv", index=False, encoding="utf-8-sig"
    )
    model_comparison.to_csv(
        tables_dir / "network_model_comparison.csv", index=False, encoding="utf-8-sig"
    )
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {"build_stats": asdict(build_stats), "network_summary": asdict(summary)},
            handle,
            ensure_ascii=False,
            indent=2,
        )


def write_metric_tables(
    output_dir: Path,
    metrics: pd.DataFrame,
    bridges: pd.DataFrame,
    resilience: pd.DataFrame,
    accessibility: pd.DataFrame,
    top_n: int,
) -> None:
    tables_dir = output_dir / "tables"
    metrics.sort_values("weighted_degree", ascending=False).to_csv(
        tables_dir / "stop_metrics.csv", index=False, encoding="utf-8-sig"
    )
    ranking_specs = {
        "top_degree_stops.csv": "degree",
        "top_weighted_degree_stops.csv": "weighted_degree",
        "top_pagerank_stops.csv": "pagerank",
        "top_approx_betweenness_stops.csv": "approx_betweenness",
        "top_approx_harmonic_stops.csv": "approx_harmonic",
    }
    for filename, column in ranking_specs.items():
        metrics.sort_values(column, ascending=False).head(top_n).to_csv(
            tables_dir / filename, index=False, encoding="utf-8-sig"
        )
    metrics[metrics["is_articulation_point"]].sort_values(
        ["degree", "weighted_degree"], ascending=False
    ).head(top_n).to_csv(
        tables_dir / "top_articulation_points.csv", index=False, encoding="utf-8-sig"
    )
    bridges.to_csv(tables_dir / "top_bridges.csv", index=False, encoding="utf-8-sig")
    resilience.to_csv(
        tables_dir / "resilience_random_vs_targeted.csv", index=False, encoding="utf-8-sig"
    )
    accessibility.to_csv(
        tables_dir / "accessibility_damage_by_removal.csv",
        index=False,
        encoding="utf-8-sig",
    )


def write_figures(
    output_dir: Path,
    metrics: pd.DataFrame,
    route_types: pd.DataFrame,
    resilience: pd.DataFrame,
    community_summary: pd.DataFrame,
    degree_distribution: pd.DataFrame,
    model_comparison: pd.DataFrame,
    accessibility: pd.DataFrame,
) -> None:
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    plot_top_metric(
        metrics,
        "weighted_degree",
        "Top Stops by Scheduled Segment Frequency",
        figures_dir / "top_weighted_degree_stops.png",
    )
    plot_top_metric(
        metrics,
        "pagerank",
        "Top Stops by Weighted PageRank",
        figures_dir / "top_pagerank_stops.png",
    )
    plot_top_metric(
        metrics,
        "approx_harmonic",
        "Top Stops by Approximate Harmonic Centrality",
        figures_dir / "top_approx_harmonic_stops.png",
    )
    plot_route_types(route_types, figures_dir / "route_type_distribution.png")
    plot_community_sizes(community_summary, figures_dir / "top_communities.png")
    plot_resilience(resilience, figures_dir / "resilience_curve.png")
    plot_accessibility_damage(
        accessibility, figures_dir / "accessibility_damage_curve.png"
    )
    plot_degree_distribution(
        degree_distribution, figures_dir / "degree_distribution_loglog.png"
    )
    plot_model_comparison(
        model_comparison, figures_dir / "network_model_comparison.png"
    )
    plot_stop_map(metrics, figures_dir / "active_stops_map.png")


def plot_top_metric(metrics: pd.DataFrame, column: str, title: str, path: Path) -> None:
    top = metrics.sort_values(column, ascending=False).head(15).iloc[::-1]
    labels = top["stop_id"].astype(str)
    values = top[column].astype(float)

    plt.figure(figsize=(9, 6))
    plt.barh(labels, values, color="#2563eb")
    plt.xlabel(column.replace("_", " ").title())
    plt.ylabel("Stop ID")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_route_types(route_types: pd.DataFrame, path: Path) -> None:
    labels = route_types["route_type_label"] + " (" + route_types["route_type"] + ")"
    plt.figure(figsize=(8, 5))
    plt.bar(labels, route_types["routes"], color="#0f766e")
    plt.ylabel("Routes")
    plt.title("GTFS Route Types")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_community_sizes(community_summary: pd.DataFrame, path: Path) -> None:
    top = community_summary.sort_values("stops", ascending=False).head(15).iloc[::-1]
    labels = top["community_id"].astype(str)
    plt.figure(figsize=(8, 5))
    plt.barh(labels, top["stops"], color="#7c3aed")
    plt.xlabel("Stops")
    plt.ylabel("Community ID")
    plt.title("Largest Louvain Communities")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_resilience(resilience: pd.DataFrame, path: Path) -> None:
    if resilience.empty:
        return
    plt.figure(figsize=(9, 6))
    for strategy, group in resilience.groupby("strategy"):
        group = group.sort_values("removed_stops")
        plt.plot(
            group["removed_stops"],
            group["largest_component_share"],
            marker="o",
            linewidth=1.8,
            label=strategy,
        )
    plt.xlabel("Removed Stops")
    plt.ylabel("Largest Component Share")
    plt.title("Network Resilience Under Stop Removal")
    plt.ylim(0, 1.02)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_accessibility_damage(accessibility: pd.DataFrame, path: Path) -> None:
    if accessibility.empty:
        return
    plt.figure(figsize=(9, 6))
    for strategy, group in accessibility.groupby("strategy"):
        group = group.sort_values("removed_stops")
        plt.plot(
            group["removed_stops"],
            group["reachable_share"],
            marker="o",
            linewidth=1.8,
            label=strategy,
        )
    plt.xlabel("Removed Stops")
    plt.ylabel("Reachable OD Pair Share")
    plt.title("Accessibility Damage Under Stop Removal")
    plt.ylim(0, 1.02)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_degree_distribution(degree_distribution: pd.DataFrame, path: Path) -> None:
    if degree_distribution.empty:
        return
    plotted = degree_distribution[degree_distribution["degree"] > 0]
    plt.figure(figsize=(8, 5))
    plt.scatter(
        plotted["degree"],
        plotted["probability"],
        s=18,
        color="#dc2626",
        alpha=0.75,
    )
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Degree")
    plt.ylabel("P(k)")
    plt.title("Degree Distribution (log-log)")
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_model_comparison(model_comparison: pd.DataFrame, path: Path) -> None:
    if model_comparison.empty:
        return
    columns = ["average_clustering", "largest_component_share"]
    available = [column for column in columns if column in model_comparison.columns]
    if not available:
        return
    labels = model_comparison["model"].astype(str)
    x_positions = range(len(labels))
    width = 0.35

    plt.figure(figsize=(10, 5))
    for idx, column in enumerate(available):
        offsets = [x + (idx - (len(available) - 1) / 2) * width for x in x_positions]
        plt.bar(offsets, model_comparison[column].astype(float), width=width, label=column)
    plt.xticks(list(x_positions), labels, rotation=20, ha="right")
    plt.ylabel("Metric Value")
    plt.title("Real Transit Network vs. Network Models")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_stop_map(metrics: pd.DataFrame, path: Path) -> None:
    coords = metrics.copy()
    coords["stop_lat"] = pd.to_numeric(coords["stop_lat"], errors="coerce")
    coords["stop_lon"] = pd.to_numeric(coords["stop_lon"], errors="coerce")
    coords = coords.dropna(subset=["stop_lat", "stop_lon"])

    point_sizes = 2 + 30 * (
        coords["weighted_degree"].astype(float) / coords["weighted_degree"].max()
    )
    plt.figure(figsize=(7, 9))
    plt.scatter(
        coords["stop_lon"],
        coords["stop_lat"],
        s=point_sizes,
        c=coords["weighted_degree"].astype(float),
        cmap="viridis",
        alpha=0.65,
        linewidths=0,
    )
    plt.colorbar(label="Weighted degree")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Active GTFS Stops in Israel")
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def print_runtime(message: str, start_time: float) -> None:
    elapsed = time.perf_counter() - start_time
    print(f"[{elapsed:7.1f}s] {message}", flush=True)


def main() -> None:
    args = parse_args()
    started = time.perf_counter()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = args.output_dir / "tables"
    figures_dir = args.output_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    print_runtime("Loading GTFS metadata tables", started)
    stops = read_csv_frame(args.data_dir / "stops.txt").set_index("stop_id", drop=False)
    routes = read_csv_frame(args.data_dir / "routes.txt")

    print_runtime("Building stop graphs from stop_times.txt", started)
    directed, undirected, stop_use_counts, build_stats = build_stop_graphs(args.data_dir)
    attach_stop_attributes(directed, stops)
    attach_stop_attributes(undirected, stops)

    print_runtime("Summarizing network structure", started)
    summary = summarize_network(
        directed,
        undirected,
        path_source_samples=args.path_source_samples,
        clustering_trials=args.clustering_trials,
        seed=args.seed,
    )
    route_types = route_type_table(routes)
    degree_distribution = degree_distribution_table(undirected)

    print_runtime("Computing centrality metrics", started)
    metrics = compute_stop_metrics(
        directed=directed,
        undirected=undirected,
        stop_use_counts=stop_use_counts,
        betweenness_samples=args.betweenness_samples,
        harmonic_samples=args.harmonic_samples,
        seed=args.seed,
    )
    metrics = add_stop_metadata(metrics, stops)

    print_runtime("Detecting Louvain communities", started)
    metrics, community_summary = compute_louvain_communities(
        graph=undirected, stops=stops, metrics=metrics, seed=args.seed
    )
    summary = replace(
        summary,
        louvain_communities=len(community_summary),
        largest_louvain_community_nodes=int(community_summary["stops"].max()),
    )
    centrality_correlation = centrality_correlation_table(metrics)

    print_runtime("Running resilience simulations", started)
    articulation_rank = metrics.sort_values(
        ["is_articulation_point", "degree", "weighted_degree"],
        ascending=[False, False, False],
    )["stop_id"].tolist()
    rankings = {
        "weighted_degree": metrics.sort_values("weighted_degree", ascending=False)[
            "stop_id"
        ].tolist(),
        "pagerank": metrics.sort_values("pagerank", ascending=False)["stop_id"].tolist(),
        "approx_betweenness": metrics.sort_values("approx_betweenness", ascending=False)[
            "stop_id"
        ].tolist(),
        "approx_harmonic": metrics.sort_values("approx_harmonic", ascending=False)[
            "stop_id"
        ].tolist(),
        "articulation_degree": articulation_rank,
    }
    resilience = resilience_curve(
        graph=undirected,
        rankings=rankings,
        max_removals=args.resilience_removals,
        steps=args.resilience_steps,
        random_trials=args.random_trials,
        seed=args.seed,
    )

    print_runtime("Running accessibility-damage simulations", started)
    accessibility = accessibility_damage_table(
        graph=undirected,
        rankings=rankings,
        max_removals=args.accessibility_removals,
        steps=args.accessibility_steps,
        pair_samples=args.accessibility_pairs,
        random_trials=args.random_trials,
        seed=args.seed,
    )

    print_runtime("Comparing with network models", started)
    if args.skip_model_comparison:
        model_comparison = pd.DataFrame()
    else:
        model_comparison = compare_network_models(
            graph=undirected,
            path_source_samples=args.path_source_samples,
            clustering_trials=args.clustering_trials,
            seed=args.seed,
        )

    print_runtime("Writing tables and figures", started)
    bridges = bridges_table(undirected, stops, args.top_n)
    write_summary_tables(
        args.output_dir,
        build_stats,
        summary,
        route_types,
        community_summary,
        centrality_correlation,
        degree_distribution,
        model_comparison,
    )
    write_metric_tables(
        args.output_dir, metrics, bridges, resilience, accessibility, args.top_n
    )
    write_figures(
        args.output_dir,
        metrics,
        route_types,
        resilience,
        community_summary,
        degree_distribution,
        model_comparison,
        accessibility,
    )

    if args.write_graph:
        graph_path = args.output_dir / "stop_graph_weighted.graphml"
        nx.write_graphml(undirected, graph_path)

    print_runtime("Done", started)
    print(f"Tables:  {tables_dir}")
    print(f"Figures: {figures_dir}")


if __name__ == "__main__":
    main()

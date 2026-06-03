"""
Stage 06B -- socioeconomic equity analysis.

This script joins transit stops to the CBS 2021 socioeconomic statistical-area
layer, then compares transit availability across socioeconomic clusters and
across Louvain communities.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import requests

matplotlib.use("Agg")
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from _hebrew_bidi import install_hebrew
install_hebrew()
import matplotlib.pyplot as plt
import seaborn as sns


ROOT = Path(__file__).resolve().parents[3]
STAGE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = STAGE_DIR / "outputs"
FIG_DIR = ROOT / "public_transport_network_research/figures/06_regional_comparison"

REGIONAL_STOPS_CSV = OUT_DIR / "stops_with_region.csv"
STAGED_METRICS_CSV = ROOT / "public_transport_network_research/04_centrality_analysis/outputs/stop_metrics.csv"
COMMUNITIES_CSV = ROOT / "public_transport_network_research/07_community_detection/outputs/community_assignments.csv"
PRIMARY_STOP_METRICS_CSV = ROOT / "outputs/tables/stop_metrics.csv"

CBS_LAYER_URL = (
    "https://services2.arcgis.com/xMRYm7cNgdR5RN6F/arcgis/rest/services/"
    "SOEC_Stat11_2021/FeatureServer/27"
)
PAGE_SIZE = 2000
NEAREST_JOIN_MAX_DISTANCE_M = 3000

SOCIO_FIELDS = [
    "SEMEL_YISH",
    "STAT11",
    "YISHUV_STA",
    "Shem_Yishuv",
    "Shem_Yishuv_English",
    "Pop_Total",
    "eshkol_mad",
    "CLUSTER_2021",
    "INDEX_VALUE_2021",
    "שם_יישוב",
    "סמל_יישוב",
    "סמל_אזור_סטטיסטי",
    "אוכלוסיית_המדד",
    "ערך_מדד",
    "אשכול",
]

sns.set_theme(style="whitegrid", font_scale=1.0)


def first_existing(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    values = None
    for col in columns:
        if col in df.columns:
            if values is None:
                values = df[col].copy()
            else:
                values = values.where(values.notna(), df[col])
    if values is None:
        return pd.Series(pd.NA, index=df.index, dtype="object")
    return values


def mode_or_na(series: pd.Series):
    values = series.dropna()
    if values.empty:
        return pd.NA
    return values.mode().iloc[0]


def per_1000(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = pd.to_numeric(denominator, errors="coerce")
    numerator = pd.to_numeric(numerator, errors="coerce")
    return np.where(denominator > 0, numerator / denominator * 1000, np.nan)


def query_url(offset: int | None = None, count_only: bool = False) -> str:
    params = {
        "where": "1=1",
        "f": "json" if count_only else "geojson",
    }
    if count_only:
        params["returnCountOnly"] = "true"
    else:
        params.update(
            {
                "outFields": ",".join(SOCIO_FIELDS),
                "returnGeometry": "true",
                "outSR": "4326",
                "resultRecordCount": str(PAGE_SIZE),
                "resultOffset": str(offset or 0),
            }
        )
    return f"{CBS_LAYER_URL}/query?{urlencode(params, safe=',')}"


def load_socioeconomic_areas() -> gpd.GeoDataFrame:
    response = requests.get(query_url(count_only=True), timeout=60)
    response.raise_for_status()
    total = int(response.json()["count"])

    batches = []
    for offset in range(0, total, PAGE_SIZE):
        print(f"  Loading CBS socioeconomic polygons {offset + 1}-{min(offset + PAGE_SIZE, total)} / {total}")
        batches.append(gpd.read_file(query_url(offset=offset)))

    raw = pd.concat(batches, ignore_index=True)
    raw = gpd.GeoDataFrame(raw, geometry="geometry", crs="EPSG:4326")

    socio = gpd.GeoDataFrame(
        {
            "socio_locality_code": first_existing(raw, ["SEMEL_YISH", "סמל_יישוב"]),
            "socio_stat_area_code": first_existing(raw, ["STAT11", "סמל_אזור_סטטיסטי"]),
            "socio_unit_full_code": first_existing(raw, ["YISHUV_STA"]),
            "socio_locality": first_existing(raw, ["Shem_Yishuv", "שם_יישוב"]),
            "socio_locality_en": first_existing(raw, ["Shem_Yishuv_English"]),
            "socio_population": first_existing(raw, ["אוכלוסיית_המדד", "Pop_Total"]),
            "socio_cluster": first_existing(raw, ["אשכול", "eshkol_mad", "CLUSTER_2021"]),
            "socio_index_value": first_existing(raw, ["ערך_מדד", "INDEX_VALUE_2021"]),
        },
        geometry=raw.geometry,
        crs=raw.crs,
    )

    for col in [
        "socio_locality_code",
        "socio_stat_area_code",
        "socio_unit_full_code",
        "socio_population",
        "socio_cluster",
        "socio_index_value",
    ]:
        socio[col] = pd.to_numeric(socio[col], errors="coerce")

    fallback_id = (
        socio["socio_locality_code"].astype("Int64").astype(str)
        + "_"
        + socio["socio_stat_area_code"].astype("Int64").astype(str)
    )
    socio["socio_unit_id"] = socio["socio_unit_full_code"].astype("Int64").astype(str)
    socio.loc[socio["socio_unit_full_code"].isna(), "socio_unit_id"] = fallback_id
    socio["socio_cluster"] = socio["socio_cluster"].astype("Int64")

    keep = socio["socio_cluster"].between(1, 10) & socio.geometry.notna()
    return socio.loc[keep].copy()


def load_stops() -> pd.DataFrame:
    base_path = REGIONAL_STOPS_CSV if REGIONAL_STOPS_CSV.exists() else STAGED_METRICS_CSV
    stops = pd.read_csv(base_path, encoding="utf-8-sig")

    if "lat" not in stops.columns and "stop_lat" in stops.columns:
        stops["lat"] = stops["stop_lat"]
    if "lon" not in stops.columns and "stop_lon" in stops.columns:
        stops["lon"] = stops["stop_lon"]

    stops["stop_id"] = stops["stop_id"].astype(str)
    stops["degree"] = pd.to_numeric(stops.get("degree", 0), errors="coerce").fillna(0)
    if "is_critical" in stops.columns:
        stops["is_critical"] = stops["is_critical"].astype(str).str.lower().isin(["true", "1", "yes"])
    else:
        stops["is_critical"] = False

    if COMMUNITIES_CSV.exists():
        communities = pd.read_csv(COMMUNITIES_CSV, encoding="utf-8-sig")
        communities["stop_id"] = communities["stop_id"].astype(str)
        stops = stops.merge(
            communities[["stop_id", "community_louvain", "community_lp"]],
            on="stop_id",
            how="left",
        )
    else:
        stops["community_louvain"] = pd.NA
        stops["community_lp"] = pd.NA

    if PRIMARY_STOP_METRICS_CSV.exists():
        primary_header = pd.read_csv(PRIMARY_STOP_METRICS_CSV, nrows=0, encoding="utf-8-sig").columns
        primary_cols = [
            col
            for col in ["stop_id", "stop_use_count", "weighted_degree", "degree"]
            if col in primary_header
        ]
        primary = pd.read_csv(PRIMARY_STOP_METRICS_CSV, usecols=primary_cols, encoding="utf-8-sig")
        primary["stop_id"] = primary["stop_id"].astype(str)
        primary = primary.rename(
            columns={
                "degree": "trip_graph_degree",
                "weighted_degree": "trip_graph_weighted_degree",
            }
        )
        stops = stops.merge(primary, on="stop_id", how="left")

    if "stop_use_count" not in stops.columns:
        stops["stop_use_count"] = np.nan
    stops["has_service_count"] = stops["stop_use_count"].notna()
    stops["stop_use_count"] = pd.to_numeric(stops["stop_use_count"], errors="coerce").fillna(0)

    stops["community_louvain"] = pd.to_numeric(stops["community_louvain"], errors="coerce").fillna(-1).astype(int)
    stops["lat"] = pd.to_numeric(stops["lat"], errors="coerce")
    stops["lon"] = pd.to_numeric(stops["lon"], errors="coerce")
    return stops.dropna(subset=["lat", "lon"]).copy()


def join_stops_to_socio(stops: pd.DataFrame, socio: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    stops_gdf = gpd.GeoDataFrame(
        stops,
        geometry=gpd.points_from_xy(stops["lon"], stops["lat"]),
        crs="EPSG:4326",
    )

    socio_cols = [
        "socio_unit_id",
        "socio_locality_code",
        "socio_stat_area_code",
        "socio_locality",
        "socio_locality_en",
        "socio_population",
        "socio_cluster",
        "socio_index_value",
        "geometry",
    ]

    joined = gpd.sjoin(stops_gdf, socio[socio_cols], how="left", predicate="within")
    joined = joined[~joined.index.duplicated(keep="first")].drop(columns=["index_right"], errors="ignore")
    joined["socio_join_method"] = np.where(joined["socio_cluster"].notna(), "within", pd.NA)
    joined["socio_join_distance_m"] = np.where(joined["socio_cluster"].notna(), 0.0, np.nan)

    missing_index = joined.index[joined["socio_cluster"].isna()]
    if len(missing_index):
        missing = stops_gdf.loc[missing_index].copy()
        nearest = gpd.sjoin_nearest(
            missing.to_crs(3857),
            socio[socio_cols].to_crs(3857),
            how="left",
            max_distance=NEAREST_JOIN_MAX_DISTANCE_M,
            distance_col="socio_join_distance_m",
        )
        nearest = nearest[~nearest.index.duplicated(keep="first")].drop(columns=["index_right"], errors="ignore")
        matched_nearest = nearest.index[nearest["socio_cluster"].notna()]
        fill_cols = [col for col in socio_cols if col != "geometry"] + ["socio_join_distance_m"]
        for col in fill_cols:
            joined.loc[matched_nearest, col] = nearest.loc[matched_nearest, col]
        joined.loc[matched_nearest, "socio_join_method"] = "nearest"

    joined["socio_cluster"] = pd.to_numeric(joined["socio_cluster"], errors="coerce").astype("Int64")
    joined["socio_cluster_group"] = pd.cut(
        joined["socio_cluster"].astype("float"),
        bins=[0, 4, 7, 10],
        labels=["low_1_4", "middle_5_7", "high_8_10"],
    )
    return joined


def build_area_access(joined: pd.DataFrame, socio: gpd.GeoDataFrame) -> pd.DataFrame:
    matched = joined[joined["socio_cluster"].notna()].copy()
    matched["active_stop"] = matched["stop_use_count"] > 0

    area = (
        matched.groupby(
            [
                "socio_unit_id",
                "socio_locality",
                "socio_locality_code",
                "socio_stat_area_code",
                "socio_cluster",
            ],
            dropna=False,
        )
        .agg(
            stops=("stop_id", "count"),
            active_stops=("active_stop", "sum"),
            total_stop_use_count=("stop_use_count", "sum"),
            avg_stop_use_count=("stop_use_count", "mean"),
            median_stop_use_count=("stop_use_count", "median"),
            avg_proximity_degree=("degree", "mean"),
            critical_stops=("is_critical", "sum"),
            dominant_region=("region", mode_or_na),
            dominant_metro=("metro", mode_or_na),
            louvain_communities=("community_louvain", lambda s: s[s >= 0].nunique()),
        )
        .reset_index()
    )

    socio_lookup = socio.drop_duplicates("socio_unit_id")[
        ["socio_unit_id", "socio_population", "socio_index_value"]
    ]
    area = area.merge(socio_lookup, on="socio_unit_id", how="left")
    area["active_stop_share"] = area["active_stops"] / area["stops"]
    area["stops_per_1000_residents"] = per_1000(area["stops"], area["socio_population"])
    area["stop_use_count_per_1000_residents"] = per_1000(
        area["total_stop_use_count"], area["socio_population"]
    )
    area["stop_use_count_per_stop"] = np.where(
        area["stops"] > 0, area["total_stop_use_count"] / area["stops"], np.nan
    )
    area["critical_stop_share"] = area["critical_stops"] / area["stops"]
    return area.sort_values(["socio_cluster", "socio_locality", "socio_stat_area_code"])


def build_cluster_summary(area: pd.DataFrame) -> pd.DataFrame:
    cluster = (
        area.groupby("socio_cluster", dropna=False)
        .agg(
            socio_areas=("socio_unit_id", "count"),
            population=("socio_population", "sum"),
            stops=("stops", "sum"),
            active_stops=("active_stops", "sum"),
            total_stop_use_count=("total_stop_use_count", "sum"),
            median_area_stops_per_1000=("stops_per_1000_residents", "median"),
            median_area_stop_use_count_per_1000=("stop_use_count_per_1000_residents", "median"),
            mean_area_proximity_degree=("avg_proximity_degree", "mean"),
            mean_area_critical_stop_share=("critical_stop_share", "mean"),
        )
        .reset_index()
    )
    cluster["active_stop_share"] = cluster["active_stops"] / cluster["stops"]
    cluster["stops_per_1000_residents"] = per_1000(cluster["stops"], cluster["population"])
    cluster["stop_use_count_per_1000_residents"] = per_1000(
        cluster["total_stop_use_count"], cluster["population"]
    )
    cluster["stop_use_count_per_stop"] = np.where(
        cluster["stops"] > 0, cluster["total_stop_use_count"] / cluster["stops"], np.nan
    )
    return cluster.sort_values("socio_cluster")


def build_community_summary(joined: pd.DataFrame) -> pd.DataFrame:
    matched = joined[(joined["socio_cluster"].notna()) & (joined["community_louvain"] >= 0)].copy()
    matched["low_socio_stop"] = matched["socio_cluster"] <= 4
    matched["active_stop"] = matched["stop_use_count"] > 0

    community = (
        matched.groupby("community_louvain")
        .agg(
            stops=("stop_id", "count"),
            active_stops=("active_stop", "sum"),
            total_stop_use_count=("stop_use_count", "sum"),
            avg_stop_use_count=("stop_use_count", "mean"),
            avg_proximity_degree=("degree", "mean"),
            avg_socio_cluster=("socio_cluster", "mean"),
            median_socio_cluster=("socio_cluster", "median"),
            dominant_socio_cluster=("socio_cluster", mode_or_na),
            low_socio_stop_share=("low_socio_stop", "mean"),
            dominant_region=("region", mode_or_na),
            dominant_metro=("metro", mode_or_na),
            socio_areas=("socio_unit_id", "nunique"),
        )
        .reset_index()
    )

    population = (
        matched.drop_duplicates(["community_louvain", "socio_unit_id"])
        .groupby("community_louvain")["socio_population"]
        .sum()
        .rename("covered_population_estimate")
        .reset_index()
    )
    community = community.merge(population, on="community_louvain", how="left")
    community["active_stop_share"] = community["active_stops"] / community["stops"]
    community["stops_per_1000_residents"] = per_1000(
        community["stops"], community["covered_population_estimate"]
    )
    community["stop_use_count_per_1000_residents"] = per_1000(
        community["total_stop_use_count"], community["covered_population_estimate"]
    )
    return community.sort_values("stops", ascending=False)


def spearman_rows(area: pd.DataFrame, joined: pd.DataFrame) -> pd.DataFrame:
    try:
        from scipy.stats import spearmanr
    except ImportError:
        spearmanr = None

    rows = []
    definitions = [
        (
            "statistical_area",
            area,
            [
                "stops_per_1000_residents",
                "stop_use_count_per_1000_residents",
                "stop_use_count_per_stop",
                "avg_proximity_degree",
                "critical_stop_share",
            ],
        ),
        (
            "stop",
            joined[joined["socio_cluster"].notna()],
            ["stop_use_count", "degree", "is_critical"],
        ),
    ]

    for scope, df, metrics in definitions:
        for metric in metrics:
            sample = df[["socio_cluster", metric]].dropna()
            if len(sample) < 3 or sample["socio_cluster"].nunique() < 2:
                rho, p_value = np.nan, np.nan
            elif spearmanr:
                rho, p_value = spearmanr(sample["socio_cluster"], sample[metric])
            else:
                rho = sample["socio_cluster"].corr(sample[metric], method="spearman")
                p_value = np.nan
            rows.append(
                {
                    "scope": scope,
                    "metric": metric,
                    "spearman_rho": rho,
                    "p_value": p_value,
                    "n": len(sample),
                }
            )
    return pd.DataFrame(rows)


def join_quality(joined: pd.DataFrame) -> dict:
    total = len(joined)
    within = int((joined["socio_join_method"] == "within").sum())
    nearest = int((joined["socio_join_method"] == "nearest").sum())
    unmatched = int(joined["socio_join_method"].isna().sum())
    nearest_dist = joined.loc[joined["socio_join_method"] == "nearest", "socio_join_distance_m"]
    return {
        "total_stops": total,
        "matched_within_polygon": within,
        "matched_by_nearest_polygon": nearest,
        "unmatched": unmatched,
        "match_rate_pct": round((within + nearest) / total * 100, 2) if total else 0,
        "nearest_join_max_distance_m": NEAREST_JOIN_MAX_DISTANCE_M,
        "nearest_join_median_distance_m": None
        if nearest_dist.empty
        else round(float(nearest_dist.median()), 1),
        "nearest_join_max_observed_distance_m": None
        if nearest_dist.empty
        else round(float(nearest_dist.max()), 1),
        "cbs_layer": CBS_LAYER_URL,
    }


def plot_cluster_access(cluster: pd.DataFrame) -> None:
    data = cluster.dropna(subset=["socio_cluster"]).copy()
    data["socio_cluster"] = data["socio_cluster"].astype(int)
    palette = sns.color_palette("crest", n_colors=len(data))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.barplot(
        data=data,
        x="socio_cluster",
        y="stops_per_1000_residents",
        palette=palette,
        hue="socio_cluster",
        legend=False,
        ax=axes[0],
    )
    axes[0].set_title("Stops per 1,000 residents")
    axes[0].set_xlabel("CBS socioeconomic cluster")
    axes[0].set_ylabel("Stops / 1,000 residents")

    sns.barplot(
        data=data,
        x="socio_cluster",
        y="stop_use_count_per_1000_residents",
        palette=palette,
        hue="socio_cluster",
        legend=False,
        ax=axes[1],
    )
    axes[1].set_title("Scheduled stop-use count per 1,000 residents")
    axes[1].set_xlabel("CBS socioeconomic cluster")
    axes[1].set_ylabel("Stop-use count / 1,000 residents")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "socioeconomic_access_by_cluster.png", dpi=160)
    plt.close()


def plot_stop_use_boxplot(joined: pd.DataFrame) -> None:
    data = joined[joined["socio_cluster"].notna()].copy()
    data["socio_cluster"] = data["socio_cluster"].astype(int)
    data["log_stop_use_count"] = np.log1p(data["stop_use_count"])

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(
        data=data,
        x="socio_cluster",
        y="log_stop_use_count",
        hue="socio_cluster",
        palette="viridis",
        legend=False,
        showfliers=False,
        ax=ax,
    )
    ax.set_title("Distribution of station service counts by socioeconomic cluster")
    ax.set_xlabel("CBS socioeconomic cluster")
    ax.set_ylabel("log(1 + stop_use_count)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "socioeconomic_stop_use_boxplot.png", dpi=160)
    plt.close()


def plot_community_access(community: pd.DataFrame) -> None:
    data = community.dropna(subset=["avg_socio_cluster", "stop_use_count_per_1000_residents"]).copy()
    if data.empty:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(
        data["avg_socio_cluster"],
        data["stop_use_count_per_1000_residents"],
        s=np.clip(data["stops"], 20, 500),
        c=data["low_socio_stop_share"],
        cmap="mako_r",
        alpha=0.75,
        edgecolor="white",
        linewidth=0.4,
    )
    ax.set_title("Louvain communities: socioeconomic level vs. transit availability")
    ax.set_xlabel("Average socioeconomic cluster in community")
    ax.set_ylabel("Stop-use count / 1,000 covered residents")
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Share of stops in clusters 1-4")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "community_socioeconomic_access.png", dpi=160)
    plt.close()


def save_outputs(
    joined: gpd.GeoDataFrame,
    area: pd.DataFrame,
    cluster: pd.DataFrame,
    community: pd.DataFrame,
    correlations: pd.DataFrame,
    quality: dict,
) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    stop_columns = [
        "stop_id",
        "stop_name",
        "region",
        "metro",
        "community_louvain",
        "lat",
        "lon",
        "degree",
        "stop_use_count",
        "has_service_count",
        "is_critical",
        "socio_join_method",
        "socio_join_distance_m",
        "socio_unit_id",
        "socio_locality",
        "socio_cluster",
        "socio_cluster_group",
        "socio_index_value",
        "socio_population",
    ]
    stop_columns = [col for col in stop_columns if col in joined.columns]
    joined[stop_columns].to_csv(OUT_DIR / "stops_with_socioeconomic.csv", index=False, encoding="utf-8-sig")
    area.to_csv(OUT_DIR / "socioeconomic_area_access.csv", index=False, encoding="utf-8-sig")
    cluster.to_csv(OUT_DIR / "socioeconomic_cluster_summary.csv", index=False, encoding="utf-8-sig")
    community.to_csv(OUT_DIR / "community_socioeconomic_summary.csv", index=False, encoding="utf-8-sig")
    correlations.to_csv(OUT_DIR / "socioeconomic_correlation_summary.csv", index=False, encoding="utf-8-sig")
    (OUT_DIR / "socioeconomic_join_quality.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    plot_cluster_access(cluster)
    plot_stop_use_boxplot(joined)
    plot_community_access(community)


def main() -> None:
    print("=== Stage 06B: socioeconomic equity analysis ===")
    stops = load_stops()
    print(f"  Loaded {len(stops):,} stops")
    socio = load_socioeconomic_areas()
    print(f"  Loaded {len(socio):,} CBS socioeconomic units")

    joined = join_stops_to_socio(stops, socio)
    quality = join_quality(joined)
    print(f"  Socioeconomic join match rate: {quality['match_rate_pct']}%")

    area = build_area_access(joined, socio)
    cluster = build_cluster_summary(area)
    community = build_community_summary(joined)
    correlations = spearman_rows(area, joined)
    save_outputs(joined, area, cluster, community, correlations, quality)

    print("\nKey Spearman correlations:")
    print(correlations.to_string(index=False))
    print(f"\nOutputs saved to:\n  {OUT_DIR}\n  {FIG_DIR}")


if __name__ == "__main__":
    main()

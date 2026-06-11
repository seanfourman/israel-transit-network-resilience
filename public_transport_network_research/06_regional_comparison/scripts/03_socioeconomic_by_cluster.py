"""
Stage 06C -- within-cluster socioeconomic equity analysis.

Motivation
----------
Stage 06B (``02_socioeconomic_equity.py``) joined every stop to its CBS 2021
socioeconomic statistical area and concluded, at the *national* level, that
transit availability barely depends on socioeconomic cluster (pooled Spearman
rho ~ -0.15). That national average is misleading: it pools dense metropolitan
areas with sparse periphery, so opposite local gaps cancel out (a Simpson's
paradox). It was also computed against a *stale, partial* community assignment
(only ~4,500 Tel-Aviv-area stops carried a community), so the per-community
equity table was not trustworthy.

This script fixes both problems, fully offline, from files that already exist:

1. Re-merge the **correct** Louvain community assignment from stage 07
   (``07_community_detection/outputs/community_assignments.csv``, full coverage,
   ~30k stops / 74 communities).
2. Aggregate stops to the CBS statistical area ("neighborhood") level, because
   the socioeconomic cluster is an attribute of the statistical area; the
   neighborhood is the clean unit of analysis for a per-capita equity test.
3. For each major cluster, measure the **within-cluster** relationship between
   socioeconomic cluster and transit availability (Spearman), and contrast it
   with the flat national pooled value.
4. Regenerate a corrected ``community_socioeconomic_summary.csv``.

No network access is required: the spatial join was already done in stage 06B
and is read from ``stops_with_socioeconomic.csv``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _hebrew_bidi import install_hebrew

install_hebrew()
import matplotlib.pyplot as plt
import seaborn as sns

try:
    from scipy.stats import spearmanr
except ImportError:  # pragma: no cover - scipy is in requirements
    spearmanr = None

ROOT = Path(__file__).resolve().parents[3]
STAGE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = STAGE_DIR / "outputs"
FIG_DIR = ROOT / "public_transport_network_research/figures/06_regional_comparison"

STOPS_SOCIO_CSV = OUT_DIR / "stops_with_socioeconomic.csv"
COMMUNITIES_CSV = ROOT / "public_transport_network_research/07_community_detection/outputs/community_assignments.csv"

# A cluster needs enough socioeconomically varied neighborhoods for an honest
# within-cluster correlation. These thresholds keep the test meaningful.
MIN_NEIGHBORHOODS = 12
MIN_DISTINCT_CLUSTERS = 3
TOP_CLUSTERS_FOR_FIGURE = 15
# For the bar figure, require a slightly larger sample so the headline ranking is
# not dominated by tiny clusters; the underlying table keeps every major cluster.
FIG_MIN_NEIGHBORHOODS = 20

sns.set_theme(style="whitegrid", font_scale=1.0)


def spearman(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    sample = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(sample) < 8 or sample["x"].nunique() < 2 or sample["y"].nunique() < 2:
        return np.nan, np.nan
    if spearmanr is not None:
        rho, p = spearmanr(sample["x"], sample["y"])
        return float(rho), float(p)
    return float(sample["x"].corr(sample["y"], method="spearman")), np.nan


def mode_or_na(series: pd.Series):
    values = series.dropna()
    return values.mode().iloc[0] if not values.empty else pd.NA


def load_stops_with_correct_communities() -> pd.DataFrame:
    stops = pd.read_csv(STOPS_SOCIO_CSV, encoding="utf-8-sig")
    stops["stop_id"] = stops["stop_id"].astype(str)

    stale_cov = (
        (pd.to_numeric(stops.get("community_louvain"), errors="coerce") >= 0).mean()
        if "community_louvain" in stops.columns
        else 0.0
    )

    communities = pd.read_csv(COMMUNITIES_CSV, encoding="utf-8-sig")
    communities["stop_id"] = communities["stop_id"].astype(str)
    stops = stops.drop(columns=["community_louvain"], errors="ignore").merge(
        communities[["stop_id", "community_louvain"]], on="stop_id", how="left"
    )
    # community_louvain == -1 marks stops Louvain left unassigned (226 stops,
    # ~0.7%); it is not a real community, so treat it as missing. The real count
    # is 73 communities, matching community_summary.csv and slide 10.
    stops.loc[stops["community_louvain"] == -1, "community_louvain"] = np.nan
    fresh_cov = (stops["community_louvain"].notna()).mean()
    print(
        f"  Community coverage: stale file {stale_cov:5.1%} -> re-merged {fresh_cov:5.1%} "
        f"({stops['community_louvain'].notna().sum():,} stops, "
        f"{stops['community_louvain'].dropna().nunique()} communities)"
    )

    stops["socio_cluster"] = pd.to_numeric(stops["socio_cluster"], errors="coerce")
    stops["socio_population"] = pd.to_numeric(stops["socio_population"], errors="coerce")
    stops["stop_use_count"] = pd.to_numeric(stops.get("stop_use_count"), errors="coerce").fillna(0)
    return stops[stops["socio_cluster"].notna() & stops["community_louvain"].notna()].copy()


def build_neighborhoods(stops: pd.DataFrame) -> pd.DataFrame:
    """Aggregate stops to CBS statistical area (neighborhood); the cluster is an
    attribute of the area, so this removes pseudo-replication from many stops in
    one area and gives a clean per-capita equity unit."""
    nb = (
        stops.groupby("socio_unit_id")
        .agg(
            socio_cluster=("socio_cluster", "first"),
            population=("socio_population", "first"),
            stops=("stop_id", "count"),
            total_stop_use=("stop_use_count", "sum"),
            community=("community_louvain", mode_or_na),
            city=("socio_locality", mode_or_na),
            region=("region", mode_or_na),
            metro=("metro", mode_or_na),
        )
        .reset_index()
    )
    nb["community"] = pd.to_numeric(nb["community"], errors="coerce").astype("Int64")
    nb["stop_use_per_1000"] = np.where(
        nb["population"] > 0, nb["total_stop_use"] / nb["population"] * 1000, np.nan
    )
    nb["stops_per_1000"] = np.where(
        nb["population"] > 0, nb["stops"] / nb["population"] * 1000, np.nan
    )
    return nb


def within_cluster_correlations(nb: pd.DataFrame, stops: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for community, group in nb.groupby("community"):
        if pd.isna(community):
            continue
        group = group.dropna(subset=["socio_cluster"])
        if len(group) < MIN_NEIGHBORHOODS or group["socio_cluster"].nunique() < MIN_DISTINCT_CLUSTERS:
            continue

        rho_use, p_use = spearman(group["socio_cluster"], group["stop_use_per_1000"])
        rho_stops, p_stops = spearman(group["socio_cluster"], group["stops_per_1000"])
        stop_group = stops[stops["community_louvain"] == community]
        rho_stop_level, p_stop_level = spearman(
            stop_group["socio_cluster"], stop_group["stop_use_count"]
        )

        rows.append(
            {
                "community_louvain": int(community),
                "dominant_city": mode_or_na(group["city"]),
                "dominant_region": mode_or_na(group["region"]),
                "dominant_metro": mode_or_na(group["metro"]),
                "n_neighborhoods": len(group),
                "n_stops": int(stop_group.shape[0]),
                "population": float(group["population"].sum()),
                "mean_socio_cluster": float(group["socio_cluster"].mean()),
                "socio_cluster_spread": int(group["socio_cluster"].nunique()),
                "rho_use_per_capita": rho_use,
                "p_use_per_capita": p_use,
                "rho_stops_per_capita": rho_stops,
                "p_stops_per_capita": p_stops,
                "rho_stop_level_use": rho_stop_level,
                "p_stop_level_use": p_stop_level,
            }
        )
    out = pd.DataFrame(rows)
    out["abs_rho"] = out["rho_use_per_capita"].abs()
    out["significant_05"] = out["p_use_per_capita"] < 0.05
    return out.sort_values("rho_use_per_capita")


def corrected_community_summary(stops: pd.DataFrame, nb: pd.DataFrame) -> pd.DataFrame:
    stops = stops.copy()
    stops["low_socio_stop"] = stops["socio_cluster"] <= 4
    stops["active_stop"] = stops["stop_use_count"] > 0
    community = (
        stops.groupby("community_louvain")
        .agg(
            stops=("stop_id", "count"),
            active_stops=("active_stop", "sum"),
            total_stop_use_count=("stop_use_count", "sum"),
            avg_stop_use_count=("stop_use_count", "mean"),
            avg_socio_cluster=("socio_cluster", "mean"),
            median_socio_cluster=("socio_cluster", "median"),
            dominant_socio_cluster=("socio_cluster", mode_or_na),
            low_socio_stop_share=("low_socio_stop", "mean"),
            dominant_city=("socio_locality", mode_or_na),
            dominant_region=("region", mode_or_na),
            dominant_metro=("metro", mode_or_na),
            socio_areas=("socio_unit_id", "nunique"),
        )
        .reset_index()
    )
    pop = (
        nb.dropna(subset=["community"])
        .groupby("community")["population"]
        .sum()
        .rename("covered_population_estimate")
        .reset_index()
        .rename(columns={"community": "community_louvain"})
    )
    community = community.merge(pop, on="community_louvain", how="left")
    community["active_stop_share"] = community["active_stops"] / community["stops"]
    return community.sort_values("stops", ascending=False)


def national_baseline(nb: pd.DataFrame, stops: pd.DataFrame) -> dict:
    rho_nb, p_nb = spearman(nb["socio_cluster"], nb["stop_use_per_1000"])
    rho_stop, p_stop = spearman(stops["socio_cluster"], stops["stop_use_count"])
    return {
        "national_neighborhood_rho_use_per_capita": rho_nb,
        "national_neighborhood_p": p_nb,
        "national_neighborhood_n": int(nb["stop_use_per_1000"].notna().sum()),
        "national_stop_rho_use": rho_stop,
        "national_stop_n": int(len(stops)),
    }


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def plot_within_cluster_bars(corr: pd.DataFrame, national_rho: float) -> Path:
    data = corr.dropna(subset=["rho_use_per_capita"]).copy()
    data = data[data["n_neighborhoods"] >= FIG_MIN_NEIGHBORHOODS]
    data = data.reindex(data["abs_rho"].sort_values(ascending=False).index)
    data = data.head(TOP_CLUSTERS_FOR_FIGURE).copy()
    # Plot the equity *direction*, not the raw sign: equity_bias = -rho, so a
    # positive value means service leans toward the weaker neighborhoods (the
    # equitable, intuitive "green / plus / right" direction).
    data["equity_bias"] = -data["rho_use_per_capita"]
    data = data.sort_values("equity_bias")

    labels = [
        f"{city}  ({n} שכונות)"
        for city, n in zip(data["dominant_city"], data["n_neighborhoods"])
    ]
    colors = ["#1e8449" if v > 0 else "#c0392b" for v in data["equity_bias"]]

    lo = float(data["equity_bias"].min())
    hi = float(data["equity_bias"].max())
    plt.rcParams.update({"font.size": 13})
    fig, ax = plt.subplots(figsize=(12, 7.5))
    y = np.arange(len(data))
    bars = ax.barh(y, data["equity_bias"], color=colors, edgecolor="white")
    # Non-significant clusters are drawn faded, so significance is read straight
    # off the bar instead of from an asterisk that needs decoding.
    for bar, sig in zip(bars, data["significant_05"]):
        if not sig:
            bar.set_alpha(0.40)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12)
    ax.axvline(0, color="#555555", linewidth=1)
    national_bias = -national_rho
    ax.axvline(
        national_bias,
        color="#2471a3",
        linestyle="--",
        linewidth=2.5,
        label=f"ממוצע ארצי = {national_bias:.2f}",
    )
    for yi, v in enumerate(data["equity_bias"]):
        ax.text(
            v + (0.015 if v >= 0 else -0.015),
            yi,
            f"{v:+.2f}",
            va="center",
            ha="left" if v >= 0 else "right",
            fontsize=11,
            fontweight="bold",
        )
    ax.set_xlabel("הטיית השירות לטובת השכונות החלשות  (חיובי = שוויוני)", fontsize=13)
    ax.set_title(
        "פער השירות הסוציו-אקונומי משתנה מקלאסטר לקלאסטר\n(ירוק = שכונות חלשות מקבלות יותר שירות, אדום = שכונות חזקות מקבלות יותר)",
        fontsize=15, pad=12,
    )
    ax.set_xlim(lo - 0.17, hi + 0.13)
    ax.legend(loc="lower right", fontsize=12)
    ax.text(
        0.02, 0.95,
        "עמודה חיוורת = הקשר אינו מובהק (p>0.05)",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=14, color="#444444",
        bbox=dict(boxstyle="round,pad=0.4", fc="#f4f4f4", ec="#cccccc", lw=1.0),
    )
    plt.tight_layout()
    path = FIG_DIR / "socioeconomic_within_cluster_correlation.png"
    plt.savefig(path, dpi=160)
    plt.close()
    plt.rcParams.update({"font.size": 10})
    return path


def plot_cluster_average_flat(community: pd.DataFrame) -> Path:
    """Step A of the story: check each cluster by its *average* socioeconomic
    level vs its average service. This stays weak and non-significant, because a
    whole-cluster average blends strong and weak neighborhoods together."""
    data = community.copy()
    data["use_per_1000"] = np.where(
        data["covered_population_estimate"] > 0,
        data["total_stop_use_count"] / data["covered_population_estimate"] * 1000,
        np.nan,
    )
    data = data.dropna(subset=["avg_socio_cluster", "use_per_1000"])

    y_cap = float(np.nanpercentile(data["use_per_1000"], 95))
    plt.rcParams.update({"font.size": 14})
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.scatter(
        data["avg_socio_cluster"],
        data["use_per_1000"],
        s=np.clip(data["stops"], 30, 600),
        alpha=0.55,
        color="#34557a",
        edgecolor="white",
        linewidth=0.6,
    )
    fit = data[data["use_per_1000"] <= y_cap]
    if fit["avg_socio_cluster"].nunique() >= 2:
        coef = np.polyfit(fit["avg_socio_cluster"], fit["use_per_1000"], 1)
        xs = np.array([data["avg_socio_cluster"].min(), data["avg_socio_cluster"].max()])
        ax.plot(xs, np.polyval(coef, xs), color="#c0392b", linewidth=3, linestyle="--")
    ax.set_ylim(0, 1.05 * y_cap)
    ax.set_title(
        f"כל נקודה = קלאסטר אחד ({len(data)} קהילות)",
        fontsize=18, fontweight="bold", pad=14,
    )
    ax.set_xlabel("מעמד סוציו-אקונומי ממוצע של הקלאסטר  (1 = חלש, 10 = חזק)", fontsize=14)
    ax.set_ylabel("שירות לנפש (מופעי עצירה / 1,000)", fontsize=14)
    ax.annotate(
        "גודל הנקודה = מספר התחנות בקלאסטר",
        xy=(0.97, 0.95), xycoords="axes fraction", ha="right", va="top",
        fontsize=16, color="#333333",
        bbox=dict(boxstyle="round,pad=0.5", fc="#f4f4f4", ec="#bbbbbb", lw=1.0),
    )
    plt.tight_layout()
    path = FIG_DIR / "socioeconomic_cluster_average_flat.png"
    plt.savefig(path, dpi=160)
    plt.close()
    plt.rcParams.update({"font.size": 10})
    return path


def plot_simpson_explainer(nb: pd.DataFrame) -> Path:
    """Dedicated Simpson's-paradox slide: two clusters with opposite within-group
    trends (Netanya down, Bet Shean up) plus the flat national pooled line. The
    steep coloured lines vs the flat black line is the paradox, made visible."""
    examples = [
        (34, "נתניה", "#2980b9"),
        (23, "בית שאן", "#e67e22"),
    ]
    plt.rcParams.update({"font.size": 14})
    fig, ax = plt.subplots(figsize=(12, 7))

    allnb = nb.dropna(subset=["socio_cluster", "stop_use_per_1000"])
    # Display and fitting cap: a few low-socio central areas have huge per-capita
    # service; trimming them keeps every line on-chart and lets each line reflect
    # the typical neighborhood, matching the rank-based (Spearman) story.
    y_cap = float(np.nanpercentile(allnb["stop_use_per_1000"], 90))

    def robust_line(frame):
        f = frame[frame["stop_use_per_1000"] <= y_cap]
        return np.polyfit(f["socio_cluster"], f["stop_use_per_1000"], 1)

    xs = np.array([1, 10])
    ax.plot(xs, np.polyval(robust_line(allnb), xs), color="#222222", linewidth=3.5,
            linestyle="--", label="ארצי - המגמות מתקזזות", zorder=5)

    for comm, name, color in examples:
        g = nb[nb["community"] == comm].dropna(subset=["socio_cluster", "stop_use_per_1000"])
        g_show = g[g["stop_use_per_1000"] <= y_cap]
        ax.scatter(g_show["socio_cluster"], g_show["stop_use_per_1000"], s=70, alpha=0.55,
                   color=color, edgecolor="white", linewidth=0.5, zorder=3)
        gx = np.array([g["socio_cluster"].min(), g["socio_cluster"].max()])
        ax.plot(gx, np.polyval(robust_line(g), gx), color=color, linewidth=4.5,
                label=f"{name}", zorder=4)

    ax.set_ylim(0, 1.05 * y_cap)
    ax.set_xlim(0.5, 10.5)
    ax.set_xlabel("מעמד סוציו-אקונומי של השכונה  (1 = חלש, 10 = חזק)", fontsize=14)
    ax.set_ylabel("שירות לנפש (מופעי עצירה / 1,000)", fontsize=14)
    ax.set_title(
        "אותה מדינה, מסקנה הפוכה בכל עיר\n"
        "בנתניה: חזק = פחות שירות. בבית שאן: חזק = יותר. ארצית הן מתבטלות",
        fontsize=15, fontweight="bold", pad=12,
    )
    ax.legend(loc="upper right", fontsize=13, frameon=True, title="קו מגמה בתוך:")
    plt.tight_layout()
    path = FIG_DIR / "socioeconomic_simpson_paradox.png"
    plt.savefig(path, dpi=160)
    plt.close()
    plt.rcParams.update({"font.size": 10})
    return path


def plot_named_cities_flat(community: pd.DataFrame) -> Path:
    """Slide A visual: a few recognizable cities ordered by wealth, with jumpy
    service bars -> wealth does not predict service at the cluster level. Carries
    the overall (non-significant) rho/p as the statistical backing."""
    community = community.copy()
    community["use_per_1000"] = np.where(
        community["covered_population_estimate"] > 0,
        community["total_stop_use_count"] / community["covered_population_estimate"] * 1000,
        np.nan,
    )
    rho, p = spearman(community["avg_socio_cluster"], community["use_per_1000"])

    show = ["אופקים", "קריית גת", "נתניה", "ראשון לציון", "כפר סבא", "רמת גן"]
    d = (
        community[community["dominant_city"].isin(show)]
        .drop_duplicates("dominant_city")
        .set_index("dominant_city")
        .reindex(show)
        .reset_index()
        .sort_values("avg_socio_cluster")
    )

    plt.rcParams.update({"font.size": 14})
    fig, ax = plt.subplots(figsize=(12, 7))
    norm = plt.Normalize(1, 10)
    colors = plt.cm.RdYlGn(norm(d["avg_socio_cluster"]))
    bars = ax.bar(range(len(d)), d["use_per_1000"], color=colors, edgecolor="#333333", linewidth=0.8)
    ax.set_xticks(range(len(d)))
    ax.set_xticklabels(
        [f"{c}\n(מעמד {s:.0f})" for c, s in zip(d["dominant_city"], d["avg_socio_cluster"])],
        fontsize=13,
    )
    for bar, val in zip(bars, d["use_per_1000"]):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 40, f"{val:,.0f}",
                ha="center", va="bottom", fontsize=13, fontweight="bold")
    ax.set_ylabel("שירות לנפש (מופעי עצירה / 1,000)", fontsize=14)
    ax.set_title("מסודרות מהענייה לעשירה - אבל גובה השירות קופץ בלי חוק",
                 fontsize=16, fontweight="bold", pad=14)
    ax.annotate(
        f"מעמד לא מנבא שירות\nrho = {rho:.2f},  p = {p:.2f}  (לא מובהק)",
        xy=(0.97, 0.95), xycoords="axes fraction", ha="right", va="top",
        fontsize=15, fontweight="bold", color="#c0392b",
        bbox=dict(boxstyle="round,pad=0.5", fc="#fdecea", ec="#c0392b", lw=1.5),
    )
    ax.margins(y=0.18)
    plt.tight_layout()
    path = FIG_DIR / "socioeconomic_cities_no_rule.png"
    plt.savefig(path, dpi=160)
    plt.close()
    plt.rcParams.update({"font.size": 10})
    return path


def plot_example_scatters(nb: pd.DataFrame, corr: pd.DataFrame) -> Path:
    # Use large-sample clusters for the scatter so each panel is defensible, and
    # show the full spread: strong negative, near-zero, strong positive.
    big = corr.dropna(subset=["rho_use_per_capita"])
    big = big[big["n_neighborhoods"] >= 40].sort_values("rho_use_per_capita")
    most_negative = big.iloc[0]
    most_positive = big.iloc[-1]
    near_zero = big.reindex(big["rho_use_per_capita"].abs().sort_values().index).iloc[0]
    picks = [most_negative, near_zero, most_positive]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), sharey=False)
    for ax, row in zip(axes, picks):
        g = nb[nb["community"] == row["community_louvain"]].dropna(
            subset=["socio_cluster", "stop_use_per_1000"]
        )
        # Clip the y-axis to the 97th percentile so a single central-station
        # outlier does not flatten the visible relationship.
        y_cap = float(np.nanpercentile(g["stop_use_per_1000"], 97))
        ax.scatter(
            g["socio_cluster"],
            g["stop_use_per_1000"],
            s=np.clip(g["population"] / 200, 12, 240),
            alpha=0.65,
            color="#2c3e50",
            edgecolor="white",
            linewidth=0.4,
        )
        if g["socio_cluster"].nunique() >= 2:
            coef = np.polyfit(g["socio_cluster"], g["stop_use_per_1000"], 1)
            xs = np.array([g["socio_cluster"].min(), g["socio_cluster"].max()])
            ax.plot(xs, np.polyval(coef, xs), color="#c0392b", linewidth=2)
        ax.set_ylim(-0.05 * y_cap, 1.08 * y_cap)
        ax.set_title(
            f"{row['dominant_city']}  |  rho = {row['rho_use_per_capita']:.2f}"
            f"{'*' if row['significant_05'] else ''}  (n={int(row['n_neighborhoods'])})",
            fontsize=12,
        )
        ax.set_xlabel("אשכול סוציו-אקונומי (1=חלש, 10=חזק)")
        ax.set_ylabel("מופעי שירות לנפש (per 1,000)")
    fig.suptitle("בתוך מטרופולין בודד: שכונות חזקות מול חלשות ורמת השירות", fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    path = FIG_DIR / "socioeconomic_within_cluster_examples.png"
    plt.savefig(path, dpi=160)
    plt.close()
    return path


def main() -> None:
    print("=== Stage 06C: within-cluster socioeconomic equity ===")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    stops = load_stops_with_correct_communities()
    nb = build_neighborhoods(stops)
    print(f"  Neighborhoods (CBS statistical areas): {len(nb):,}")

    corr = within_cluster_correlations(nb, stops)
    baseline = national_baseline(nb, stops)
    community = corrected_community_summary(stops, nb)

    nb.to_csv(OUT_DIR / "socioeconomic_neighborhood_access.csv", index=False, encoding="utf-8-sig")
    corr.to_csv(OUT_DIR / "socioeconomic_within_cluster_correlation.csv", index=False, encoding="utf-8-sig")
    community.to_csv(OUT_DIR / "community_socioeconomic_summary.csv", index=False, encoding="utf-8-sig")
    (OUT_DIR / "socioeconomic_within_cluster_baseline.json").write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    fig0 = plot_cluster_average_flat(community)
    figA = plot_named_cities_flat(community)
    fig1 = plot_within_cluster_bars(corr, baseline["national_neighborhood_rho_use_per_capita"])
    fig2 = plot_example_scatters(nb, corr)
    fig3 = plot_simpson_explainer(nb)

    valid = corr.dropna(subset=["rho_use_per_capita"])
    n_sig = int(valid["significant_05"].sum())
    print("\n--- Findings ---")
    print(
        f"  National pooled neighborhood rho(socio, service/capita) = "
        f"{baseline['national_neighborhood_rho_use_per_capita']:.3f} "
        f"(n={baseline['national_neighborhood_n']:,})"
    )
    print(
        f"  Within-cluster rho spans {valid['rho_use_per_capita'].min():.2f} .. "
        f"{valid['rho_use_per_capita'].max():.2f} over {len(valid)} major clusters; "
        f"{n_sig} significant at p<0.05"
    )
    print("\n  Strongest local gaps (most negative rho):")
    print(
        valid.head(5)[
            ["dominant_city", "dominant_region", "n_neighborhoods", "rho_use_per_capita", "p_use_per_capita"]
        ].to_string(index=False)
    )
    print("\n  Opposite direction (most positive rho):")
    print(
        valid.tail(3)[
            ["dominant_city", "dominant_region", "n_neighborhoods", "rho_use_per_capita", "p_use_per_capita"]
        ].to_string(index=False)
    )
    print(f"\n  Figures: {fig0.name}, {fig1.name}, {fig2.name}")
    print(f"  Outputs in: {OUT_DIR}")


if __name__ == "__main__":
    main()

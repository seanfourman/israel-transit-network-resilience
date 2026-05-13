# Critical Stations in Israel Public Transportation

Project title: תחנות קריטיות: ניתוח מרכזיות ועמידות ברשת התחבורה הציבורית בישראל

This repository analyzes Israel's public transportation GTFS feed as a graph:

- nodes are public-transport stops
- directed edges connect consecutive stops within each scheduled trip
- edge weight is the number of scheduled trip segments using that stop-to-stop connection

The goal is to identify critical stations using centrality metrics and test network resilience under targeted stop removals.

## Repository Structure

```text
israel-public-transportation/     GTFS data files
src/transit_network_analysis.py   Reusable analysis pipeline and CLI
notebooks/critical_stations_analysis.ipynb
outputs/                          Generated tables and figures
docs/                             Course instructions and reference material
reports/                          Final report and guideline compliance notes
```

## Setup

Install Git LFS first if needed, then hydrate the large GTFS files:

```powershell
git lfs pull
```

Create an environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The pipeline uses only the standard GTFS text files in `israel-public-transportation/`.

## Run The Full Analysis

```powershell
python src\transit_network_analysis.py `
  --data-dir israel-public-transportation `
  --output-dir outputs `
  --betweenness-samples 128 `
  --resilience-removals 500 `
  --resilience-steps 25 `
  --random-trials 5
```

For a faster smoke run, lower `--betweenness-samples` and `--random-trials`.

## Outputs

Main tables:

- `outputs/tables/network_summary.csv`
- `outputs/tables/gtfs_graph_build_summary.csv`
- `outputs/tables/stop_metrics.csv`
- `outputs/tables/top_degree_stops.csv`
- `outputs/tables/top_weighted_degree_stops.csv`
- `outputs/tables/top_pagerank_stops.csv`
- `outputs/tables/top_approx_betweenness_stops.csv`
- `outputs/tables/top_articulation_points.csv`
- `outputs/tables/top_bridges.csv`
- `outputs/tables/resilience_random_vs_targeted.csv`
- `outputs/tables/community_summary.csv`
- `outputs/tables/centrality_correlation_spearman.csv`

Main figures:

- `outputs/figures/top_weighted_degree_stops.png`
- `outputs/figures/top_pagerank_stops.png`
- `outputs/figures/route_type_distribution.png`
- `outputs/figures/top_communities.png`
- `outputs/figures/resilience_curve.png`
- `outputs/figures/active_stops_map.png`

## Final Report

The Hebrew final-report draft is in:

- `reports/final_report_he.md`
- `reports/final_report_he.docx`

The course-guideline coverage checklist is in:

- `reports/guidelines_compliance.md`

The 10-slide presentation outline is in:

- `reports/presentation_outline_he.md`

To rebuild the Word document from the Markdown source:

```powershell
python reports\build_report_docx.py
```

## Analysis Notes

`stop_times.txt` is streamed row by row because it is large. The GTFS feed is assumed to be ordered by `trip_id` and `stop_sequence`, which allows consecutive rows from the same trip to define graph edges without loading the full table into memory.

Exact betweenness centrality is expensive on a national network, so the pipeline computes approximate betweenness on the largest connected component using sampled source nodes. Increase `--betweenness-samples` for a more stable estimate.

Resilience is measured by removing stops according to centrality rankings and tracking the size of the largest connected component. A random-removal mean is included as a baseline.

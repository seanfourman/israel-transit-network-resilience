# Critical Stations in Israel Public Transportation

Project title: תחנות קריטיות: ניתוח מרכזיות ועמידות ברשת התחבורה הציבורית בישראל

Decoded project title: תחנות קריטיות: ניתוח מרכזיות ועמידות ברשת התחבורה הציבורית בישראל

This repository analyzes Israel's public transportation GTFS feed as a graph.
The primary final-project analysis is the GTFS trip-adjacency graph:

- nodes are public-transport stops
- directed edges connect consecutive stops within each scheduled trip
- edge weight is the number of scheduled trip segments using that stop-to-stop connection

The goal is to identify critical stations using centrality metrics and test network resilience under targeted stop removals.

The repository also contains a staged research pipeline under
`public_transport_network_research/`. Its `02_graph_construction` stage builds
the same GTFS trip-adjacency graph, which is why both pipelines agree on the
network structure (900 articulation points, 971 bridges). This staged pipeline
is the source of the June final-presentation figures — specifically the
critical-station isolation test (`04_centrality_analysis`) and the
socioeconomic-equity analysis (`06_regional_comparison`).

An earlier 500-meter stop-proximity graph was retired and removed: it connected
stops by geographic distance alone, regardless of whether any service linked
them, and it is not the source of any checked-in result.

## Repository Structure

```text
israel-public-transportation/      GTFS data files
src/transit_network_analysis.py    Canonical analysis pipeline and CLI (final report)
src/rail_network_analysis.py       Rail-only (route_type=2) resilience analysis
src/rail_socioeconomic_analysis.py Rail centrality vs CBS socioeconomic clusters
public_transport_network_research/ Staged research pipeline (presentation figures)
public_transport_network_notebooks/ Narrated notebook walkthrough (stages 01-10)
notebooks/critical_stations_analysis.ipynb
outputs/                           Generated tables and figures
outputs/rail/                      Rail-only tables and figures
docs/Presentation/                 Final presentation deck and slide figures
docs/Graph_Algo_project_guidelines_2026.pdf   Course project brief
reports/                           Final report and guideline compliance notes
```

## Setup

All GTFS files needed by the analysis ship with this repository **except**
`stop_times.txt` (816 MB), which is hosted separately and fetched on demand:

```powershell
pip install gdown
gdown 1V_yPAWXV6mGTFGrfiosah5LngcLZnviW -O israel-public-transportation/stop_times.txt
```

Most analyses do **not** need this file. The graph is already built and checked
in — `public_transport_network_research/02_graph_construction/outputs/edges.csv`
(762 KB) and `nodes.csv` (2.4 MB) are the graph. Only rebuilding the graph from
the raw feed requires `stop_times.txt`.

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
  --harmonic-samples 512 `
  --path-source-samples 128 `
  --resilience-removals 500 `
  --resilience-steps 25 `
  --accessibility-pairs 300 `
  --accessibility-removals 500 `
  --accessibility-steps 10 `
  --random-trials 5
```

For a faster smoke run, lower `--betweenness-samples`, `--harmonic-samples`,
`--path-source-samples`, `--accessibility-pairs`, and `--random-trials`.

## Run The Rail-Only Analysis

The Ministry of Transport feed also contains Israel Railways records. To build a
separate heavy-rail graph (`route_type=2`) and run exact centrality, single-station
damage, and random-versus-targeted resilience analysis:

```powershell
python src\rail_network_analysis.py `
  --data-dir israel-public-transportation `
  --output-dir outputs\rail
```

Rail tables and figures are written under `outputs/rail/`. The interpreted
results, limitations, and official data-source links are documented in
`reports/rail_network_resilience_report.md`.

To add the existing CBS 2021 socioeconomic assignments, compare all centrality
families, classify station archetypes, and generate regional/equity figures:

```powershell
python src\rail_socioeconomic_analysis.py
```

## Checked-In Outputs

The current checked-in `outputs/` directory contains the results from the latest
available full GTFS trip-adjacency run.

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

The current `src/transit_network_analysis.py` code can also produce these
additional outputs after rerunning with the large GTFS `stop_times.txt` file
downloaded via the Setup step above:

- `outputs/tables/top_approx_harmonic_stops.csv`
- `outputs/tables/degree_distribution.csv`
- `outputs/tables/network_model_comparison.csv`
- `outputs/tables/accessibility_damage_by_removal.csv`
- `outputs/figures/top_approx_harmonic_stops.png`
- `outputs/figures/accessibility_damage_curve.png`
- `outputs/figures/degree_distribution_loglog.png`
- `outputs/figures/network_model_comparison.png`

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

Harmonic centrality and global shortest-path statistics are also sampled. This keeps the run practical while still supporting the course themes of shortest paths, accessibility, and disconnected graphs.

Resilience is measured by removing stops according to centrality rankings and tracking the size of the largest connected component. A random-removal mean is included as a baseline.

Accessibility damage is measured on sampled origin-destination stop pairs by tracking which pairs remain reachable and how much shortest paths stretch after targeted removals.

The pipeline also compares the real transit graph with reference network models: Erdos-Renyi, a degree-sequence configuration model, Barabasi-Albert preferential attachment, and Watts-Strogatz small-world.

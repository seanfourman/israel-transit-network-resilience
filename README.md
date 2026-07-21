# Critical Stations in Israel Public Transportation

Project title: תחנות קריטיות: ניתוח מרכזיות ועמידות ברשת התחבורה הציבורית בישראל

Decoded project title: תחנות קריטיות: ניתוח מרכזיות ועמידות ברשת התחבורה הציבורית בישראל

This repository analyzes Israel's public transportation GTFS feed as a graph.
The primary final-project analysis is the GTFS trip-adjacency graph:

- nodes are public-transport stops
- directed edges connect consecutive stops within each scheduled trip
- edge weight is the number of scheduled trip segments using that stop-to-stop connection

The goal is to identify critical stations using centrality metrics and test network resilience under targeted stop removals.

The analysis lives entirely in the numbered notebooks under `notebooks/`.

`public_transport_network_research/` holds the earlier staged pipeline that this
series replaced. Its scripts have been removed; its stage documentation, figures
and generated tables are kept because the written report and the June
presentation cite them. Its work has been ported into the notebooks — the
critical-station isolation test into notebook 05, and the socioeconomic-equity
analysis into notebook 08.

An earlier 500-meter stop-proximity graph was retired and removed: it connected
stops by geographic distance alone, regardless of whether any service linked
them, and it is not the source of any checked-in result.

## Repository Structure

```text
notebooks/00_setup_and_data.ipynb            Environment check, GTFS download and inventory
notebooks/01_data_preparation.ipynb          Loading, cleaning, region and metro assignment
notebooks/02_graph_construction.ipynb        The trip-adjacency graph G = (V, E, W)
notebooks/03_descriptive_analysis.ipynb      Components, degree distribution, cut vertices
notebooks/04_centrality_analysis.ipynb       Degree, PageRank, betweenness, harmonic
notebooks/05_critical_station_isolation.ipynb  Do critical stations have alternatives?
notebooks/06_robustness_analysis.ipynb       Targeted vs random attack
notebooks/07_regional_comparison.ipynb       Regional and metropolitan differences
notebooks/08_socioeconomic_equity.ipynb      Service vs CBS socioeconomic cluster
notebooks/09_community_detection.ipynb       Louvain communities and inter-community links
notebooks/10_network_model_comparison.ipynb  ER / configuration / BA / Watts-Strogatz
notebooks/11_rail_network_analysis.ipynb     Heavy rail (route_type=2) only
notebooks/12_rail_socioeconomic.ipynb        Rail centrality vs socioeconomic profile
notebooks/13_embeddings_link_prediction.ipynb  Node2Vec and link prediction
notebooks/14_conclusions.ipynb               Synthesis, limitations, future work

israel-public-transportation/      GTFS data files
outputs/nb/<stage>/                Tables and figures written by the notebooks
outputs/, outputs/rail/            Earlier results cited by the written report
public_transport_network_research/ Earlier staged pipeline: docs, figures and outputs
docs/Presentation/                 Final presentation deck and slide figures
docs/Graph_Algo_project_guidelines_2026.pdf   Course project brief
reports/                           Final report and guideline compliance notes
```

The notebooks are the project. Each one is self-contained: it installs what it
needs, locates the repository (or clones it on Colab), fetches the GTFS feed on
demand, and carries its own analysis code inline. Run them in numeric order.

## Setup

All GTFS files needed by the analysis ship with this repository **except**
`stop_times.txt` (816 MB), which is hosted separately and fetched on demand:

```powershell
pip install gdown
gdown 1V_yPAWXV6mGTFGrfiosah5LngcLZnviW -O israel-public-transportation/stop_times.txt
```

You usually do not need to do this by hand: notebook `00_setup_and_data` and
notebook `02_graph_construction` download the file themselves if it is missing.

Only notebooks 00, 02 and 11 read the raw feed. Everything downstream works from
the built graph, which is checked in at
`outputs/nb/02_graph_construction/tables/` (`edges.csv` 762 KB, `nodes.csv`
2.4 MB) — so a reviewer can run notebooks 03 onwards with no download at all.

Create an environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The pipeline uses only the standard GTFS text files in `israel-public-transportation/`.

## Run The Analysis

Open the notebooks in `notebooks/` and run them in numeric order, or execute the
whole series from the command line:

```powershell
foreach ($nb in Get-ChildItem notebooks\[0-9][0-9]_*.ipynb | Sort-Object Name) {
  python -m nbconvert --to notebook --execute --inplace `
    --ExecutePreprocessor.timeout=7200 $nb.FullName
}
```

Measured runtimes on a laptop (full series, about 10 minutes):

| Notebook | Time | Notes |
|---|---|---|
| 00 setup_and_data | 10 s | downloads the feed on first run |
| 01 data_preparation | 7 s | |
| 02 graph_construction | 24 s | streams all 15.7M rows |
| 03 descriptive_analysis | 13 s | |
| 04 centrality_analysis | 92 s | sampled betweenness |
| 05 critical_station_isolation | 8 s | |
| 06 robustness_analysis | 86 s | attack simulations |
| 07 regional_comparison | 7 s | |
| 08 socioeconomic_equity | 9 s | downloads the CBS layer, then caches it |
| 09 community_detection | 43 s | Louvain plus a seed sweep |
| 10 network_model_comparison | 132 s | four null models |
| 11 rail_network_analysis | 15 s | reads the raw feed |
| 12 rail_socioeconomic | 5 s | needs 08 and 11 |
| 13 embeddings_link_prediction | 132 s | Node2Vec |
| 14 conclusions | 6 s | reads every earlier stage |

Dependencies between stages: 02 needs 01; 03-10 and 13 need 02; 08 also needs 09;
12 needs 08 and 11; 14 reads all of them and skips any stage that has not run.
Each notebook fails with an explicit message naming the notebook to run first.

Expensive steps are exposed as constants near the top of each notebook (for
example `K_BETWEENNESS`), so a faster smoke run only means lowering those.

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

These `outputs/` and `outputs/rail/` tables come from the earlier script-based
pipeline and are kept because the written report cites them. They are **not**
regenerated by the notebooks.

The notebooks write to `outputs/nb/<stage>/tables/` and
`outputs/nb/<stage>/figures/` instead, and those results are also checked in, so
every figure and table in the series can be inspected without running anything.

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

`stop_times.txt` is streamed row by row because it is large. The feed is assumed
to be ordered by `trip_id` and `stop_sequence`, so consecutive rows of the same
trip define a segment without loading the table into memory. Notebook 02 now
verifies that assumption instead of trusting it, and reports 562 `stop_sequence`
regressions across the 15.7M rows (0.004%, with no interleaved trip blocks).

Exact betweenness is expensive on a national network, so betweenness is estimated
from sampled source nodes on the largest connected component. Raise
`K_BETWEENNESS` in notebook 04 for a more stable estimate. The estimate is noisy,
so any percentile threshold built on it inherits that noise — notebook 04 reports
a stability check.

Resilience is measured by removing stops in centrality order and tracking the
largest connected component, against a random-removal baseline. Notebook 06
reports the surviving component normalized **both** by the original node count
and by the number of surviving nodes: dividing by the original count conflates
"nodes deleted" with "network fragmented", and the earlier report quoted the raw
version.

Link prediction is evaluated with the edge split performed **before** the
embeddings are trained. Training Node2Vec on the full graph and then testing on
held-out edges leaks, and inflates AUC from 0.83 to 0.99; notebook 13 reports
both, plus a hard-negative evaluation that is considerably less flattering.

Accessibility damage is measured on sampled origin-destination stop pairs by tracking which pairs remain reachable and how much shortest paths stretch after targeted removals.

The pipeline also compares the real transit graph with reference network models: Erdos-Renyi, a degree-sequence configuration model, Barabasi-Albert preferential attachment, and Watts-Strogatz small-world.

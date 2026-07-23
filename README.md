# Critical Stations in Israel Public Transportation

Project title: קריטיות תחנה כמושג תלוי-הגדרה - ניתוח רשת התחבורה הציבורית בישראל

This repository analyzes Israel's public-transportation GTFS feed as a graph. The
core analysis is the GTFS trip-adjacency graph:

- nodes are public-transport stops
- directed edges connect consecutive stops within each scheduled trip
- edge weight is the number of scheduled trip segments using that stop-to-stop
  connection

The starting question is which stations are "critical", and the main finding is
that criticality is not a single well-defined property: seven reasonable
definitions (weighted degree, betweenness, articulation, demand, transfer role,
travel-time centrality, dynamic resilience) rank stations almost independently of
one another. The notebooks build the graph, measure centrality and resilience,
compare the network against null models, and test each definition against the
others.

The analysis lives entirely in the numbered notebooks under `notebooks/`. There
is no separate library, build step, or generated report in this repository - the
notebooks are the project.

## Repository Structure

```text
README.md                          This file
requirements.txt                   Python dependencies
.gitignore
israel-public-transportation/      GTFS feed (text files)
notebooks/                         The analysis, notebooks 00–24 (run in order)
```

Running the notebooks creates an `outputs/nb/<stage>/` tree of tables and figures.
That tree is regenerated on every run and is not tracked in git.

### Notebooks

```text
00_setup_and_data              Environment check, GTFS download and inventory
01_data_preparation            Loading, cleaning, region and metro assignment
02_graph_construction          The trip-adjacency graph G = (V, E, W)
03_descriptive_analysis        Components, degree distribution, cut vertices
04_centrality_analysis         Degree, PageRank, betweenness, harmonic
05_critical_station_isolation  Do critical stations have alternatives?
06_robustness_analysis         Targeted vs random attack
07_regional_comparison         Regional and metropolitan differences
08_community_detection         Louvain communities and inter-community links
09_socioeconomic_equity        Service vs CBS socioeconomic cluster (Simpson's paradox)
10_network_model_comparison    ER / configuration / BA / Watts-Strogatz null models
11_rail_network_analysis       Heavy rail (route_type=2) only
12_rail_socioeconomic          Rail centrality vs socioeconomic profile
13_embeddings_link_prediction  Node2Vec and link prediction
14_multimodal_inventory        Mode inventory and cross-mode comparison
15_bus_network                 Bus-only network (route_type=3)
16_lightrail_and_minor_modes   Light rail, tram and minor modes
17_multimodal_transfer_hubs    Stations that connect two or more modes
18_travel_time_network         Travel-time weighted network
19_time_of_day_graphs          Per-hour graphs across the day
20_dynamic_resilience          Dynamic resilience, peak vs off-peak
21_demand_weighted_criticality Criticality weighted by scheduled demand
22_rerouting_model             Rerouting and load redistribution after removals
23_critical_station_lenses     Critical stations across all seven lenses
24_conclusions                 Synthesis, limitations, future work
```

Each notebook is self-contained: it installs what it needs, locates the
repository (or clones it on Colab), fetches the GTFS feed on demand, and carries
its own analysis code inline.

## Setup

Create an environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

All GTFS files needed by the analysis ship with this repository **except**
`stop_times.txt` (816 MB), which is hosted separately and fetched on demand:

```powershell
pip install gdown
gdown 1V_yPAWXV6mGTFGrfiosah5LngcLZnviW -O israel-public-transportation/stop_times.txt
```

You usually do not need to do this by hand: notebooks `00_setup_and_data` and
`02_graph_construction` download the file themselves if it is missing. Notebook 02
builds the graph from the raw feed; everything downstream reads the graph that 02
writes, so once 02 has run the large table is no longer needed.

## Run The Analysis

Open the notebooks in `notebooks/` and run them in numeric order, or execute the
whole series from the command line:

```powershell
foreach ($nb in Get-ChildItem notebooks\[0-9][0-9]_*.ipynb | Sort-Object Name) {
  python -m nbconvert --to notebook --execute --inplace `
    --ExecutePreprocessor.timeout=7200 $nb.FullName
}
```

Run them in order. A notebook that depends on an earlier stage fails with an
explicit message naming the notebook to run first, so the order is enforced rather
than assumed. The full series takes on the order of ten minutes on a laptop; the
expensive stages are the sampled betweenness (04), the four null models (10),
Node2Vec (13), and the resilience and rerouting simulations (06, 20, 22).

Expensive steps are exposed as constants near the top of each notebook (for
example `K_BETWEENNESS`), so a faster smoke run only means lowering those.

## Analysis Notes

`stop_times.txt` is streamed row by row because it is large. The feed is assumed
to be ordered by `trip_id` and `stop_sequence`, so consecutive rows of the same
trip define a segment without loading the table into memory. Notebook 02 verifies
that assumption instead of trusting it, and reports 562 `stop_sequence`
regressions across the 15.7M rows (0.004%, with no interleaved trip blocks).

Exact betweenness is expensive on a national network, so betweenness is estimated
from sampled source nodes on the largest connected component. Raise
`K_BETWEENNESS` in notebook 04 for a more stable estimate. The estimate is noisy,
so any percentile threshold built on it inherits that noise - notebook 04 reports
a stability check.

Resilience is measured by removing stops in centrality order and tracking the
largest connected component, against a random-removal baseline. Notebook 06
reports the surviving component normalized **both** by the original node count and
by the number of surviving nodes: dividing by the original count conflates "nodes
deleted" with "network fragmented".

Link prediction is evaluated with the edge split performed **before** the
embeddings are trained. Training Node2Vec on the full graph and then testing on
held-out edges leaks, and inflates AUC from 0.83 to 0.99; notebook 13 reports the
honest split plus a hard-negative evaluation that is considerably less flattering.

The pipeline compares the real transit graph against reference network models:
Erdős–Rényi, a degree-sequence configuration model, Barabási–Albert preferential
attachment, and Watts–Strogatz small-world.

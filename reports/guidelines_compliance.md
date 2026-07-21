# Project Guidelines Compliance

Maps each course requirement to a concrete artifact in this repository.
Report section numbers refer to `reports/final_report_he.md`.

## Submission requirements

| Requirement | Where it is addressed | Status |
|---|---|---|
| Code uploaded to GitHub | `github.com/seanfourman/israel-transit-network-resilience` | met |
| Prefer a Jupyter notebook, each code block with clear explanations | 25 notebooks in `notebooks/` (00–24). Every code cell is preceded by a markdown explanation — 263 markdown cells against 227 code cells | met |
| Code self-contained, runnable by a third party without changes | Each notebook installs its own dependencies via `_ensure()`, locates the repository (or clones it on Colab), and carries its analysis code inline. All 25 were executed end to end from a clean state | met |
| Special installations must be part of the code | `_ensure()` installs missing packages at run time; `requirements.txt` mirrors them | met |
| Data directly accessible to the running code; the reviewer must not download it | 8 of the 9 GTFS files are committed. `stop_times.txt` (816 MB) is hosted on Google Drive and fetched automatically by `gdown` inside notebooks 00, 02, 11, 14–19. Verified end to end | met |
| Team registered in the shared course file (names, problem, dataset) | Administrative step, outside this repository | **to verify** |
| Report ends with each student's individual contribution | **Not included.** Omitted at the team's request | **not met** |

> The guidelines state that without a per-student contribution section, all team
> members receive an identical grade. This is a deliberate choice, not an oversight.

## Final report criteria

| Criterion | Report section |
|---|---|
| Introduction / motivation / problem definition | 1 |
| Related work, with a short summary of each cited source | 2 and the reference list |
| Model / algorithm / method — the main contribution | 4 (graph construction, centrality measures, resilience protocol) |
| Results and findings, with interpretation per research question | 5.1–5.13 |
| Conclusions | 6, 8 |
| Length 6–8 pages | ~2,700 words plus 11 tables |
| Style, organisation, cleanliness | Numbered sections, limitations stated explicitly in 7 |

## Course themes covered

| Theme | Where |
|---|---|
| Graph construction and formal definition | notebook 02; report 4.1 |
| Connectivity, components, articulation points, bridges | notebook 03; report 5.1 |
| Centrality (degree, weighted, PageRank, betweenness, harmonic) | notebook 04; report 5.2 |
| Shortest paths | notebook 18 — travel-time weighted paths versus hop count; report 5.8 |
| Robustness, targeted versus random attack | notebooks 06, 15, 20; report 5.4, 5.9 |
| Community detection (Louvain, label propagation) | notebook 09; report 5.5 |
| Random network models (ER, configuration, BA, Watts–Strogatz) | notebook 10; report 5.1 |
| Graph learning (Node2Vec, link prediction) | notebook 13; report 5.13 |

## Extensions beyond the original scope

| Extension | Notebooks | Report |
|---|---|---|
| Per-mode networks (bus, rail, light rail, cable tram, trolleybus, demand-responsive) | 14–17 | 5.7 |
| Travel-time weighted network | 18 | 5.8 |
| Time-of-day analysis, peak versus off-peak | 19–20 | 5.9 |
| Demand-weighted criticality (population proxy) | 21 | 5.10 |
| Rerouting and load redistribution | 22 | 5.11 |
| Eight competing criticality lenses | 23 | 5.12 |

## Methodological corrections made during the work

These were found while rebuilding the project as notebooks and are documented
in the report rather than hidden:

| Issue | Effect | Fix |
|---|---|---|
| Scheduled stop calls were never counted | The service-volume column reached the equity analysis as all-NaN, so every within-community correlation silently evaluated to NaN | Counted during the existing streaming pass |
| Feed sort order assumed, never verified | Wrong edges would be created silently | Verification pass; 562 regressions found in 15.7M rows and reported |
| Link prediction trained on the full graph, then tested on held-out edges | AUC inflated to 0.9928 | Split before training; AUC 0.8284, and 0.2361 against hard negatives |
| Largest component normalised by the original node count | Conflated "nodes deleted" with "network fragmented" | Both normalisations reported |
| Articulation-point removal used a set, so fewer than k nodes were removed | Unfair attack comparison | Order-preserving de-duplication |
| Null models differed from the real graph by up to 40% in edge count | Clustering and path-length comparisons not meaningful | Size-matched, achieved counts reported |
| 57 within-cluster correlations tested without correction | 15 "significant" results | Benjamini–Hochberg applied; 8 survive |

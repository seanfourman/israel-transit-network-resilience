# Project Guidelines Compliance

This file maps the course project requirements to concrete repository artifacts.

| Guideline Requirement | Where It Is Addressed |
|---|---|
| Code must be uploaded to GitHub | Repository contains source code under `src/`, notebook under `notebooks/`, and generated outputs under `outputs/`. |
| Prefer Jupyter notebook with clear explanations | `notebooks/critical_stations_analysis.ipynb` runs the pipeline and displays tables/figures. |
| Code must be self-contained and runnable by a third party | `README.md` contains setup and run commands; `requirements.txt` lists dependencies; `src/transit_network_analysis.py` is a CLI. |
| Special installations must be part of the code/docs | Dependencies are listed in `requirements.txt`; Git LFS requirement is documented in `README.md`. |
| Data must be directly accessible to the code | GTFS data is in `israel-public-transportation/`; large files are tracked by Git LFS according to `.gitattributes`. |
| Proposal question: What problem is solved? | `reports/final_report_he.md`, Sections 1 and 9. |
| Proposal question: What data is used? | `reports/final_report_he.md`, Section 3. |
| Proposal question: What work is performed? | `reports/final_report_he.md`, Sections 4-6. |
| Proposal question: Which algorithms/techniques are used? | `reports/final_report_he.md`, Section 5. |
| Proposal question: How is the method evaluated? | `reports/final_report_he.md`, Sections 5.3 and 6.8. |
| Milestone: database metadata and usage | `reports/final_report_he.md`, Section 3; generated summaries in `outputs/tables/`. |
| Milestone: algorithm description | `reports/final_report_he.md`, Sections 4-5. |
| Final report: introduction/motivation/problem | `reports/final_report_he.md`, Section 1. |
| Final report: related work | `reports/final_report_he.md`, Section 2 and references. |
| Final report: model/algorithm/method | `reports/final_report_he.md`, Sections 4-5. |
| Final report: results and findings | `reports/final_report_he.md`, Section 6. |
| Final report: conclusions | `reports/final_report_he.md`, Section 9. |
| Final report: individual contributions | `reports/final_report_he.md`, Section 11. |
| Presentation-ready figures | `outputs/figures/*.png`. |
| Presentation-ready tables | `outputs/tables/*.csv`. |
| Presentation outline up to 10 slides | `reports/presentation_outline_he.md`. |

Before final submission, replace the placeholder student names and individual contributions with the real team members.

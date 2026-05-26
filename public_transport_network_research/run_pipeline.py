"""
run_pipeline.py — מריץ את כל שלבי המחקר בסדר
הרצה: python3.13 public_transport_network_research/run_pipeline.py
"""
import subprocess, sys, time
from pathlib import Path

PYTHON = sys.executable
BASE = Path(__file__).resolve().parent

STEPS = [
    ("01 — הכנת דאטה",           BASE / "01_data_preparation/scripts/01_load_and_clean.py"),
    ("02 — בניית גרף",            BASE / "02_graph_construction/scripts/01_build_graph.py"),
    ("03 — ניתוח תיאורי",         BASE / "03_network_descriptive_analysis/scripts/01_descriptive_analysis.py"),
    ("04 — מרכזיות",              BASE / "04_centrality_analysis/scripts/01_centrality.py"),
    ("05 — שיבושים ועמידות",      BASE / "05_robustness_and_disruption_analysis/scripts/01_robustness.py"),
    ("06 — השוואה אזורית",        BASE / "06_regional_comparison/scripts/01_regional.py"),
    ("07 — Community Detection",  BASE / "07_community_detection/scripts/01_community.py"),
    ("08 — Node2Vec + Embeddings",BASE / "08_graph_learning_node_embeddings/scripts/01_node2vec.py"),
    ("09 — Link Prediction",      BASE / "09_link_prediction_and_network_improvement/scripts/01_link_prediction.py"),
]

def run_step(name, script):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    t0 = time.time()
    result = subprocess.run([PYTHON, str(script)], capture_output=False)
    elapsed = time.time() - t0
    if result.returncode != 0:
        print(f"  ✗ שגיאה בשלב: {name}")
        return False
    print(f"  ✓ הושלם תוך {elapsed:.0f} שניות")
    return True

if __name__ == "__main__":
    print("=== Pipeline ראשי — עמידות רשת התחבורה ===")
    t_start = time.time()
    for name, script in STEPS:
        ok = run_step(name, script)
        if not ok:
            print(f"\nPipeline נעצר בשלב: {name}")
            sys.exit(1)
    total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"  Pipeline הושלם בהצלחה! ({total:.0f} שניות)")
    print(f"  גרפים נמצאים ב: {BASE}/figures/")
    print(f"{'='*60}")

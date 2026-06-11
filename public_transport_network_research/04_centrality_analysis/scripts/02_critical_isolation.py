"""
שלב 04 (משלים) — מבחן מציאות: אילו תחנות קריטיות באמת אין להן תחליף?

קריטיות בגרף (Betweenness גבוה) לא בהכרח אומרת קריטיות במציאות: אם יש תחנה
חלופית במרחק הליכה, נוסע פשוט עובר אליה והאזור לא מתנתק. נקודות הכשל האמיתיות
הן התחנות הקריטיות שגם *מבודדות* גיאוגרפית - אין להן חלופה קרובה.

קלט:  04_centrality_analysis/outputs/stop_metrics.csv  (כל התחנות עם Betweenness וקואורדינטות)
פלט:  04_centrality_analysis/outputs/critical_isolation.csv + figures/critical_isolation.png
"""
from pathlib import Path

ROOT     = Path(__file__).resolve().parents[3]
METRICS  = ROOT / "public_transport_network_research/04_centrality_analysis/outputs/stop_metrics.csv"
OUT_DIR  = Path(__file__).resolve().parents[1] / "outputs"
FIG_DIR  = ROOT / "public_transport_network_research/figures/04_centrality_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from _hebrew_bidi import install_hebrew
install_hebrew()
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from sklearn.neighbors import BallTree

WALK_M = 300  # מרחק הליכה סביר לתחנה חלופית (מטרים)
EARTH_M = 6371000.0


def main():
    print("=== שלב 04 משלים: בידוד תחנות קריטיות ===")
    m = pd.read_csv(METRICS, encoding="utf-8-sig").dropna(subset=["lat", "lon"]).reset_index(drop=True)

    # מרחק לתחנה הקרובה ביותר (מטרים) לכל תחנה, באמצעות BallTree עם מטריקת haversine
    coords = np.radians(m[["lat", "lon"]].values)
    tree = BallTree(coords, metric="haversine")
    dist, _ = tree.query(coords, k=2)            # k=2: התחנה עצמה + הקרובה אליה
    m["nearest_alt_m"] = dist[:, 1] * EARTH_M

    # קריטי = top 10% betweenness (הגדרת הפרויקט)
    thr = m["betweenness"].quantile(0.90)
    crit = m[m["betweenness"] >= thr].copy()
    isolated = crit[crit["nearest_alt_m"] > WALK_M]
    print(f"  תחנות קריטיות (top 10% betweenness): {len(crit):,}")
    print(f"  עם חלופה במרחק {WALK_M} מ׳: {len(crit)-len(isolated):,} ({100*(len(crit)-len(isolated))/len(crit):.1f}%)")
    print(f"  מבודדות (נקודת כשל אמיתית): {len(isolated):,} ({100*len(isolated)/len(crit):.1f}%)")

    crit.sort_values("betweenness", ascending=False).to_csv(
        OUT_DIR / "critical_isolation.csv", index=False, encoding="utf-8-sig")

    # גרף: תחנות קריטיות לפי המרחק לחלופה הקרובה
    bins   = [0, 100, 300, 500, 1000, 1e9]
    labels = ["עד 100 מ׳", "100-300 מ׳", "300-500 מ׳", "500-1000 מ׳", "מעל 1 ק״מ"]
    counts = pd.cut(crit["nearest_alt_m"], bins=bins, labels=labels, right=False).value_counts().reindex(labels)
    colors = ["#16a34a", "#16a34a", "#dc2626", "#dc2626", "#dc2626"]

    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.bar(labels, counts.values, color=colors, edgecolor="white")
    for bar, v in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
                f"{v}\n({100*v/len(crit):.0f}%)", ha="center", va="bottom", fontsize=11)
    ax.set_xlabel("מרחק לתחנה החלופית הקרובה ביותר", fontsize=14)
    ax.set_ylabel("מספר תחנות קריטיות", fontsize=14)
    ax.set_title("האם לתחנה הקריטית יש חלופה במרחק הליכה?", fontsize=16, fontweight="bold", pad=10)
    ax.tick_params(labelsize=12)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(handles=[Patch(color="#16a34a", label="יש חלופה קרובה - בפועל לא קריטית"),
                       Patch(color="#dc2626", label="מבודדת - נקודת כשל אמיתית")],
              fontsize=12, loc="upper right")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "critical_isolation.png", dpi=150)
    plt.close()
    print("  ✓ critical_isolation.png")
    print(f"\nפלטים נשמרו ב:\n  {OUT_DIR}\n  {FIG_DIR}")


if __name__ == "__main__":
    main()

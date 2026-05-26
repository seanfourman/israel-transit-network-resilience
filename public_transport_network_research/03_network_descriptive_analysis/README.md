# שלב 03 — ניתוח תיאורי של הרשת

## מה המטרה של החלק הזה?

להבין את המבנה הבסיסי של רשת התחבורה לפני שמתחילים לחפש דפוסים מורכבים.
זהו ה"תיאור" של הרשת — כמו "סיכום הנתונים" לפני ניתוח סטטיסטי.

## למה אנחנו עושים את זה?

לפני שאפשר לשאול "מי התחנה הכי מרכזית?", צריך לשאול:
- "האם הרשת בכלל מחוברת?"
- "כמה צמתים ספורדיים יש?"
- "האם יש נקודות תורפה ברורות?"

הניתוח התיאורי מבסס את ההבנה הבסיסית שעליה נשלוף את כל המסקנות בהמשך.

## קלט

- `02_graph_construction/outputs/graph_directed.pkl`
- `02_graph_construction/outputs/graph_undirected.pkl`
- `02_graph_construction/outputs/nodes.csv`
- `02_graph_construction/outputs/edges.csv`

## פלט

| קובץ | תוכן |
|------|------|
| `outputs/network_summary.json` | כל הסטטיסטיקות הבסיסיות |
| `outputs/degree_distribution.csv` | התפלגות דרגות |
| `outputs/articulation_points.csv` | רשימת Articulation Points |
| `outputs/bridges.csv` | רשימת Bridges |
| `figures/03_network_descriptive_analysis/` | כל גרפי הניתוח |

## איך זה מקדם את שאלת המחקר?

**חיבוריות הרשת** (כמה % מהתחנות בSCC הראשי) קובעת עד כמה ניתוח עמידות יהיה משמעותי.
**Bridges ו-Articulation Points** הם "תחנות/מקטעים קריטיים" אמיתיים לפי הגדרה — הם ישמשו אחד ממדדי הCentrality בשלב 05.

## מדדים לחישוב

### על הגרף המכוון:
- מספר צמתים `|V|`
- מספר קשתות `|E|`
- density = `|E| / (|V| × (|V|-1))`
- average out-degree, average in-degree
- מספר Strongly Connected Components (SCC)
- גודל SCC הגדול ביותר (absolute + % מהרשת)
- מספר Weakly Connected Components (WCC)

### על הגרף הלא מכוון:
- מספר Connected Components
- גודל הרכיב הגדול ביותר
- Bridges — כמה קשתות שהסרתן תפצל את הגרף
- Articulation Points — כמה צמתים שהסרתם תפצל את הגרף
- Clustering Coefficient (ממוצע לוקלי וגלובלי)
- Average Shortest Path Length (על הרכיב הגדול)

### התפלגות דרגות:
- Degree Distribution (Histogram)
- האם ההתפלגות היא Power Law? (בדיקת רשת Scale-Free)
- In-degree distribution, Out-degree distribution (גרף מכוון)

## קבצים/סקריפטים בחלק הזה

- `scripts/01_compute_basic_stats.py` — סטטיסטיקות בסיסיות
- `scripts/02_find_bridges_and_ap.py` — Bridges ו-Articulation Points
- `scripts/03_degree_distribution.py` — התפלגות דרגות
- `scripts/04_plot_network.py` — ויזואליזציית הרשת

## ויזואליזציות נדרשות

| גרף | תיאור | מתאים ל- |
|-----|--------|----------|
| `degree_distribution_hist.png` | היסטוגרמה של התפלגות דרגות | דוח + מצגת |
| `degree_distribution_loglog.png` | אותו גרף בסקלה לוג-לוג (לבדיקת Power Law) | דוח |
| `network_overview.png` | ויזואליזציה כללית של הרשת | מצגת |
| `components_summary_bar.png` | גרף עמודות — גודל רכיבים קשורים | דוח |
| `indegree_vs_outdegree.png` | פיזור In-degree מול Out-degree | דוח |

## מה צריך להופיע בדוח הסופי?

- טבלת סיכום של כל הסטטיסטיקות הבסיסיות
- דיון: האם הרשת צפופה או דלילה?
- דיון: האם הרשת מחוברת?
- כמה Bridges ו-Articulation Points נמצאו?
- פרשנות: מה זה אומר על עמידות הרשת?

## TODO

- [ ] לחשב את כל הסטטיסטיקות ולשמור ב-network_summary.json
- [ ] לזהות את כל ה-Bridges ולשמור ב-bridges.csv
- [ ] לזהות את כל ה-Articulation Points ולשמור ב-articulation_points.csv
- [ ] לייצר את כל הגרפים ולשמור בtables/figures/
- [ ] לבדוק האם ההתפלגות היא Power Law
- [ ] לכתוב את הפרשנות ב-structural_statistics.md

## פלטים צפויים

```
outputs/
├── network_summary.json
├── degree_distribution.csv
├── articulation_points.csv
└── bridges.csv

figures/03_network_descriptive_analysis/
├── degree_distribution_hist.png
├── degree_distribution_loglog.png
├── network_overview.png
├── components_summary_bar.png
└── indegree_vs_outdegree.png
```

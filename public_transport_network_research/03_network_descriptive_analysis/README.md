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
| `outputs/network_summary.csv` | אותן סטטיסטיקות בפורמט טבלאי |
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

- `scripts/01_descriptive_analysis.py` — computes summary statistics,
  bridges, articulation points, and descriptive figures.

## ויזואליזציות נדרשות

| גרף | תיאור | מתאים ל- |
|-----|--------|----------|
| `degree_distribution.png` | היסטוגרמה וסקאלת log-log של התפלגות דרגות | דוח + מצגת |
| `network_overview_map.png` | ויזואליזציה כללית של התחנות על מפה | מצגת |
| `components_summary_bar.png` | גרף עמודות — גודל רכיבים קשורים | דוח |
| `stops_by_region.png` | התפלגות תחנות לפי אזור | דוח + מצגת |

## מה צריך להופיע בדוח הסופי?

- טבלת סיכום של כל הסטטיסטיקות הבסיסיות
- דיון: האם הרשת צפופה או דלילה?
- דיון: האם הרשת מחוברת?
- כמה Bridges ו-Articulation Points נמצאו?
- פרשנות: מה זה אומר על עמידות הרשת?

## TODO / Historical Plan

- [x] לחשב את כל הסטטיסטיקות ולשמור ב-network_summary.json/csv
- [x] לזהות את כל ה-Bridges ולשמור ב-bridges.csv
- [x] לזהות את כל ה-Articulation Points ולשמור ב-articulation_points.csv
- [x] לייצר את הגרפים הקיימים ולשמור ב-figures/
- [ ] לבדוק האם ההתפלגות היא Power Law
- [ ] לכתוב את הפרשנות ב-structural_statistics.md

## פלטים צפויים

```
outputs/
├── network_summary.json
├── network_summary.csv
├── articulation_points.csv
└── bridges.csv

figures/03_network_descriptive_analysis/
├── degree_distribution.png
├── network_overview_map.png
├── components_summary_bar.png
└── stops_by_region.png
```

# שלב 05 — ניתוח שיבושים ועמידות (Robustness & Disruption Analysis)

## מה המטרה של החלק הזה?

זהו **לב הפרויקט**. בשלב זה מבצעים סימולציות הסרת תחנות ומודדים את הנזק שנגרם לרשת.
המטרה: לבדוק האם תחנות שנראות "מרכזיות" לפי Centrality הן אכן הקריטיות ביותר בפועל.

## למה אנחנו עושים את זה?

מדדי Centrality אומרים מי "חשוב" — אבל "חשוב" לא תמיד = "קריטי".
ייתכן שתחנה עם Betweenness גבוה מאוד תוסר ואחרות יחליפו אותה בקלות.
ייתכן שתחנה עם Betweenness בינוני היא למעשה Articulation Point שהסרתה שוברת את הרשת.
הסימולציה בודקת את הקשר בין המדד לנזק האמיתי.

## קלט

- `02_graph_construction/outputs/graph_directed.pkl`
- `02_graph_construction/outputs/graph_undirected.pkl`
- `04_centrality_analysis/outputs/stop_metrics.csv`
- `03_network_descriptive_analysis/outputs/articulation_points.csv`
- `03_network_descriptive_analysis/outputs/bridges.csv`

## פלט

| קובץ | תוכן |
|------|------|
| `outputs/disruption_results.csv` | תוצאות כל סימולציה |
| `outputs/resilience_summary.json` | סיכום השוואתי בין אסטרטגיות |
| `figures/05_robustness_and_disruption_analysis/` | גרפים |

## איך זה מקדם את שאלת המחקר?

**שאלת המחקר הראשית** שואלת אם הרשת עמידה לשיבושים.
שלב זה **מוסיף קוד ומספרים** לשאלה הזו — לא רק "נראה שהרשת פגיעה" אלא "כשמסירים X% מהתחנות לפי מדד Y, גודל הרכיב הגדול יורד ב-Z%".

## אסטרטגיות הסרה

### 1. הסרה לפי Betweenness (מהגבוה לנמוך)
המסירים תחנות שיושבות על הכי הרבה מסלולים קצרים.
**השערה:** סטרטגיה זו תגרום לנזק הגדול ביותר.

### 2. הסרה לפי Degree (מהגבוה לנמוך)
המסירים את "תחנות הHub" — אלו עם הכי הרבה שכנים.
**השערה:** גם אסטרטגיה זו תגרום לנזק גדול, אולי פחות מBetweenness.

### 3. הסרה לפי PageRank (מהגבוה לנמוך)
**השערה:** דומה לDegree אבל יכול להיות שונה.

### 4. הסרת Articulation Points (בלבד)
הסרת הנקודות שהוגדרו מבנית כקריטיות.
**השערה:** גרמת הנזק הגדולה ביותר ביחס לכמות התחנות שמוסרים.

### 5. הסרה רנדומלית (Baseline)
הסרת תחנות אקראיות — מהווה קו השוואה (Baseline).
**השערה:** הנזק יהיה קטן יותר מכל האסטרטגיות הממוקדות.

### 6. הסרת Bridges (מקטעים קריטיים)
הסרת קשתות במקום צמתים.

---

## מדדים שנמדדים אחרי כל הסרה

| מדד | תיאור |
|-----|--------|
| `largest_component_size` | גודל הרכיב הקשור הגדול (מספר תחנות) |
| `largest_component_share` | אחוז מהרשת המקורית |
| `num_components` | מספר הרכיבים הקשורים |
| `disconnected_stations` | מספר תחנות שהתנתקו |
| `avg_shortest_path` | זמן נסיעה ממוצע ברכיב הגדול |
| `accessibility_drop` | ירידה בנגישות ממיקומים נבחרים |

---

## פרוטוקול הסימולציה

```
לכל אסטרטגיה הסרה:
  1. טעון גרף מלא G
  2. דרג תחנות לפי האסטרטגיה
  3. לכל k ∈ {1, 5, 10, 20, 50, 100, ...}:
     a. הסר k תחנות מדורגות ראשונות
     b. חשב את כל המדדים
     c. שמור תוצאה
  4. ייצר resilience curve
```

---

## קבצים/סקריפטים בחלק הזה

- `scripts/01_run_disruption_simulation.py` — הרצת כל הסימולציות
- `scripts/02_measure_network_metrics.py` — חישוב מדדים אחרי הסרה
- `scripts/03_plot_resilience_curves.py` — ייצור גרפים
- `scripts/04_compare_strategies.py` — השוואת אסטרטגיות

## ויזואליזציות נדרשות

| גרף | תוכן | מתאים ל- |
|-----|-------|----------|
| `resilience_curves_comparison.png` | גרף קו — largest_component_share לפי k תחנות שהוסרו, השוואה בין אסטרטגיות | דוח + מצגת |
| `damage_at_k10_bar.png` | בar chart — נזק לאחר הסרת 10 תחנות לפי כל אסטרטגיה | דוח + מצגת |
| `articulation_points_impact.png` | השפעת הסרת AP לעומת הסרה רנדומלית | דוח |
| `before_after_disruption.png` | ויזואליזציה של הרשת לפני ואחרי הסרת Top 5 | מצגת |
| `bridges_impact.png` | השפעת הסרת Bridges | דוח |

## מה צריך להופיע בדוח הסופי?

- תיאור פרוטוקול הסימולציה
- גרפי resilience curves לכל האסטרטגיות
- טבלת סיכום: איזה אסטרטגיה גרמה לנזק הגדול ביותר?
- דיון: האם תחנות עם Centrality גבוה הן אכן הקריטיות ביותר?
- מסקנה: מה "שביר" ברשת התחבורה הישראלית?

## TODO

- [ ] לממש את פרוטוקול הסימולציה לכל 5 אסטרטגיות
- [ ] למדוד כל מדד לכל ערך k
- [ ] לייצר resilience_curves_comparison.png
- [ ] לייצר damage_at_k10_bar.png
- [ ] לכתוב את הפרשנות ב-disruption_scenarios.md ו-evaluation_metrics.md

## פלטים צפויים

```
outputs/
├── disruption_results.csv       (strategy, k, largest_component_share, ...)
└── resilience_summary.json

figures/05_robustness_and_disruption_analysis/
├── resilience_curves_comparison.png
├── damage_at_k10_bar.png
├── articulation_points_impact.png
├── before_after_disruption.png
└── bridges_impact.png
```

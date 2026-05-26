# שלב 04 — ניתוח מרכזיות (Centrality Analysis)

## מה המטרה של החלק הזה?

לחשב מדדי מרכזיות שונים לכל תחנה ולזהות את התחנות שנראות הכי "חשובות" לפי כל הגדרה.

## למה אנחנו עושים את זה?

לפני שנבדוק מה קורה כשמסירים תחנות (שלב 05), צריך לדעת **אילו** תחנות לבדוק.
מדדי Centrality הם דרך אוטומטית לדרג תחנות לפי "חשיבות" ברשת.
אבל כל מדד מגדיר "חשיבות" אחרת — ולכן נחשב מספר מדדים ונשווה.

## קלט

- `02_graph_construction/outputs/graph_directed.pkl`
- `02_graph_construction/outputs/graph_undirected.pkl`
- `02_graph_construction/outputs/nodes.csv`

## פלט

| קובץ | תוכן |
|------|------|
| `outputs/stop_metrics.csv` | כל מדדי ה-centrality לכל תחנה |
| `outputs/top10_by_metric.json` | Top 10 תחנות לכל מדד |
| `outputs/centrality_correlation.csv` | מטריצת קורלציה בין מדדים |
| `figures/04_centrality_analysis/` | גרפים ויזואליים |

## איך זה מקדם את שאלת המחקר?

שלב 04 עונה על שאלת המשנה: "אילו תחנות הן המרכזיות ביותר לפי מדדי Centrality?"
ומהווה בסיס לשלב 05 שבודק: "האם תחנות מרכזיות הן באמת הקריטיות ביותר?"

## מדדים לחישוב

### 1. Degree Centrality
```
degree_centrality(v) = deg(v) / (|V| - 1)
```
**מה מודד:** כמה שכנים ישירים יש לתחנה
**משמעות:** תחנת "תחנה מרכזית" שממנה יוצאים הרבה קווים

**גרסאות:**
- **In-Degree Centrality** — כמה תחנות מגיעות לכאן (כמה קווים מגיעים)
- **Out-Degree Centrality** — כמה תחנות יוצאות מכאן

---

### 2. Betweenness Centrality
```
betweenness_centrality(v) = Σ_{s≠v≠t} (σ_st(v) / σ_st)
```
**מה מודד:** כמה מסלולים קצרים בין זוגות תחנות עוברים דרך תחנה זו
**משמעות:** תחנת "צוואר בקבוק" — תחנה שהסרתה תאריך מסלולים רבים

**הערה:** לרשת גדולה — להשתמש ב-`nx.betweenness_centrality(G, k=500)` (approximation)

---

### 3. Closeness Centrality
```
closeness_centrality(v) = (|V| - 1) / Σ_u d(v, u)
```
**מה מודד:** כמה "קרוב" הצומת לשאר הצמתים ברשת
**משמעות:** תחנה שממנה ניתן להגיע לכל תחנה אחרת בזמן קצר

**הערה:** לרשת לא מחוברת, להשתמש ב-Harmonic Centrality:
```
harmonic_centrality(v) = Σ_{u≠v} (1 / d(v, u))
```

---

### 4. PageRank
```
PR(v) = (1-d)/|V| + d × Σ_{u→v} PR(u) / out_degree(u)
```
**מה מודד:** חשיבות הצומת על פי חשיבות השכנים שמצביעים עליו
**משמעות:** תחנה שמחוברת לתחנות חשובות אחרות — לא רק "כמה שכנים" אלא "כמה שכנים חשובים"

**הערה:** PageRank מתאים לגרף מכוון — כי הכיוון משמעותי (מי "מצביע" על מי).

---

### 5. Eigenvector Centrality (אופציונלי)
```
x_v = (1/λ) × Σ_{u: (u,v)∈E} x_u
```
**מה מודד:** דומה ל-PageRank — חשיבות על פי חשיבות השכנים
**הערה:** לעיתים לא מתכנס לגרפים לא מחוברים. PageRank מועדף.

---

## קבצים/סקריפטים בחלק הזה

- `scripts/01_compute_degree_centrality.py`
- `scripts/02_compute_betweenness.py` (כולל approximation לרשתות גדולות)
- `scripts/03_compute_closeness_harmonic.py`
- `scripts/04_compute_pagerank.py`
- `scripts/05_merge_centrality_metrics.py`
- `scripts/06_plot_centrality.py`

## ויזואליזציות נדרשות

| גרף | תוכן | מתאים ל- |
|-----|-------|----------|
| `top10_degree_bar.png` | Top 10 לפי Degree | דוח + מצגת |
| `top10_betweenness_bar.png` | Top 10 לפי Betweenness | דוח + מצגת |
| `top10_pagerank_bar.png` | Top 10 לפי PageRank | דוח + מצגת |
| `top10_harmonic_bar.png` | Top 10 לפי Harmonic Centrality | דוח |
| `centrality_correlation_heatmap.png` | קורלציה בין מדדים | דוח |
| `centrality_scatter_degree_betweenness.png` | פיזור Degree מול Betweenness | דוח + מצגת |
| `network_centrality_colored.png` | מפת הרשת עם תחנות צבועות לפי centrality | מצגת |

## מה צריך להופיע בדוח הסופי?

- הגדרה פורמלית של כל מדד
- טבלת Top-10 לכל מדד (עם שם תחנה, ערך, וניתוח)
- דיון: מה ההבדל בין המדדים? האם התחנות שמגיעות ראשונות זהות?
- קורלציה בין המדדים — האם Degree גבוה תמיד מקביל ל-Betweenness גבוה?

## שאלת הביניים המרכזית

> **"האם תחנות מרכזיות לפי מדדי Centrality הן באמת תחנות קריטיות לתפקוד הרשת?"**
> שאלה זו נענית בשלב 05.

## TODO

- [ ] לחשב Degree, Betweenness, Closeness/Harmonic, PageRank לכל תחנה
- [ ] לשמור stop_metrics.csv עם כל המדדים
- [ ] לייצר כל הגרפים
- [ ] לחשב קורלציות בין מדדים
- [ ] לכתוב interpretation_guide.md עם פרשנות לכל מדד

## פלטים צפויים

```
outputs/
├── stop_metrics.csv         (stop_id + כל מדדי centrality)
├── top10_by_metric.json
└── centrality_correlation.csv

figures/04_centrality_analysis/
├── top10_degree_bar.png
├── top10_betweenness_bar.png
├── top10_pagerank_bar.png
├── top10_harmonic_bar.png
├── centrality_correlation_heatmap.png
├── centrality_scatter_degree_betweenness.png
└── network_centrality_colored.png
```

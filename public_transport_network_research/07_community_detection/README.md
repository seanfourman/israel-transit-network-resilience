# שלב 07 — זיהוי קהילות (Community Detection)

## מה המטרה של החלק הזה?

לזהות אוטומטית "קהילות" ברשת — קבוצות של תחנות שמחוברות ביניהן יותר מאשר לשאר הרשת.

## למה אנחנו עושים את זה?

קהילות ברשת תחבורה מייצגות "אזורי תחבורה טבעיים" — אזורים שבהם הנסיעות הן בעיקר פנימיות.
**שאלה מרכזית:** האם הקהילות שזיהינו אוטומטית תואמות אזורים גיאוגרפיים? אם כן — הגיוני.
אם לא — ייתכן שמפעיל מסוים "כובש" אזורים גיאוגרפיים שונים, או שיש מסלולים בין-אזוריים שמאחדים אזורים מרוחקים.

## קלט

- `02_graph_construction/outputs/graph_undirected.pkl`
- `02_graph_construction/outputs/nodes.csv` (עם lat/lon לוויזואליזציה)

## פלט

| קובץ | תוכן |
|------|------|
| `outputs/community_assignments.csv` | community_id לכל תחנה |
| `outputs/community_summary.csv` | גודל כל קהילה, תחנות מרכזיות |
| `outputs/inter_community_bridges.csv` | תחנות שמחברות בין קהילות |
| `figures/07_community_detection/` | גרפים |

## איך זה מקדם את שאלת המחקר?

קהילות מגדירות "גבולות טבעיים" ברשת. תחנות שמחברות קהילות הן הקריטיות ביותר לשמירת אחדות הרשת.
זיהוי הקהילות גם תומך ב-Node Embeddings בשלב 08 — embeddings טובים אמורים לשקף מבנה קהילות.

## שיטות זיהוי קהילות

### 1. Louvain Algorithm (מומלץ ראשי)

**עקרון:** מנסה למקסם את ה-Modularity — מדד שבוחן עד כמה הקשרים בתוך הקהילות צפופים יחסית לצפוי.

```python
import community as community_louvain
partition = community_louvain.best_partition(G_undirected, weight='weight_freq')
modularity = community_louvain.modularity(partition, G_undirected, weight='weight_freq')
```

**יתרונות:** מהיר, עובד על רשתות גדולות, לא דורש מספר קהילות מראש
**חסרונות:** לא דטרמיניסטי (תוצאות שונות בהרצות שונות)

---

### 2. Label Propagation

**עקרון:** כל צומת "מאמץ" את התווית הנפוצה ביותר בשכנותיו. מתכנס לקהילות.

```python
from networkx.algorithms.community import label_propagation_communities
communities = label_propagation_communities(G_undirected)
```

**יתרונות:** מהיר מאוד, לא דורש פרמטרים
**חסרונות:** לא יציב — תוצאות שונות בכל הרצה

---

### 3. Girvan-Newman (על תת-גרף קטן)

**עקרון:** מסיר באופן חוזר את הקשת עם ה-Betweenness הגבוה ביותר — כך שקהילות "מתפרקות" בהדרגה.

**הערה:** יקר מדי על הגרף המלא. להריץ רק על תת-גרף של 200-500 תחנות.

```python
from networkx.algorithms.community import girvan_newman
communities = next(girvan_newman(G_subgraph))
```

---

## ניתוח הקהילות

### מה לבדוק לאחר זיהוי קהילות:

1. **כמה קהילות נמצאו?** (ציפייה: 10-50 קהילות)
2. **מה גודל הקהילות?** (האם יש כמה גדולות ורבות קטנות?)
3. **האם קהילות תואמות אזורים גיאוגרפיים?** (לבדוק lat/lon ממוצע של כל קהילה)
4. **האם קהילות תואמות מפעילים?** (לבדוק agency_id הנפוץ בכל קהילה)
5. **תחנות בין-קהילתיות:** תחנות שמחברות בין שתי קהילות שונות — מי הן?
6. **Modularity:** ערך גבוה (> 0.5) = קהילות ברורות, ערך נמוך = הרשת אחידה

---

## קבצים/סקריפטים בחלק הזה

- `scripts/01_louvain_community.py`
- `scripts/02_label_propagation.py`
- `scripts/03_girvan_newman_subgraph.py`
- `scripts/04_analyze_communities.py`
- `scripts/05_find_inter_community_nodes.py`
- `scripts/06_plot_communities.py`

## ויזואליזציות נדרשות

| גרף | תוכן | מתאים ל- |
|-----|-------|----------|
| `community_map_louvain.png` | מפה גיאוגרפית עם תחנות צבועות לפי קהילה | מצגת |
| `community_sizes_bar.png` | גרף עמודות — גודל כל קהילה | דוח |
| `inter_community_nodes.png` | תחנות שמחברות קהילות שונות | דוח |

## מה צריך להופיע בדוח הסופי?

- תיאור השיטות שהורצו + הסבר קצר לכל שיטה
- טבלת קהילות: מספר קהילה, גודל, תחנות מרכזיות, אזור גיאוגרפי רווח, מפעיל רווח
- ניתוח: האם הקהילות הגיוניות? תואמות גיאוגרפיה?
- טבלת תחנות בין-קהילתיות + ניתוח

## TODO / Historical Plan

- [x] להריץ Louvain ולשמור community_id לכל תחנה
- [x] להריץ Label Propagation ולהשוות תוצאות
- [x] לזהות תחנות בין-קהילתיות
- [ ] לבדוק קורלציה בין קהילות לאזורים גיאוגרפיים
- [ ] לבדוק קורלציה בין קהילות למפעילים
- [x] לייצר את גרפי הקהילות הקיימים

## פלטים צפויים

```
outputs/
├── community_assignments.csv      (stop_id, community_id_louvain, community_id_lp)
├── community_summary.csv          (community_id, size, centroid_lat, centroid_lon, top_agency)
└── inter_community_bridges.csv    (stop_id, community_a, community_b, betweenness)

figures/07_community_detection/
├── community_map_louvain.png
├── community_sizes_bar.png
└── inter_community_nodes.png
```

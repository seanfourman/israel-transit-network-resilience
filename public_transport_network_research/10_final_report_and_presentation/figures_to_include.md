# גרפים לדוח ולמצגת — רשימה מרכזית

## עקרון

כל גרף כאן מייצג **ממצא מחקרי** — לא "גרף יפה" אלא "ראיה לטענה מסוימת".
לכל גרף יש: שם, מקור, מסר מרכזי, ומתאים ל-דוח/מצגת/שניהם.

---

## שלב 03 — ניתוח תיאורי

### G1 — degree_distribution.png
- **מקור:** `figures/03_network_descriptive_analysis/`
- **מה מוצג:** היסטוגרמה של התפלגות דרגות — כמה תחנות יש לכל מספר שכנים
- **מסר:** "הרשת מאופיינת בפחות תחנות עם דרגה גבוהה ורבות עם דרגה נמוכה — מבנה Power-Law-like"
- **מתאים ל:** דוח + מצגת (שקף 4)

### G2 — network_overview_map.png
- **מקור:** `figures/03_network_descriptive_analysis/`
- **מה מוצג:** ויזואליזציה כללית של הרשת (או מפת ישראל עם תחנות)
- **מסר:** "הרשת מורכבת, עם ריכוז ברור באזור המרכז"
- **מתאים ל:** מצגת (שקף 3)

---

## שלב 04 — Centrality

### G3 — top_betweenness_bar.png
- **מקור:** `figures/04_centrality_analysis/`
- **מה מוצג:** 10 התחנות עם Betweenness הגבוה ביותר
- **מסר:** "תחנות ה-Betweenness הגבוה הן [שמות] — אלו שיושבות על הכי הרבה מסלולים"
- **מתאים ל:** דוח + מצגת (שקף 5)

### G4 — top_degree_bar.png
- **מקור:** `figures/04_centrality_analysis/`
- **מה מוצג:** 10 התחנות עם Degree הגבוה ביותר
- **מסר:** "תחנות ה-Degree הגבוה — רבות מהן Hub בערים גדולות"
- **מתאים ל:** דוח

### G5 — centrality_correlation_heatmap.png
- **מקור:** `figures/04_centrality_analysis/`
- **מה מוצג:** מטריצת קורלציה בין 4 מדדי Centrality
- **מסר:** "Degree ו-PageRank מאוד מתואמים, אבל Betweenness מציג דפוס שונה"
- **מתאים ל:** דוח

### G6 — centrality_scatter.png
- **מקור:** `figures/04_centrality_analysis/`
- **מה מוצג:** scatter plot — Degree מול Betweenness (נקודה = תחנה)
- **מסר:** "יש תחנות עם Degree נמוך אבל Betweenness גבוה — הן המעניינות!"
- **מתאים ל:** דוח + מצגת (שקף 5)

---

## שלב 05 — Robustness

### G7 — resilience_curves_comparison.png ⭐ (גרף מרכזי)
- **מקור:** `figures/05_robustness_and_disruption_analysis/`
- **מה מוצג:** 5 עקומות LCS(k) — אחת לכל אסטרטגיה הסרה
- **מסר:** "הסרה לפי Betweenness גורמת לנזק הגדול ביותר — הרשת פגיעה להתקפה ממוקדת"
- **מתאים ל:** דוח + מצגת (שקף 6) — **גרף הכי חשוב בפרויקט**

### G8 — damage_at_k10_bar.png
- **מקור:** `figures/05_robustness_and_disruption_analysis/`
- **מה מוצג:** Bar chart — LCS לאחר הסרת 10 תחנות לפי כל אסטרטגיה
- **מסר:** "Betweenness גורמת ל-X% ירידה לעומת Random שגורמת ל-Y% בלבד"
- **מתאים ל:** דוח + מצגת

---

## שלב 06 — השוואה אזורית

### G9 — regional_vulnerability_comparison.png
- **מקור:** `figures/06_regional_comparison/`
- **מה מוצג:** השוואה בין אזורים — מספר AP, Bridges, תחנות קריטיות
- **מסר:** "הפריפריה (צפון/דרום) מכילה יחסית יותר AP ו-Bridges — פגיעה גדולה יותר"
- **מתאים ל:** דוח + מצגת (שקף 7)

### G10 — stations_map_by_region.png
- **מקור:** `figures/06_regional_comparison/`
- **מה מוצג:** מפה גיאוגרפית של ישראל עם תחנות בצבעים לפי אזור
- **מסר:** "פיזור התחנות הקריטיות — ריכוז ברור במרכז"
- **מתאים ל:** מצגת (שקף 7)

---

## שלב 07 — Community Detection

### G11 — community_map_louvain.png ⭐
- **מקור:** `figures/07_community_detection/`
- **מה מוצג:** מפה גיאוגרפית עם תחנות צבועות לפי קהילה
- **מסר:** "קהילות הרשת [תואמות / לא תואמות] אזורים גיאוגרפיים"
- **מתאים ל:** דוח + מצגת (שקף 8)

### G12 — inter_community_nodes.png
- **מקור:** `figures/07_community_detection/`
- **מה מוצג:** תחנות שמחברות בין קהילות — מסומנות בגרף
- **מסר:** "תחנות ה-bridge בין קהילות חופפות לתחנות עם Betweenness גבוה"
- **מתאים ל:** דוח

---

## שלב 08 — Graph Learning

### G13 — tsne_by_critical.png ⭐
- **מקור:** `figures/08_graph_learning_node_embeddings/`
- **מה מוצג:** t-SNE 2D — תחנות קריטיות (אדום) לעומת רגילות (כחול)
- **מסר:** "תחנות קריטיות מקובצות יחד ב-embedding space — Node2Vec לומד מבנה מבני"
- **מתאים ל:** דוח + מצגת (שקף 9)

### G14 — confusion_matrix.png
- **מקור:** `figures/08_graph_learning_node_embeddings/`
- **מה מוצג:** Confusion Matrix לסיווג תחנות קריטיות
- **מסר:** "F1=X — embeddings מנבאים קריטיות ברמה [טובה/סבירה]"
- **מתאים ל:** דוח + מצגת (שקף 9)

---

## שלב 09 — Link Prediction

### G15 — method_comparison_auc_bar.png
- **מקור:** `figures/09_link_prediction_and_network_improvement/`
- **מה מוצג:** AUC לפי שיטה (CN, Jaccard, AA, RA, Node2Vec)
- **מסר:** "[שיטה X] משיגה AUC הגבוה ביותר"
- **מתאים ל:** דוח + מצגת (שקף 9)

### G16 — resilience_before_after_links.png ⭐
- **מקור:** `figures/09_link_prediction_and_network_improvement/`
- **מה מוצג:** resilience curve לפני ואחרי הוספת 20 חיבורים מוצעים
- **מסר:** "הוספת X חיבורים שיפרה את LCS ב-Y% לאחר שיבוש"
- **מתאים ל:** דוח + מצגת (שקף 10) — **ממצא הסיום של הפרויקט**

---

## סיכום — גרפים חובה (⭐)

| # | גרף | שקף |
|---|-----|-----|
| G7 | resilience_curves_comparison.png | 6 |
| G11 | community_map_louvain.png | 8 |
| G13 | tsne_by_critical.png | 9 |
| G16 | resilience_before_after_links.png | 10 |

שאר הגרפים — לדוח המלא.

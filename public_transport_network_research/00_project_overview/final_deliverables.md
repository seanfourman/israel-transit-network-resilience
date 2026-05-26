# תוצרים נדרשים — רשימה מלאה

## תוצרים טכניים (קוד ונתונים)

### קבצי נתונים
- [ ] `nodes.csv` — כל תחנות הרשת עם מאפיינים
- [ ] `edges.csv` — כל הקשתות עם משקלים
- [ ] `graph_directed.pkl` — גרף מכוון
- [ ] `graph_undirected.pkl` — גרף לא מכוון
- [ ] `stop_metrics.csv` — כל מדדי הcentrality לכל תחנה
- [ ] `community_assignments.csv` — שיוך קהילות לתחנות
- [ ] `node_embeddings.pkl` — ייצוגים וקטוריים
- [ ] `top_k_suggested_links.csv` — חיבורים מומלצים
- [ ] `disruption_results.csv` — תוצאות סימולציות שיבוש

### קבצי קוד (סקריפטים)
- [ ] `01_clean_gtfs.py` — ניקוי דאטה
- [ ] `02_build_graph.py` — בניית גרף
- [ ] `03_descriptive_analysis.py` — ניתוח תיאורי
- [ ] `04_centrality_analysis.py` — חישוב מרכזיות
- [ ] `05_robustness_simulation.py` — סימולציות שיבוש
- [ ] `06_regional_comparison.py` — השוואה אזורית
- [ ] `07_community_detection.py` — זיהוי קהילות
- [ ] `08_node_embeddings.py` — Node2Vec ומשימות
- [ ] `09_link_prediction.py` — ניבוי קישורים

---

## ויזואליזציות נדרשות

### ניתוח תיאורי
- [ ] degree_distribution.png
- [ ] network_overview_map.png
- [ ] components_summary_chart.png

### מרכזיות
- [x] top_degree_bar.png
- [x] top_betweenness_bar.png
- [x] top_pagerank_bar.png
- [ ] centrality_correlation_scatter.png
- [ ] station_map_centrality_colored.png (אופציונלי)

### שיבושים ועמידות
- [ ] resilience_curves_comparison.png
- [ ] disruption_damage_bar.png
- [ ] before_after_disruption.png

### השוואה אזורית
- [ ] critical_stations_by_region.png
- [ ] bridges_by_region.png
- [ ] regional_vulnerability_map.png (אופציונלי)

### קהילות
- [x] community_map_louvain.png
- [x] community_sizes_bar.png
- [x] inter_community_nodes.png

### Graph Learning
- [ ] tsne_embeddings.png
- [ ] pca_embeddings.png
- [ ] classification_confusion_matrix.png
- [ ] top_similar_stations_table.png

### Link Prediction
- [ ] link_prediction_roc.png
- [ ] method_comparison_bar.png
- [ ] suggested_links_visualization.png
- [ ] resilience_before_after_new_links.png

---

## תוצרים כתובים

- [ ] דוח מחקר מלא (20-30 עמודים)
- [ ] מצגת PowerPoint / PDF (10 שקפים)
- [ ] README מרכזי לפרויקט
- [ ] תיעוד שלבי הניתוח (קבצי README בכל תיקייה)

---

## קריטריוני הצלחה

| תחום | מה נדרש |
|------|---------|
| דאטה | רשת מנוקה עם לפחות 500 תחנות |
| גרף | גרף מחובר עם SCC ראשי ≥ 80% |
| Centrality | 4 מדדים לפחות + פרשנות |
| Robustness | השוואה בין לפחות 4 אסטרטגיות הסרה + random |
| אזורים | לפחות 3 אזורים גיאוגרפיים |
| קהילות | לפחות שתי שיטות זיהוי |
| Node Embeddings | לפחות 2 מתוך 3 המשימות (Similarity / Classification / Link Prediction) |
| ויזואליזציה | לפחות 10 גרפים ייחודיים |

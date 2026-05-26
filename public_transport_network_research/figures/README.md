# תיקיית Figures — ויזואליזציות המחקר

## מבנה

```
figures/
├── 03_network_descriptive_analysis/   ← גרפים מהניתוח התיאורי
├── 04_centrality_analysis/            ← גרפי Centrality
├── 05_robustness_and_disruption_analysis/ ← עקומות Resilience
├── 06_regional_comparison/            ← השוואה אזורית
├── 07_community_detection/            ← ויזואליזציית קהילות
├── 08_graph_learning_node_embeddings/ ← t-SNE, Confusion Matrix
└── 09_link_prediction_and_network_improvement/ ← ROC, לפני/אחרי
```

## כללי שמירה

- כל גרף נשמר כ-**PNG** ברזולוציה 150 DPI לפחות
- שם קובץ: `תיאור_קצר_בלי_רווחים.png`
- כל גרף צריך: כותרת, תוויות צירים (בעברית או אנגלית), legend אם יש יותר מסדרה אחת
- לגרפים חשובים במיוחד (resilience curves, t-SNE) — גם SVG לעיצוב נקי

## גרפים חובה (לפני הגשה)

- [ ] degree_distribution_hist.png
- [ ] resilience_curves_comparison.png ⭐
- [ ] top10_betweenness_bar.png
- [ ] community_map_geographic.png ⭐
- [ ] tsne_by_critical.png ⭐
- [ ] resilience_before_after_links.png ⭐

ראה `10_final_report_and_presentation/figures_to_include.md` לרשימה המלאה.

# שלב 09 — Link Prediction ושיפור הרשת

## מה המטרה של החלק הזה?

לחזות חיבורים חסרים ברשת ולבדוק האם הוספת חיבורים מומלצים משפרת את עמידות הרשת.

## למה אנחנו עושים את זה?

המחקר לא נגמר באיבחון — הוא צריך גם להציע פתרון.
אם מצאנו שהרשת פגיעה בנקודות מסוימות, **Link Prediction** מאפשר לשאול:
"אילו חיבורים חדשים בין תחנות יכולים להפחית את הפגיעות?"
ובדיקת העמידות אחרי ההוספה מאמתת שהחיבורים אכן משפרים.

## קלט

- `02_graph_construction/outputs/graph_undirected.pkl`
- `08_graph_learning_node_embeddings/outputs/node_embeddings.pkl`
- `05_robustness_and_disruption_analysis/outputs/disruption_results.csv`

## פלט

| קובץ | תוכן |
|------|------|
| `outputs/link_prediction_results.csv` | תוצאות כל שיטות הניבוי |
| `outputs/top_k_suggested_links.csv` | Top-K חיבורים מומלצים |
| `outputs/resilience_after_new_links.json` | מדדי עמידות אחרי הוספת חיבורים |
| `figures/09_link_prediction_and_network_improvement/` | גרפים |

## איך זה מקדם את שאלת המחקר?

שאלת המחקר שואלת גם "אילו חיבורים חדשים יכולים לשפר עמידות הרשת?"
שלב זה עונה על כך בצורה מדידה — לא רק "מציע" אלא גם "מוכיח" שיפור.

---

## Level 1 — Link Prediction קלאסי (הומוגני)

שיטות אלו לא דורשות ML — הן מחשבות ציון לכל זוג תחנות לא מחובר.

### Common Neighbors (CN)
```
score(u, v) = |N(u) ∩ N(v)|
```
ניבוי: ככל שיש יותר שכנים משותפים, כך סביר יותר שתהיה קשת.

### Jaccard Coefficient
```
score(u, v) = |N(u) ∩ N(v)| / |N(u) ∪ N(v)|
```
מנרמל לפי גודל השכנות — מתחשב גם בתחנות עם מעט שכנים.

### Resource Allocation (RA)
```
score(u, v) = Σ_{w ∈ N(u)∩N(v)} 1/degree(w)
```
שכן משותף עם דרגה נמוכה "נחשב יותר" — כי הוא "מקצה משאב" לחיבור.

### Adamic-Adar
```
score(u, v) = Σ_{w ∈ N(u)∩N(v)} 1/log(degree(w))
```
דומה ל-RA אבל עם לוגריתם — פחות חד ב-hubs.

### Preferential Attachment (PA)
```
score(u, v) = degree(u) × degree(v)
```
תחנות עם הרבה שכנים "מועדפות" — שיקוף של רשתות Scale-Free.

```python
from networkx.algorithms import link_prediction

cn_scores = list(link_prediction.common_neighbor_centrality(G, ebunch=non_edges))
jc_scores = list(link_prediction.jaccard_coefficient(G, ebunch=non_edges))
ra_scores = list(link_prediction.resource_allocation_index(G, ebunch=non_edges))
aa_scores = list(link_prediction.adamic_adar_index(G, ebunch=non_edges))
pa_scores = list(link_prediction.preferential_attachment(G, ebunch=non_edges))
```

---

## Level 2 — Link Prediction מבוסס Embeddings

### Node2Vec Similarity
```python
from sklearn.metrics.pairwise import cosine_similarity

def hadamard(u, v, embeddings):
    return embeddings[u] * embeddings[v]

def avg_embedding(u, v, embeddings):
    return (embeddings[u] + embeddings[v]) / 2
```

**מודל:**
```python
# features לכל זוג תחנות
X_pairs = [hadamard(u, v, embeddings) for u, v in edge_pairs]
y_pairs = [1 if (u, v) in G.edges() else 0 for u, v in edge_pairs]

clf = LogisticRegression()
clf.fit(X_train, y_train)
```

---

## פרוטוקול הערכה

```
1. הסר 10% מהקשתות (test_edges)
2. צור 10% זוגות שליליים (non_edges)
3. אמן כל שיטה על 90% הנותרים
4. נבא את ה-10% שהוסרו + הזוגות השליליים
5. מדוד AUC, Precision@K, Recall@K
6. השווה בין שיטות
```

---

## הצעת חיבורים חדשים לשיפור הרשת

לאחר הערכת השיטות, ניקח את השיטה הטובה ביותר ונניח:
```
Top-K = 20 חיבורים מומלצים (זוגות תחנות שאינם מחוברים כיום)
```

**לאחר הוספתם, נמדוד:**
- האם מספר ה-Bridges ירד?
- האם מספר ה-Articulation Points ירד?
- האם ה-Largest Component Share אחרי שיבוש (הסרת 10 תחנות) השתפר?
- האם ASPL ירד?

---

## קבצים/סקריפטים בחלק הזה

- `scripts/01_prepare_link_prediction_data.py`
- `scripts/02_classical_link_prediction.py`
- `scripts/03_embedding_link_prediction.py`
- `scripts/04_evaluate_link_prediction.py`
- `scripts/05_suggest_new_links.py`
- `scripts/06_test_resilience_improvement.py`
- `scripts/07_plot_link_prediction.py`

## ויזואליזציות נדרשות

| גרף | תוכן | מתאים ל- |
|-----|-------|----------|
| `link_prediction_roc.png` | ROC Curve לכל שיטה | דוח |
| `method_comparison_auc_bar.png` | AUC לפי שיטה | דוח + מצגת |
| `top_suggested_links_map.png` | מפה עם חיבורים מוצעים | מצגת |
| `resilience_before_after_links.png` | עמידות לפני ואחרי הוספת חיבורים | מצגת |
| `bridges_reduction.png` | ירידה במספר Bridges אחרי הוספה | דוח |

## מה צריך להופיע בדוח הסופי?

- תיאור כל שיטות הניבוי
- טבלת AUC להשוואה
- ROC Curves
- רשימת Top-20 חיבורים מוצעים
- השוואת עמידות לפני ואחרי הוספת חיבורים

## TODO

- [ ] לבנות את דאטה-סט של positive/negative edges
- [ ] להריץ כל שיטות ה-Link Prediction הקלאסיות
- [ ] להריץ Link Prediction מבוסס Embeddings
- [ ] להשוות AUC בין שיטות
- [ ] לייצר Top-20 חיבורים מומלצים
- [ ] לבדוק שיפור עמידות אחרי הוספת חיבורים
- [ ] לייצר כל הגרפים

## פלטים צפויים

```
outputs/
├── link_prediction_results.csv
├── top_k_suggested_links.csv
└── resilience_after_new_links.json

figures/09_link_prediction_and_network_improvement/
├── link_prediction_roc.png
├── method_comparison_auc_bar.png
├── top_suggested_links_map.png
├── resilience_before_after_links.png
└── bridges_reduction.png
```

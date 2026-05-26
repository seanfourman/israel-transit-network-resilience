# שלב 08 — Graph Learning ו-Node Embeddings

## מה המטרה של החלק הזה?

לייצג כל תחנה כוקטור מספרי (embedding) שמלכד את תפקידה המבני ברשת,
ולהשתמש ב-embeddings אלו לשלוש משימות: מציאת תחנות דומות, סיווג תחנות קריטיות, וניבוי קישורים.

## למה אנחנו עושים את זה?

מדדי Centrality הם מספרים בודדים שמאפיינים כל תחנה בממד אחד.
**Node Embeddings** מייצגים כל תחנה כוקטור בממד גבוה — מה שמאפשר:
- לזהות דמיון בין תחנות שמדדים פשוטים לא ייצגו
- לאמן מודלי ML על ייצוגים עשירים יותר
- לבצע Link Prediction על בסיס vectors

**חשוב:** זה **אינו** Deep Learning על תמונות (אין CNN). זהו למידת ייצוגים על גרפים.

## למה לא CNN?

CNN מתאים לנתונים עם מבנה רשת-כיריים (grid) כמו תמונות.
רשת תחבורה היא גרף כללי — אין מבנה גריד. CNN יתעלם ממבנה הגרף.
Node2Vec / DeepWalk מיועדים ספציפית לגרפים ולומדים מ-random walks על הרשת.
→ ראה גם: `why_not_cnn.md`

## קלט

- `02_graph_construction/outputs/graph_undirected.pkl`
- `04_centrality_analysis/outputs/stop_metrics.csv` (ל-labels)
- `03_network_descriptive_analysis/outputs/articulation_points.csv` (ל-labels)

## פלט

| קובץ | תוכן |
|------|------|
| `outputs/node_embeddings.pkl` | dict: stop_id → vector(128,) |
| `outputs/embeddings_df.csv` | טבלת embeddings |
| `outputs/station_similarity.csv` | תחנות דומות לכל תחנה בחירה |
| `outputs/classification_results.json` | תוצאות סיווג קריטיות |
| `figures/08_graph_learning_node_embeddings/` | גרפים |

## איך זה מקדם את שאלת המחקר?

Node Embeddings מאפשרים **למידת תפקיד מבני** — לא רק "כמה שכנים" אלא "מה הסביבה המבנית של התחנה".
משימות הסיווג והדמיון בודקות האם embeddings אכן קולטים מידע מבני שיש לו קורלציה עם קריטיות.

---

## משימה א — Station Similarity

**שאלה:** אילו תחנות דומות לתחנה X מבחינת תפקידן ברשת?

```python
from sklearn.metrics.pairwise import cosine_similarity

emb_matrix = np.array([embeddings[stop] for stop in stops])
similarities = cosine_similarity(emb_matrix)

# עבור תחנה מרכזית X:
top_similar = np.argsort(similarities[idx_x])[::-1][1:11]  # Top 10
```

**מה מצפים:** תחנה מרכזית תהיה דומה לתחנות מרכזיות אחרות — לא בהכרח אותו אזור גיאוגרפי.

---

## משימה ב — Critical Station Classification

**שאלה:** האם embeddings יכולים לנבא אם תחנה קריטית?

**הגדרת label:**
```python
critical = 1 if (stop_id in articulation_points) OR (betweenness > np.percentile(betweenness_values, 90))
critical = 0 otherwise
```

**מודל:**
```python
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

X = embeddings_matrix   # shape: (n_stops, embedding_dim)
y = critical_labels

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
clf = LogisticRegression()
clf.fit(X_train, y_train)
```

**מדדי הערכה:** Accuracy, Precision, Recall, F1-Score, Confusion Matrix

**מה המטרה:** לא "לנצח SOTA" אלא להראות שה-embeddings למדו מידע שיש לו קורלציה עם קריטיות.

---

## Node2Vec — תיאור האלגוריתם

**עקרון:**
1. מבצע **random walks** על הגרף — מסלולים אקראיים מכל צומת
2. מזין את ה-walks לאלגוריתם **Word2Vec** (כאילו "מילים ברצף")
3. הוקטורים שמתקבלים: צמתים שמופיעים יחד בwalks → וקטורים דומים

**פרמטרים:**
- `p` — פרמטר Return: ערך גבוה = BFS-like (שכנות מקומית)
- `q` — פרמטר In-Out: ערך גבוה = DFS-like (חקירת מבנה מרחוק)
- `dimensions` = 64 / 128
- `walk_length` = 30
- `num_walks` = 10

```python
from node2vec import Node2Vec

node2vec = Node2Vec(G_undirected, dimensions=128, walk_length=30, num_walks=10, p=1, q=1)
model = node2vec.fit(window=10, min_count=1, batch_words=4)
embeddings = {str(node): model.wv[str(node)] for node in G_undirected.nodes()}
```

---

## DeepWalk — חלופה ל-Node2Vec

DeepWalk הוא מקרה פרטי של Node2Vec עם `p=1, q=1` (random walk סטנדרטי).
לרוב נשתמש ב-Node2Vec שנותן יותר שליטה.

---

## קבצים/סקריפטים בחלק הזה

- `scripts/01_train_node2vec.py`
- `scripts/02_station_similarity.py`
- `scripts/03_critical_station_classification.py`
- `scripts/04_visualize_embeddings.py` (PCA + t-SNE)

## ויזואליזציות נדרשות

| גרף | תוכן | מתאים ל- |
|-----|-------|----------|
| `tsne_by_community.png` | t-SNE 2D — נקודות צבועות לפי קהילה | מצגת |
| `tsne_by_region.png` | t-SNE 2D — נקודות צבועות לפי אזור | מצגת |
| `tsne_by_critical.png` | t-SNE 2D — critical vs. non-critical | דוח + מצגת |
| `pca_embeddings.png` | PCA 2D (מהיר יותר מ-t-SNE) | דוח |
| `confusion_matrix.png` | Confusion Matrix לסיווג קריטיות | דוח + מצגת |
| `similar_stations_table.png` | טבלת Top-10 דומות לתחנה מרכזית | מצגת |

## מה צריך להופיע בדוח הסופי?

- הסבר Node2Vec: עקרון ה-random walks
- תיאור 3 המשימות ותוצאותיהן
- Classification Report (Precision, Recall, F1)
- Confusion Matrix
- גרפי t-SNE עם הסבר מה רואים

## TODO

- [ ] לאמן Node2Vec על הגרף הלא מכוון
- [ ] לשמור embeddings ל-pkl ול-csv
- [ ] לבצע Station Similarity ל-5 תחנות מרכזיות
- [ ] לאמן Logistic Regression + Random Forest לסיווג קריטיות
- [ ] לייצר גרפי t-SNE ו-PCA
- [ ] לכתוב critical_station_classification.md ו-station_similarity.md

## פלטים צפויים

```
outputs/
├── node_embeddings.pkl
├── embeddings_df.csv
├── station_similarity.csv
└── classification_results.json

figures/08_graph_learning_node_embeddings/
├── tsne_by_community.png
├── tsne_by_region.png
├── tsne_by_critical.png
├── pca_embeddings.png
├── confusion_matrix.png
└── similar_stations_table.png
```

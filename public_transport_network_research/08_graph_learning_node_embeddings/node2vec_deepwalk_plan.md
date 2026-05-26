# תכנית Node2Vec ו-DeepWalk

## תיאור רעיוני — Random Walks על גרף

### הרעיון
דמיינו "נוסע אקראי" שמתחיל בתחנה כלשהי ומתחיל לנסוע:
- בכל תחנה הוא בוחר תחנה עוקבת אקראית (לפי משקל הקשת)
- הוא עושה זאת 30 צעדים ברצף (walk_length)
- חוזר 10 פעמים מאותה תחנה (num_walks)

**הרצף שנוצר** (מסלול של תחנות) מוזן ל-**Word2Vec** — כאילו כל תחנה היא "מילה".
Word2Vec לומד: תחנות שמופיעות יחד בהרבה walks → וקטורים דומים.

### מה הוקטורים מייצגים?
- **תחנות עם תפקיד דומה ברשת** → וקטורים דומים
  - שתי תחנות שהן "Hub" בפאתי שתי ערים → וקטורים קרובים
  - שתי תחנות שהן "קצה" של קווים → וקטורים קרובים
- זה שונה מדמיון גיאוגרפי — תחנה בתל אביב ותחנה בחיפה יכולות להיות "דומות" מבנית

---

## פרמטרי Node2Vec

| פרמטר | ערך מומלץ | משמעות |
|--------|-----------|---------|
| `dimensions` | 128 | גודל הוקטור (embeddings) |
| `walk_length` | 30 | אורך כל random walk |
| `num_walks` | 10 | מספר walks מכל צומת |
| `p` | 1.0 | Return parameter (1=BFS-like, 0.5=DFS-like) |
| `q` | 1.0 | In-Out parameter |
| `window` | 10 | גודל חלון ב-Word2Vec |
| `workers` | 4 | מקביליזציה |

**הסבר p ו-q:**
- `p` קטן: ה-walk נוטה לחזור לצמתים שכבר ביקר בהם → BFS → קולט מבנה שכנות מקומי
- `q` קטן: ה-walk נוטה להתרחק → DFS → קולט מבנה מבני גלובלי

לפרויקט שלנו: `p=1, q=1` (DeepWalk סטנדרטי) כנקודת התחלה.

---

## קוד ריצה

```python
from node2vec import Node2Vec
import pickle

# אימון
node2vec_model = Node2Vec(
    G_undirected,
    dimensions=128,
    walk_length=30,
    num_walks=10,
    p=1,
    q=1,
    workers=4,
    seed=42
)

model = node2vec_model.fit(
    window=10,
    min_count=1,
    batch_words=4
)

# שמירה
embeddings = {str(node): model.wv[str(node)] for node in G_undirected.nodes()}
with open("outputs/node_embeddings.pkl", "wb") as f:
    pickle.dump(embeddings, f)
```

---

## ויזואליזציה — t-SNE

```python
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

nodes = list(embeddings.keys())
emb_matrix = np.array([embeddings[n] for n in nodes])

tsne = TSNE(n_components=2, random_state=42, perplexity=30)
emb_2d = tsne.fit_transform(emb_matrix)

# צביעה לפי קהילה
plt.figure(figsize=(12, 8))
for comm_id in communities:
    idx = [i for i, n in enumerate(nodes) if community_map[n] == comm_id]
    plt.scatter(emb_2d[idx, 0], emb_2d[idx, 1], label=f"Community {comm_id}", s=5)
plt.legend()
plt.title("Node Embeddings (t-SNE) — Colored by Community")
plt.savefig("figures/08.../tsne_by_community.png", dpi=150)
```

---

## ניסויים שכדאי להריץ

1. **p=1, q=1** (DeepWalk — baseline)
2. **p=0.5, q=2** (DFS-like — מבנה גלובלי)
3. **p=2, q=0.5** (BFS-like — מבנה מקומי)
4. **dimensions=64 vs. 128** — בדיקת גודל וקטור

לבחור את הגרסה עם F1 הגבוה ביותר במשימת הסיווג.

# תכנית הערכה — Link Prediction

## פרוטוקול מלא

### שלב 1 — הכנת דאטה-סט

```python
import random
import networkx as nx

G = load_graph("graph_undirected.pkl")
edges = list(G.edges())
non_edges = list(nx.non_edges(G))

# דגימה של 10% לtest
test_size = int(0.1 * len(edges))
test_edges = random.sample(edges, test_size)
test_non_edges = random.sample(non_edges, test_size)  # Negative samples

# הסרת test_edges מהגרף לאימון
G_train = G.copy()
G_train.remove_edges_from(test_edges)
```

### שלב 2 — הרצת שיטות

```python
# קלאסי
from networkx.algorithms.link_prediction import (
    common_neighbor_centrality, jaccard_coefficient,
    adamic_adar_index, resource_allocation_index,
    preferential_attachment
)
test_pairs = test_edges + test_non_edges
labels = [1]*len(test_edges) + [0]*len(test_non_edges)

cn = dict(common_neighbor_centrality(G_train, ebunch=test_pairs))
```

### שלב 3 — הערכה

```python
from sklearn.metrics import roc_auc_score, average_precision_score

def evaluate(scores_dict, pairs, labels):
    scores = [scores_dict.get((u, v), scores_dict.get((v, u), 0)) for u, v in pairs]
    auc = roc_auc_score(labels, scores)
    ap = average_precision_score(labels, scores)
    return auc, ap
```

---

## מדדים

| מדד | הגדרה | פרשנות |
|-----|--------|---------|
| **AUC-ROC** | שטח מתחת ל-ROC Curve | 0.5=אקראי, 1.0=מושלם |
| **Average Precision** | שטח מתחת ל-Precision-Recall Curve | מתאים לnimbalanced |
| **Precision@K** | מתוך K חיזויים עליונים — כמה נכונים? | מה חשוב להמליץ? |
| **Recall@K** | מתוך הקשתות האמיתיות — כמה נמצאו ב-Top K? | כמה מפספסים? |

---

## Baseline

```python
import numpy as np
# baseline — ניקוד אקראי
random_scores = np.random.random(len(test_pairs))
baseline_auc = roc_auc_score(labels, random_scores)
# ציפייה: ~0.5
```

**כל שיטה שמשיגה AUC > 0.6 היא שיפור משמעותי על ה-baseline.**

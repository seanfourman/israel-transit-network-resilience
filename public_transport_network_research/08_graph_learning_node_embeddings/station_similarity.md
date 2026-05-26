# משימה א — Station Similarity (דמיון בין תחנות)

## שאלת המחקר למשימה זו

> "אילו תחנות דומות לתחנה מרכזית X מבחינת **תפקידן המבני** ברשת?"

---

## מה מייחד דמיון מבני?

דמיון מבני שונה מדמיון גיאוגרפי:
- שתי תחנות יכולות להיות רחוקות גיאוגרפית אבל "דומות" ברשת — שתיהן Hub, שתיהן Articulation Point וכו'.
- Node Embeddings מלכד מידע מבני — תחנות עם random walks דומים יקבלו וקטורים דומים.

---

## שיטת החישוב

```python
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def find_similar_stations(target_stop_id, embeddings, nodes_df, top_k=10):
    nodes = list(embeddings.keys())
    emb_matrix = np.array([embeddings[n] for n in nodes])
    
    target_idx = nodes.index(str(target_stop_id))
    target_emb = emb_matrix[target_idx].reshape(1, -1)
    
    sims = cosine_similarity(target_emb, emb_matrix)[0]
    top_indices = np.argsort(sims)[::-1][1:top_k+1]  # מדלג על עצמו
    
    results = []
    for idx in top_indices:
        stop_id = nodes[idx]
        results.append({
            "stop_id": stop_id,
            "stop_name": nodes_df.loc[stop_id, "stop_name"],
            "cosine_similarity": round(sims[idx], 4),
            "region": nodes_df.loc[stop_id, "region"],
            "betweenness": nodes_df.loc[stop_id, "betweenness"]
        })
    return results
```

---

## תחנות לניתוח

לבחור 3-5 תחנות מרכזיות מאזורים שונים ולמצוא את הדומות להן:

| תחנת יעד | שאלה שנבדוק |
|-----------|-------------|
| תחנה מרכזית ת"א | מה הדומות לה מבחינת תפקיד? תחנות מרכזיות אחרות? |
| תחנה קצה בפריפריה | מה הדומות לה — האם תחנות קצה באזורים אחרים? |
| Articulation Point | האם הדומות לה הן גם AP? |

---

## פרשנות מצופה

**אם המשימה מצליחה:**
- תחנה מרכזית (Hub) תהיה דומה לתחנות מרכזיות אחרות מאזורים שונים
- תחנת קצה תהיה דומה לתחנות קצה אחרות
- Articulation Point תהיה דומה ל-AP אחרים

**אם המשימה נכשלת:**
- תחנות דומות יהיו שכנות גיאוגרפיות — סימן שה-embedding עיקרו גיאוגרפי ולא מבני

---

## פלטים

- `outputs/station_similarity.csv` — עבור 5 תחנות, Top 10 דומות לכל אחת
- `figures/08.../similar_stations_table.png` — טבלה ויזואלית

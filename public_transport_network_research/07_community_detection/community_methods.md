# שיטות Community Detection — פירוט

## Modularity — מדד הבסיס

לפני שמסבירים שיטות, חשוב להבין מה אנחנו ממקסמים:

```
Q = Σ_c [ (L_c / m) - (d_c / 2m)² ]
```

כאשר:
- `L_c` = מספר הקשתות **בתוך** קהילה c
- `m` = מספר הקשתות הכולל
- `d_c` = סכום הדרגות של צמתים בקהילה c

**פרשנות:**
- Q = 0: חלוקה לקהילות אקראית לחלוטין
- Q > 0.3: חלוקה עם מבנה קהילתי
- Q > 0.5: מבנה קהילתי חזק

---

## Louvain — תיאור האלגוריתם

**שלב א — Local:** כל צומת מנסה לעבור לקהילת שכנתו שתגדיל את ה-Modularity. חוזר עד יציבות.

**שלב ב — Aggregation:** כל קהילה הופכת לצומת "מצובר". חוזרים לשלב א.

**למה Louvain מהיר?** כי כל שלב הוא מקומי — לא בודק כל הרשת בכל פעם.

**פרמטרים חשובים:**
- `resolution` — ערך גבוה יוצר יותר קהילות קטנות, ערך נמוך — פחות קהילות גדולות. ברירת מחדל = 1.

```python
# ניסוי עם resolution שונה:
for res in [0.5, 1.0, 1.5, 2.0]:
    partition = community_louvain.best_partition(G, resolution=res)
    mod = community_louvain.modularity(partition, G)
    n_communities = len(set(partition.values()))
    print(f"resolution={res}: {n_communities} קהילות, modularity={mod:.3f}")
```

---

## Label Propagation — תיאור האלגוריתם

1. כל צומת מקבל תווית ייחודית משלו
2. בכל איטרציה: כל צומת מאמץ את התווית הנפוצה ביותר בשכנותיו
3. חוזר עד שאין שינויים

**יתרון:** O(m) — מהיר מאוד.
**חיסרון:** אינו דטרמיניסטי — לתוצאות דומות צריך להריץ מספר פעמים ולקחת ממוצע.

---

## Girvan-Newman — תיאור האלגוריתם

1. מחשב Betweenness Centrality לכל הקשתות
2. מסיר את הקשת עם Betweenness הגבוה ביותר
3. חוזר — חישוב מחדש → הסרה → וכן הלאה
4. כל הסרה פוצלת קהילה לשתיים — מייצרים "דנדרוגרמה"

**יתרון:** מייצר היררכיה של קהילות.
**חיסרון:** O(m²n) — יקר מאוד. מתאים לתת-גרף של ~500 צמתים.

---

## ניתוח תחנות בין-קהילתיות

תחנה שמחברת קהילות היא תחנה שיש לה שכנים בקהילות שונות.

```python
def find_inter_community_nodes(G, partition):
    inter_nodes = []
    for node in G.nodes():
        node_comm = partition[node]
        neighbor_comms = {partition[n] for n in G.neighbors(node)}
        neighbor_comms.discard(node_comm)
        if len(neighbor_comms) > 0:
            inter_nodes.append({
                "stop_id": node,
                "own_community": node_comm,
                "connected_communities": list(neighbor_comms)
            })
    return inter_nodes
```

**למה זה חשוב?** תחנות בין-קהילתיות הן "גשרים" בין אזורי תחבורה — ייתכן שיש חפיפה עם Articulation Points ו-Betweenness גבוה.

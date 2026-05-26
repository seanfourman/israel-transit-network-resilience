# הצעות לשיפור הרשת

## עקרון

לאחר שניבאנו חיבורים חסרים ברשת, נבחר את Top-20 בעלי הפוטנציאל הגבוה ביותר
**לשיפור עמידות הרשת** — לא סתם כל חיבור עם ניקוד גבוה.

---

## קריטריונים לבחירת חיבורים מיטביים

### קריטריון א — חיבור בין קהילות
חיבורים בין תחנות ב**קהילות שונות** — יפחיתו תלות בתחנות בין-קהילתיות.

```python
def cross_community_score(u, v, community_map, link_prediction_score):
    if community_map[u] != community_map[v]:
        return link_prediction_score * 1.5  # bonus
    return link_prediction_score
```

### קריטריון ב — חיבור אזורי שמפחית Bridges
חיבורים שלאחר הוספתם, מספר ה-Bridges ב-G יורד.

```python
def would_reduce_bridges(u, v, G):
    G_test = G.copy()
    G_test.add_edge(u, v)
    bridges_before = set(nx.bridges(G))
    bridges_after = set(nx.bridges(G_test))
    return len(bridges_before) - len(bridges_after)
```

### קריטריון ג — חיבור שמקטין AP
חיבורים שלאחר הוספתם, מספר ה-Articulation Points יורד.

```python
def would_reduce_ap(u, v, G):
    G_test = G.copy()
    G_test.add_edge(u, v)
    ap_before = set(nx.articulation_points(G))
    ap_after = set(nx.articulation_points(G_test))
    return len(ap_before) - len(ap_after)
```

---

## פרוטוקול בחירה

```
1. לקחת Top-200 חיבורים מהשיטה הטובה ביותר
2. לסנן: רק חיבורים בין-קהילתיים
3. לדרג: קודם אלו שמפחיתים AP, אחר כך שמפחיתים Bridges
4. לבחור Top-20
5. להוסיף ל-G ולמדוד שיפור עמידות
```

---

## מדידת שיפור עמידות

```python
# לפני הוספת חיבורים
resilience_before = simulate_disruption(G, strategy='betweenness', k=10)

# הוספת חיבורים מומלצים
G_improved = G.copy()
for u, v in top_suggested_links:
    G_improved.add_edge(u, v)

# אחרי הוספה
resilience_after = simulate_disruption(G_improved, strategy='betweenness', k=10)

improvement = resilience_after['largest_component_share'] - resilience_before['largest_component_share']
print(f"שיפור: {improvement:.2%}")
```

---

## תבנית טבלת חיבורים מומלצים

| # | תחנה א | תחנה ב | קהילה א | קהילה ב | אזור א | אזור ב | ניקוד | AP_drop | Bridge_drop |
|---|--------|--------|---------|---------|--------|--------|-------|---------|-------------|
| 1 | | | | | | | | | |
| 2 | | | | | | | | | |
| ... | | | | | | | | | |

(למלא לאחר הרצה)

---

## פרשנות מצופה

**תחנות שמומלצות לחיבור:**
- לרוב תחנות בשתי קהילות שונות הגובלות גיאוגרפית
- קיצור מסלול בין אזורים שכיום עוברים דרך Hub מרכזי אחד
- חיבורים שמפחיתים תלות ב-AP קריטיים

**הצגה בדוח:**
לבחור 2-3 חיבורים מוצעים ולהסביר בפרטים: מדוע הם מוצעים, מה יהיה השיפור, ומה העלות הסבירה (כמה ק"מ קו חדש?).

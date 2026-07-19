# אסטרטגיית משקול קשתות

> Scope note: this file documents the weighting options that were considered for
> the GTFS trip-adjacency graph. What is actually implemented in both
> `scripts/01_build_graph.py` and `src/transit_network_analysis.py` is
> **scheduled segment frequency only**.
>
> The `weight_time` and `weight_binary` fields described in the Decision section
> below were planned but are **not** produced by the current code, and
> shortest-path / betweenness computations run unweighted (hop count).

## למה חשוב לבחור משקל נכון?

המשקל שנבחר משפיע על:
- **מסלולים קצרים** — Dijkstra ישתמש בו כ"מחיר"
- **Centrality** — Betweenness מבוסס מסלולים קצרים
- **ניתוח עמידות** — שינוי זמן נסיעה לאחר הסרת תחנה

אם נבחר משקל לא מתאים, התוצאות יהיו מוטות.

---

## אפשרויות משקול

### אפשרות א — זמן נסיעה ממוצע (מומלצת לניתוח עמידות)

```python
W(u, v) = mean(departure_time[v, t] - arrival_time[u, t]
               for all trips t containing edge u→v)
```

**יתרונות:**
- אינטואיטיבי: "עלות" הקשת היא הזמן שלוקח לנסוע
- מתאים לחישוב מסלולים קצרים במונחי זמן

**חסרונות:**
- מניח שזמן הנסיעה קבוע (לא תלוי תנועה)
- שעות חסרות מצריכות imputation

---

### אפשרות ב — תדירות (מספר נסיעות ביום)

```python
W(u, v) = count(trips t containing edge u→v)
```

**יתרונות:**
- מעיד על "חשיבות" הקשת — קשת עם תדירות גבוהה היא חשובה יותר
- שימושי לניתוח קהילות ומרכזיות

**חסרונות:**
- לא מייצג זמן נסיעה
- תדירות גבוהה לא אומרת שהנסיעה קצרה

---

### אפשרות ג — משקל הפוך לתדירות (1/תדירות)

```python
W(u, v) = 1 / count(trips containing u→v)
```

**שימוש:** כאשר רוצים שקשת עם תדירות גבוהה תהיה "קרובה יותר" — כלומר, להשתמש בתדירות כקרבה ולא כמרחק.

---

### אפשרות ד — binary (0/1)

```python
W(u, v) = 1 אם קיים trip כלשהו שמחבר u→v
```

**שימוש:** לניתוח טופולוגי בלבד, ללא התחשבות בתדירות או זמן.
מתאים ל-Community Detection (Louvain).

---

## החלטה

בפרויקט זה נשמור **שני משקלים** לכל קשת:

| שדה | ערך | שימוש |
|-----|-----|--------|
| `weight_time` | זמן נסיעה ממוצע (דקות) | מסלולים קצרים, Betweenness |
| `weight_freq` | מספר נסיעות ביום | Community Detection, חשיבות קשת |
| `weight_binary` | 1 | ניתוח טופולוגי |

---

## טיפול בקשתות מרובות (Multi-edges)

ייתכן שבין שתי תחנות יש מספר קווים שונים.
**החלטה:** לכל זוג תחנות נשמור קשת **אחת** עם:
- `weight_time = ממוצע משוקלל של זמני הנסיעה`
- `weight_freq = סכום כל הנסיעות מכל הקווים`

**נימוק:** מבחינת עמידות הרשת, מה שחשוב הוא האם קיים חיבור בין שתי תחנות ועלותו — לא ספירת הקווים הספציפיים.

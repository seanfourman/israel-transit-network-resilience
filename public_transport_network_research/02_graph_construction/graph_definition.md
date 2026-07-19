# הגדרה פורמלית של הגרף

> Scope note: this document defines the project's graph model — a GTFS
> trip-adjacency graph where directed edges connect consecutive stops within a
> scheduled trip. Both implementations build this same model:
> `scripts/01_build_graph.py` (staged pipeline) and
> `src/transit_network_analysis.py` (canonical pipeline).
>
> Implementation note: the weighting section below lists average travel time as
> the recommended option, but the checked-in code implements **segment frequency
> only**. The undirected graph **sums** the two directions' frequencies rather
> than taking `min` of travel times, and betweenness/harmonic centrality are
> computed **unweighted** (hop count, not travel time).

## הגרף המכוון — G_directed

```
G_directed = (V, E, W)
```

### צמתים — V
- כל תחנת תחבורה ציבורית פעילה היא צומת
- `|V|` = מספר התחנות הפעילות לאחר ניקוי
- מזהה הצומת = `stop_id` מקובץ stops.txt

**מאפיינים של כל צומת:**

| מאפיין | מקור | שימוש |
|--------|------|--------|
| `stop_id` | stops.txt | מזהה ראשי |
| `stop_name` | stops.txt | תצוגה |
| `lat`, `lon` | stops.txt | מפות, שיוך אזורי |
| `region` | מחושב | השוואה אזורית |
| `parent_station` | stops.txt | אופציונלי |

---

### קשתות — E
- קשת מכוונת `(u → v)` קיימת אם ישנה נסיעה (trip) שבה `v` מגיע מיד אחרי `u`
- כלומר: אם בstop_times.txt, באותה trip_id, `stop_sequence[j] = stop_sequence[i] + 1`
  ו-`stop_id[i] = u`, `stop_id[j] = v`, אז קיימת קשת `u → v`

**הגדרה פורמלית:**
```
E = { (u, v) | ∃ trip t ∈ T: stop_sequence(u, t) + 1 = stop_sequence(v, t) }
```

---

### משקל קשתות — W
כל קשת `(u, v)` מקבלת משקל המחושב מהנתונים.

**אפשרות א — זמן נסיעה ממוצע (מומלץ):**
```
W(u, v) = ממוצע של (departure_time(v, t) - arrival_time(u, t)) על כל trip t שמכיל u→v
```
יחידות: דקות

**אפשרות ב — תדירות (מספר הופעות):**
```
W(u, v) = מספר ה-trips שמכילים את הקשת u→v
```
יחידות: מספר נסיעות ביום

**בפרויקט זה נשתמש בשניהם:** זמן נסיעה לחישובי מסלולים, תדירות למשקל "חשיבות קשת".

---

## הגרף הלא מכוון — G_undirected

```
G_undirected = (V, E', W')
```

- `E'` = קשת `{u, v}` קיימת אם `(u→v) ∈ E` **או** `(v→u) ∈ E`
- `W'({u, v}) = min(W(u→v), W(v→u))` — נקח את הזמן הנמוך יותר

**שימוש בגרף הלא מכוון:**
- חישוב Bridges ו-Articulation Points (דורש גרף לא מכוון)
- Community Detection (Louvain, Label Propagation)
- Closeness / Harmonic Centrality

---

## דוגמה מספרית

```
תחנה A → תחנה B → תחנה C
                     ↓
                  תחנה D

trip_id=101: A(seq=1, dep=08:00) → B(seq=2, arr=08:15) → C(seq=3, arr=08:25)
trip_id=102: A(seq=1, dep=09:00) → B(seq=2, arr=09:12) → C(seq=3, arr=09:22) → D(seq=4, arr=09:35)

קשתות שנוצרות:
A→B: W=mean(15, 12)=13.5 דקות, תדירות=2
B→C: W=mean(10, 10)=10 דקות, תדירות=2
C→D: W=13 דקות, תדירות=1
```

---

## החלטות בנייה

### למה גרף מכוון?
כי נסיעות אוטובוס הן מכוונות — יש הבדל בין הנסיעה "ת"א → חיפה" לבין "חיפה → ת"א".

### למה גם גרף לא מכוון?
כי מדדים מסוימים (Bridges, Articulation Points, Community Detection) עובדים על גרפים לא מכוונים.
בנוסף, לעיתים הרשת היא דו-כיוונית בפועל גם אם הנסיעות הן חד-כיווניות.

### מה לא כלול בגרף?
- לא כלולות קשתות בין תחנות באותו רחוב שאין ביניהן נסיעה ישירה
- לא כלולות קשתות "העברה" (transfer) — לא מוצגות בGTFS הסטנדרטי

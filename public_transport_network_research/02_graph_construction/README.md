# שלב 02 — בניית הגרף

## מה המטרה של החלק הזה?

להמיר את נתוני GTFS המנוקים לגרף נטוורק מחשבי שניתן לנתח עם אלגוריתמים של תורת הגרפים.

## למה אנחנו עושים את זה?

נתוני תחבורה ציבורית הם טבעית רשת: תחנות הן צמתים, ומסלולים בין תחנות הן קשתות.
ייצוג הרשת כגרף מאפשר לנו להשתמש בכל הכלים שפותחו לניתוח רשתות —
centrality, community detection, robustness, ועוד.

## קלט

נתונים מנוקים משלב 01:
- `01_data_preparation/outputs/stops_clean.csv`
- `01_data_preparation/outputs/stop_times_clean.csv`
- `01_data_preparation/outputs/trips_clean.csv`

## פלט

| קובץ | תוכן |
|------|------|
| `outputs/graph_directed.pkl` | גרף מכוון (NetworkX DiGraph) |
| `outputs/graph_undirected.pkl` | גרף לא מכוון (NetworkX Graph) |
| `outputs/nodes.csv` | כל הצמתים עם מאפיינים |
| `outputs/edges.csv` | כל הקשתות עם משקלים |
| `outputs/graph_build_summary.json` | סיכום בנייה (כמה צמתים, קשתות וכו') |

## איך זה מקדם את שאלת המחקר?

ללא גרף — אין מחקר. הגרף הוא הייצוג הפורמלי של רשת התחבורה שעליו נחשב
centrality, נריץ סימולציות שיבוש, ונזהה קהילות.

## קבצים/סקריפטים בחלק הזה

- `scripts/01_build_directed_graph.py` — בניית גרף מכוון
- `scripts/02_build_undirected_graph.py` — גרף לא מכוון
- `scripts/03_add_node_attributes.py` — הוספת מאפיינים לצמתים
- `scripts/04_export_graph_files.py` — שמירת קבצי פלט

## מה צריך להופיע בדוח הסופי?

- הגדרה פורמלית של הגרף: G = (V, E, W)
- תיאור מה מייצג כל צומת וכל קשת
- תיאור אסטרטגיית המשקולות
- graph_build_summary.json
- דיון בהחלטות הבנייה (גרף מכוון vs. לא מכוון, מה נכלל ומה לא)

## TODO

- [ ] לבנות גרף מכוון: stop_i → stop_j אם הם עוקבים באותה trip
- [ ] לחשב משקל לכל קשת (זמן נסיעה ממוצע / מספר הופעות)
- [ ] לבנות גרף לא מכוון על בסיס הגרף המכוון
- [ ] להוסיף מאפיינים לצמתים: stop_name, lat, lon, stop_id, region
- [ ] לשמור graph_build_summary.json
- [ ] לוודא שהגרף המכוון מחובר בצורה הגיונית (SCC ראשי)

## פלטים צפויים

```
outputs/
├── graph_directed.pkl      (NetworkX DiGraph)
├── graph_undirected.pkl    (NetworkX Graph)
├── nodes.csv               (stop_id, stop_name, lat, lon, region, ...)
├── edges.csv               (from_stop, to_stop, weight, num_trips, ...)
└── graph_build_summary.json
```

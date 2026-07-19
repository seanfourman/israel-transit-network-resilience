# שלב 02 — בניית הגרף

> Current implementation note: `scripts/01_build_graph.py` builds the GTFS
> trip-adjacency graph — directed edges connect consecutive stops within each
> scheduled trip. This is the same model used by the canonical
> `src/transit_network_analysis.py`, which is why both pipelines report the same
> structure (900 articulation points, 971 bridges).
>
> An earlier 500-meter spatial proximity graph once lived in this directory. It
> was retired and removed: it connected stops by geographic distance alone,
> regardless of whether any service links them, and it is not the source of any
> checked-in result.

## מה המטרה של החלק הזה?

להמיר את נתוני GTFS המנוקים לגרף נטוורק מחשבי שניתן לנתח עם אלגוריתמים של תורת הגרפים.

## למה אנחנו עושים את זה?

נתוני תחבורה ציבורית הם טבעית רשת: תחנות הן צמתים, ומסלולים בין תחנות הן קשתות.
ייצוג הרשת כגרף מאפשר לנו להשתמש בכל הכלים שפותחו לניתוח רשתות —
centrality, community detection, robustness, ועוד.

## קלט

נתונים מנוקים משלב 01:
- `01_data_preparation/outputs/stops_clean.csv`
- `01_data_preparation/outputs/routes_clean.csv`
- `01_data_preparation/outputs/trips_clean.csv`

The staged script streams `stop_times.txt` to derive trip segments, and uses
`stops_clean.csv` for node attributes (name, coordinates, region).

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

- `scripts/01_build_graph.py` — builds the trip-adjacency graph and exports
  directed/undirected NetworkX graphs, nodes, edges, and summary.

## מה צריך להופיע בדוח הסופי?

- הגדרה פורמלית של הגרף: G = (V, E, W)
- תיאור מה מייצג כל צומת וכל קשת
- תיאור אסטרטגיית המשקולות
- graph_build_summary.json
- דיון בהחלטות הבנייה (גרף מכוון vs. לא מכוון, מה נכלל ומה לא)

## TODO / Historical Plan

- [x] Build the trip-adjacency graph in `src/transit_network_analysis.py`.
- [x] Build the trip-adjacency graph in `scripts/01_build_graph.py`.
- [x] Add node attributes: stop name, latitude, longitude, region, metro.
- [x] Save `graph_build_summary.json`.
- [x] Retire the 500-meter proximity graph (removed — superseded by the
  trip-adjacency model in both pipelines).

## פלטים צפויים

```
outputs/
├── graph_directed.pkl      (NetworkX DiGraph)
├── graph_undirected.pkl    (NetworkX Graph)
├── nodes.csv               (stop_id, stop_name, lat, lon, region, metro)
├── edges.csv               (from_stop, to_stop, trip_frequency)
└── graph_build_summary.json
```

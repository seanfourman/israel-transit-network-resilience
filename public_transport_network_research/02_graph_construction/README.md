# שלב 02 — בניית הגרף

> Current implementation note: the executable staged script
> `scripts/01_build_graph.py` builds a 500-meter spatial proximity graph from
> cleaned stop coordinates. The primary final-project graph is built in
> `src/transit_network_analysis.py` from consecutive GTFS stops within each
> scheduled trip. Use the staged proximity graph as an exploratory/spatial
> extension, not as the source of the main final-report numbers.

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

The current staged script uses `stops_clean.csv` only for graph construction.

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

- `scripts/01_build_graph.py` — builds the staged 500-meter proximity graph
  and exports directed/undirected NetworkX graphs, nodes, edges, and summary.

## מה צריך להופיע בדוח הסופי?

- הגדרה פורמלית של הגרף: G = (V, E, W)
- תיאור מה מייצג כל צומת וכל קשת
- תיאור אסטרטגיית המשקולות
- graph_build_summary.json
- דיון בהחלטות הבנייה (גרף מכוון vs. לא מכוון, מה נכלל ומה לא)

## TODO / Historical Plan

- [x] Build the final-project trip-adjacency graph in `src/transit_network_analysis.py`.
- [x] Build the staged proximity graph in `scripts/01_build_graph.py`.
- [x] Add node attributes: stop name, latitude, longitude, region, metro.
- [x] Save `graph_build_summary.json`.
- [ ] If the staged pipeline is used in the final presentation, explicitly label it
  as a spatial proximity extension.

## פלטים צפויים

```
outputs/
├── graph_directed.pkl      (NetworkX DiGraph)
├── graph_undirected.pkl    (NetworkX Graph)
├── nodes.csv               (stop_id, stop_name, lat, lon, region, ...)
├── edges.csv               (from_stop, to_stop, distance_m, weight)
└── graph_build_summary.json
```

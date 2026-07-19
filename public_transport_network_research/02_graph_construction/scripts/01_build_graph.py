"""
שלב 02 — בניית גרף רשת התחבורה
הגישה: גרף נסיעות (Trip-Adjacency Graph) — המודל הראשי של הפרויקט
  - צומת = תחנה פעילה (תחנה שמופיעה בלפחות נסיעה אחת)
  - קשת מכוונת (u → v) = קיים קו (trip) שבו v היא התחנה הבאה מיד אחרי u
  - משקל = מספר הנסיעות שמשתמשות במקטע u→v (תדירות)

קלט:  01_data_preparation/outputs/stops_clean.csv  (תכונות תחנה: שם, קואורדינטות, אזור, מטרופולין)
       israel-public-transportation/stop_times.txt  (רצף תחנות בכל נסיעה, ממוין לפי trip_id, stop_sequence)
פלט:  02_graph_construction/outputs/

הערה: גרסת גרף הקרבה המרחבית (500m) הוסרה מהפרויקט — היא חיברה תחנות לפי מרחק
גאוגרפי בלבד, ללא קשר לקיום שירות ביניהן, ואינה מקור לאף תוצאה בפרויקט.
"""
import sys, csv, json, pickle
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[3]
STOPS_CLEAN = ROOT / "public_transport_network_research/01_data_preparation/outputs/stops_clean.csv"
STOP_TIMES  = ROOT / "israel-public-transportation/stop_times.txt"
OUT_DIR     = Path(__file__).resolve().parents[1] / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd
import networkx as nx

# מאפשר שורות ארוכות מאוד ב-stop_times
csv.field_size_limit(10_000_000)


def load_stop_attributes():
    """טוען תכונות לכל תחנה מקובץ ה-stops הנקי."""
    stops = pd.read_csv(STOPS_CLEAN, dtype=str, encoding="utf-8-sig")
    attr = {}
    for _, r in stops.iterrows():
        sid = r["stop_id"]
        try:
            lat = float(r["stop_lat"]) if r.get("stop_lat") not in (None, "", "nan") else None
            lon = float(r["stop_lon"]) if r.get("stop_lon") not in (None, "", "nan") else None
        except (TypeError, ValueError):
            lat = lon = None
        attr[sid] = {
            "stop_name": r.get("stop_name", "") or "",
            "lat": lat,
            "lon": lon,
            "region": r.get("region", "") or "",
            "metro": r.get("metro", "") or "",
        }
    return attr


def stream_trip_edges(stop_times_path):
    """
    סורק את stop_times.txt שורה-שורה ובונה ספירת מקטעי נסיעה.
    מניח שהקובץ ממוין לפי trip_id ואז stop_sequence (תקן GTFS),
    כך ששתי שורות עוקבות מאותה נסיעה מגדירות קשת u→v.
    """
    edge_count = defaultdict(int)
    active_stops = set()
    trips_seen = set()
    rows_read = 0
    stops_per_trip = defaultdict(int)

    with open(stop_times_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        ti = header.index("trip_id")
        si = header.index("stop_id")

        prev_trip = None
        prev_stop = None
        for row in reader:
            rows_read += 1
            trip = row[ti]
            stop = row[si]
            active_stops.add(stop)
            trips_seen.add(trip)
            stops_per_trip[trip] += 1

            if trip == prev_trip and prev_stop is not None and prev_stop != stop:
                edge_count[(prev_stop, stop)] += 1

            prev_trip = trip
            prev_stop = stop

            if rows_read % 2_000_000 == 0:
                print(f"    עיבד {rows_read:,} שורות, {len(edge_count):,} מקטעים ייחודיים ...")

    n_trips = len(trips_seen)
    spt = list(stops_per_trip.values())
    build_stats = {
        "stop_times_rows": rows_read,
        "active_stops": len(active_stops),
        "active_trips": n_trips,
        "directed_edges": len(edge_count),
        "min_stops_per_trip": int(min(spt)) if spt else 0,
        "mean_stops_per_trip": round(sum(spt) / len(spt), 2) if spt else 0,
        "max_stops_per_trip": int(max(spt)) if spt else 0,
    }
    return edge_count, active_stops, build_stats


def build_graphs(edge_count, attr):
    """בונה גרף מכוון (תדירות) וגרף לא מכוון (סכום שני הכיוונים)."""
    default_attr = {"stop_name": "", "lat": None, "lon": None, "region": "", "metro": ""}

    D = nx.DiGraph()
    for (u, v), c in edge_count.items():
        D.add_edge(u, v, weight=c)
    for n in D.nodes():
        D.nodes[n].update(attr.get(n, default_attr))

    G = nx.Graph()
    for u, v, data in D.edges(data=True):
        w = data["weight"]
        if G.has_edge(u, v):
            G[u][v]["weight"] += w
        else:
            G.add_edge(u, v, weight=w)
    for n in G.nodes():
        G.nodes[n].update(attr.get(n, default_attr))

    return G, D


def main():
    print("=== שלב 02: בניית גרף נסיעות (Trip-Adjacency) ===")
    print(f"  טוען תכונות תחנות מ-{STOPS_CLEAN.name} ...")
    attr = load_stop_attributes()
    print(f"  {len(attr):,} תחנות עם תכונות נטענו")

    print(f"  סורק {STOP_TIMES.name} (קובץ גדול, נא להמתין) ...")
    edge_count, active_stops, build_stats = stream_trip_edges(STOP_TIMES)
    print("\n  סטטיסטיקת בנייה:")
    for k, v in build_stats.items():
        print(f"    {k}: {v}")

    print("\n  בונה גרפים ...")
    G, D = build_graphs(edge_count, attr)
    print(f"  גרף לא מכוון: {G.number_of_nodes():,} צמתים, {G.number_of_edges():,} קשתות")
    print(f"  גרף מכוון:    {D.number_of_nodes():,} צמתים, {D.number_of_edges():,} קשתות")

    # שמירת גרפים
    with open(OUT_DIR / "graph_undirected.pkl", "wb") as f:
        pickle.dump(G, f)
    with open(OUT_DIR / "graph_directed.pkl", "wb") as f:
        pickle.dump(D, f)

    # nodes.csv
    node_rows = []
    for nid, data in G.nodes(data=True):
        row = {"stop_id": nid}
        row.update(data)
        node_rows.append(row)
    pd.DataFrame(node_rows).to_csv(OUT_DIR / "nodes.csv", index=False, encoding="utf-8-sig")

    # edges.csv (מכוון, עם תדירות)
    edge_rows = [{"from_stop": u, "to_stop": v, "trip_frequency": data["weight"]}
                 for u, v, data in D.edges(data=True)]
    pd.DataFrame(edge_rows).to_csv(OUT_DIR / "edges.csv", index=False, encoding="utf-8-sig")

    avg_degree = round(sum(d for _, d in G.degree()) / G.number_of_nodes(), 2)
    summary = {
        "graph_type": "trip_adjacency",
        "num_nodes": G.number_of_nodes(),
        "num_edges_undirected": G.number_of_edges(),
        "num_edges_directed": D.number_of_edges(),
        "avg_degree": avg_degree,
        "density": round(nx.density(G), 6),
        "build_stats": build_stats,
    }
    with open(OUT_DIR / "graph_build_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\nסיכום:")
    for k, v in summary.items():
        if k != "build_stats":
            print(f"  {k}: {v}")
    print(f"\nפלטים נשמרו ב: {OUT_DIR}")


if __name__ == "__main__":
    main()

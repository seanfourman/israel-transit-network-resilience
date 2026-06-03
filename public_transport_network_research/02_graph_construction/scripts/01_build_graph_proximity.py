"""
שלב 02 — בניית גרף רשת התחבורה
הגישה: גרף קרבה מרחבית (Proximity Graph)
  - צומת = תחנה פעילה
  - קשת  = שתי תחנות במרחק ≤ RADIUS_M מטרים
  - משקל = 1 / מרחק (מטר), כך שקרובות יותר = קשה יותר
קלט:  01_data_preparation/outputs/stops_clean.csv
פלט:  02_graph_construction/outputs/
"""
import sys, math, json, pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IN_DIR  = ROOT / "public_transport_network_research/01_data_preparation/outputs"
OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd
import numpy as np
import networkx as nx

RADIUS_M = 500   # מטרים — מרחק מקסימלי לקשת

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(max(0, a)))

def build_graphs(stops: pd.DataFrame, radius_m: float):
    stops_arr = stops[["stop_id","stop_lat","stop_lon"]].to_numpy()
    n = len(stops_arr)

    G_und = nx.Graph()
    for _, row in stops.iterrows():
        G_und.add_node(
            row["stop_id"],
            stop_name=row.get("stop_name", ""),
            lat=float(row["stop_lat"]),
            lon=float(row["stop_lon"]),
            region=row.get("region", ""),
            metro=row.get("metro", ""),
        )

    print(f"  מחשב קשתות בין {n:,} תחנות (radius={radius_m}m) ...")

    # בניית bucket לפי lat לחיסכון בזמן חישוב
    lat_step = radius_m / 111_000  # גרדות קירוב
    from collections import defaultdict
    buckets = defaultdict(list)
    for idx, row in stops.iterrows():
        bucket_key = int(float(row["stop_lat"]) / lat_step)
        buckets[bucket_key].append(row)

    edges_added = 0
    edge_rows = []

    for idx, row in stops.iterrows():
        sid = row["stop_id"]
        la1, lo1 = float(row["stop_lat"]), float(row["stop_lon"])
        bk = int(la1 / lat_step)

        for neighbor_row in buckets[bk-1] + buckets[bk] + buckets[bk+1]:
            sid2 = neighbor_row["stop_id"]
            if sid2 <= sid:   # מונע כפילויות
                continue
            la2, lo2 = float(neighbor_row["stop_lat"]), float(neighbor_row["stop_lon"])
            dist = haversine_m(la1, lo1, la2, lo2)
            if dist <= radius_m and dist > 0:
                w = 1.0 / dist
                G_und.add_edge(sid, sid2, weight=w, distance_m=round(dist, 1))
                edges_added += 1
                edge_rows.append({
                    "from_stop": sid,
                    "to_stop": sid2,
                    "distance_m": round(dist, 1),
                    "weight": round(w, 6),
                })

        if idx % 5000 == 0:
            print(f"    עיבד {idx:,}/{n:,} תחנות, {edges_added:,} קשתות עד כה ...")

    G_dir = G_und.to_directed()
    return G_und, G_dir, pd.DataFrame(edge_rows)

def main():
    print("=== שלב 02: בניית גרף ===")
    stops = pd.read_csv(IN_DIR / "stops_clean.csv", dtype=str, encoding="utf-8-sig")
    stops["stop_lat"] = pd.to_numeric(stops["stop_lat"])
    stops["stop_lon"] = pd.to_numeric(stops["stop_lon"])
    print(f"  {len(stops):,} תחנות נטענו")

    G_und, G_dir, edges_df = build_graphs(stops, RADIUS_M)

    print(f"\n  גרף לא מכוון: {G_und.number_of_nodes():,} צמתים, {G_und.number_of_edges():,} קשתות")
    print(f"  גרף מכוון:    {G_dir.number_of_nodes():,} צמתים, {G_dir.number_of_edges():,} קשתות")

    # שמירת גרפים
    with open(OUT_DIR / "graph_undirected.pkl", "wb") as f:
        pickle.dump(G_und, f)
    with open(OUT_DIR / "graph_directed.pkl", "wb") as f:
        pickle.dump(G_dir, f)

    # שמירת nodes / edges כ-CSV
    node_rows = []
    for nid, data in G_und.nodes(data=True):
        row = {"stop_id": nid}
        row.update(data)
        node_rows.append(row)
    nodes_df = pd.DataFrame(node_rows)
    nodes_df.to_csv(OUT_DIR / "nodes.csv", index=False, encoding="utf-8-sig")
    edges_df.to_csv(OUT_DIR / "edges.csv", index=False, encoding="utf-8-sig")

    summary = {
        "num_nodes": G_und.number_of_nodes(),
        "num_edges_undirected": G_und.number_of_edges(),
        "num_edges_directed": G_dir.number_of_edges(),
        "radius_m": RADIUS_M,
        "avg_degree": round(sum(d for _, d in G_und.degree()) / G_und.number_of_nodes(), 2),
        "density": round(nx.density(G_und), 6),
    }
    with open(OUT_DIR / "graph_build_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nסיכום:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\nפלטים נשמרו ב: {OUT_DIR}")

if __name__ == "__main__":
    main()

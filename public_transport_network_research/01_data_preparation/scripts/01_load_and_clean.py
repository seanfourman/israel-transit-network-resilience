"""
שלב 01 — טעינה וניקוי נתוני GTFS
קלט:  israel-public-transportation/*.txt
פלט:  01_data_preparation/outputs/
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "israel-public-transportation"
OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

import pandas as pd
import json

def load_stops():
    df = pd.read_csv(DATA_DIR / "stops.txt", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    before = len(df)
    df["stop_lat"] = pd.to_numeric(df["stop_lat"], errors="coerce")
    df["stop_lon"] = pd.to_numeric(df["stop_lon"], errors="coerce")
    df = df.dropna(subset=["stop_lat", "stop_lon"])
    df = df[(df["stop_lat"] > 29) & (df["stop_lat"] < 34)]
    df = df[(df["stop_lon"] > 34) & (df["stop_lon"] < 36)]
    after = len(df)
    print(f"  stops: {before} → {after} (removed {before-after} with bad coords)")
    return df

def load_routes():
    df = pd.read_csv(DATA_DIR / "routes.txt", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    print(f"  routes: {len(df)}")
    return df

def load_trips():
    df = pd.read_csv(DATA_DIR / "trips.txt", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    print(f"  trips: {len(df)}")
    return df

def load_agencies():
    df = pd.read_csv(DATA_DIR / "agency.txt", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    print(f"  agencies: {len(df)}")
    return df

def assign_region(lat, lon):
    if 31.70 <= lat <= 31.90 and 34.95 <= lon <= 35.30:
        return "ירושלים"
    elif lat > 32.50:
        return "צפון"
    elif lat >= 31.55:
        return "מרכז"
    else:
        return "דרום"

def assign_metro(lat, lon):
    metros = {
        "תל אביב": (32.0853, 34.7818, 30),
        "חיפה":    (32.7940, 34.9896, 25),
        "ירושלים": (31.7683, 35.2137, 20),
        "באר שבע": (31.2518, 34.7913, 25),
    }
    import math
    def haversine(la1, lo1, la2, lo2):
        R = 6371
        phi1, phi2 = math.radians(la1), math.radians(la2)
        dphi = math.radians(la2 - la1)
        dlam = math.radians(lo2 - lo1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
        return 2*R*math.asin(math.sqrt(a))
    for city, (clat, clon, radius) in metros.items():
        if haversine(lat, lon, clat, clon) <= radius:
            return city
    return "פריפריה"

def main():
    print("=== שלב 01: טעינה וניקוי ===")
    stops   = load_stops()
    routes  = load_routes()
    trips   = load_trips()
    agencies = load_agencies()

    stops["region"] = stops.apply(lambda r: assign_region(r["stop_lat"], r["stop_lon"]), axis=1)
    stops["metro"]  = stops.apply(lambda r: assign_metro(r["stop_lat"], r["stop_lon"]), axis=1)

    stops.to_csv(OUT_DIR / "stops_clean.csv", index=False, encoding="utf-8-sig")
    routes.to_csv(OUT_DIR / "routes_clean.csv", index=False, encoding="utf-8-sig")
    trips.to_csv(OUT_DIR / "trips_clean.csv", index=False, encoding="utf-8-sig")
    agencies.to_csv(OUT_DIR / "agencies_clean.csv", index=False, encoding="utf-8-sig")

    report = {
        "stops_total": len(stops),
        "routes_total": len(routes),
        "trips_total": len(trips),
        "agencies_total": len(agencies),
        "region_counts": stops["region"].value_counts().to_dict(),
        "metro_counts":  stops["metro"].value_counts().to_dict(),
        "route_types":   routes["route_type"].value_counts().to_dict(),
    }
    with open(OUT_DIR / "data_cleaning_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nסיכום:")
    for k, v in report.items():
        print(f"  {k}: {v}")
    print(f"\nפלטים נשמרו ב: {OUT_DIR}")

if __name__ == "__main__":
    main()

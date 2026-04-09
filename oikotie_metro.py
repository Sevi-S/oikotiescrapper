#!/usr/bin/env python3
"""
Oikotie apartment finder with Helsinki metro station proximity.
Fetches listings from Oikotie API and ranks by distance to nearest metro.
Tracks seen listings so daily runs only show new ones.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from geopy.distance import geodesic
from tabulate import tabulate

# Helsinki metro stations (name, lat, lon)
METRO_STATIONS = [
    ("Mellunmäki", 60.2379, 25.1041),
    ("Kontula", 60.2365, 25.0832),
    ("Myllypuro", 60.2244, 25.0594),
    ("Itäkeskus", 60.2103, 25.0826),
    ("Puotila", 60.2098, 25.1003),
    ("Rastila", 60.2072, 25.1186),
    ("Vuosaari", 60.2073, 25.1369),
    ("Herttoniemi", 60.1946, 25.0283),
    ("Siilitie", 60.1920, 25.0490),
    ("Kulosaari", 60.1876, 25.0063),
    ("Kalasatama", 60.1876, 24.9770),
    ("Sörnäinen", 60.1854, 24.9530),
    ("Hakaniemi", 60.1793, 24.9510),
    ("Kaisaniemi", 60.1718, 24.9440),
    ("Rautatientori", 60.1710, 24.9430),
    ("Kamppi", 60.1688, 24.9320),
    ("Ruoholahti", 60.1650, 24.9140),
    ("Lauttasaari", 60.1590, 24.8780),
    ("Koivusaari", 60.1620, 24.8570),
    ("Keilaniemi", 60.1756, 24.8270),
    ("Aalto-yliopisto", 60.1845, 24.8260),
    ("Tapiola", 60.1753, 24.8050),
    ("Urheilupuisto", 60.1780, 24.7870),
    ("Niittykumpu", 60.1780, 24.7620),
    ("Matinkylä", 60.1600, 24.7390),
    ("Finnoo", 60.1570, 24.7170),
    ("Kivenlahti", 60.1580, 24.6870),
    ("Espoonlahti", 60.1530, 24.6560),
]

WALK_SPEED_KMH = 5.0
BASE_URL = "https://asunnot.oikotie.fi"
API_URL = f"{BASE_URL}/api/cards"
SEEN_FILE = os.path.join(os.environ.get("RESULTS_DIR", os.path.dirname(os.path.abspath(__file__))), "seen.json")
RESULTS_FILE = os.path.join(os.environ.get("RESULTS_DIR", os.path.dirname(os.path.abspath(__file__))), "results.csv")


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f)
    return {}


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f)


CSV_FIELDS = ["first_seen", "district", "address", "rooms", "size_m2", "price", "year", "metro", "walk_min", "url"]


def append_results_csv(results):
    """Append new results to the cumulative CSV file."""
    write_header = not os.path.exists(RESULTS_FILE)
    with open(RESULTS_FILE, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if write_header:
            w.writeheader()
        for r in results:
            w.writerow(r)


def get_auth_tokens():
    r = requests.get(f"{BASE_URL}/myytavat-asunnot", headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    })
    soup = BeautifulSoup(r.text, "html.parser")
    token = soup.find("meta", {"name": "api-token"})
    loaded = soup.find("meta", {"name": "loaded"})
    cuid = soup.find("meta", {"name": "cuid"})
    if not all([token, loaded, cuid]):
        sys.exit("Failed to get auth tokens from Oikotie")
    return {
        "OTA-token": token["content"],
        "OTA-loaded": loaded["content"],
        "OTA-cuid": cuid["content"],
    }


def get_station_range(name_from, name_to):
    names = [s[0].lower() for s in METRO_STATIONS]
    try:
        i = names.index(name_from.lower())
        j = names.index(name_to.lower())
    except ValueError as e:
        sys.exit(f"Unknown metro station: {e}. Available: {', '.join(s[0] for s in METRO_STATIONS)}")
    lo, hi = min(i, j), max(i, j)
    return METRO_STATIONS[lo:hi + 1]


def nearest_metro(lat, lon, stations):
    best = min(stations, key=lambda s: geodesic((lat, lon), (s[1], s[2])).km)
    return best[0], geodesic((lat, lon), (best[1], best[2])).km


def fetch_and_filter(tokens, params, max_metro_min, stations, rooms_min, rooms_max, max_pages, seen):
    headers = {
        **tokens,
        "Referer": f"{BASE_URL}/myytavat-asunnot",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    }
    limit = 24
    offset = 0
    results = []
    fetched = 0
    pages = 0

    while pages < max_pages:
        query = {
            "cardType": 100,
            "limit": limit,
            "offset": offset,
            "sortBy": "published_desc",
        }
        for key, qkey in [
            ("locations", "locations"), ("price_min", "price[min]"),
            ("price_max", "price[max]"), ("size_min", "size[min]"),
            ("size_max", "size[max]"), ("rooms_min", "rooms[min]"),
            ("rooms_max", "rooms[max]"), ("building_type", "buildingType[]"),
        ]:
            if key in params:
                query[qkey] = params[key]

        r = requests.get(API_URL, headers=headers, params=query)
        if r.status_code != 200:
            print(f"API error: {r.status_code}", file=sys.stderr)
            break
        data = r.json()
        cards = data.get("cards", [])
        total = data.get("found", 0)
        if not cards:
            break
        fetched += len(cards)

        for c in cards:
            card_id = str(c.get("id"))
            rooms = c.get("rooms") or 0
            if rooms_min and rooms < rooms_min:
                continue
            if rooms_max and rooms > rooms_max:
                continue
            coords = c.get("coordinates")
            if not coords or not coords.get("latitude"):
                continue
            station, dist = nearest_metro(coords["latitude"], coords["longitude"], stations)
            walk_min = round(dist / WALK_SPEED_KMH * 60)
            if max_metro_min and walk_min > max_metro_min:
                continue
            is_new = card_id not in seen
            seen[card_id] = datetime.now().isoformat()
            bd = c.get("buildingData", {})
            entry = {
                "district": bd.get("district", "?"),
                "address": bd.get("address", "?"),
                "rooms": c.get("roomConfiguration", "?"),
                "size_m2": c.get("size", "?"),
                "price": c.get("price", "?"),
                "year": bd.get("year", "?"),
                "metro": station,
                "walk_min": walk_min,
                "url": c.get("url", ""),
                "new": "★" if is_new else "",
            }
            if is_new:
                entry["first_seen"] = datetime.now().strftime("%Y-%m-%d")
            results.append(entry)

        offset += limit
        pages += 1
        print(f"  Fetched {fetched}/{total} from API, {len(results)} matches so far...")
        if fetched >= total:
            break

    results.sort(key=lambda x: x["walk_min"])
    return results


def main():
    p = argparse.ArgumentParser(description="Find apartments near Helsinki metro")
    p.add_argument("--city", default="Helsinki,Espoo", help="Comma-separated cities (default: Helsinki,Espoo)")
    p.add_argument("--price-min", type=int, help="Min price €")
    p.add_argument("--price-max", type=int, help="Max price €")
    p.add_argument("--size-min", type=int, help="Min size m²")
    p.add_argument("--size-max", type=int, help="Max size m²")
    p.add_argument("--rooms-min", type=int, help="Min rooms")
    p.add_argument("--rooms-max", type=int, help="Max rooms")
    p.add_argument("--metro-max", type=float, help="Max walking minutes to metro")
    p.add_argument("--metro-from", default="Matinkylä", help="First metro stop in range (default: Matinkylä)")
    p.add_argument("--metro-to", default="Kalasatama", help="Last metro stop in range (default: Kalasatama)")
    p.add_argument("--max-pages", type=int, default=50, help="Max API pages to scan (default: 50)")
    p.add_argument("--building-type", type=int, help="1=kerrostalo, 2=rivitalo, 4=omakotitalo, 256=paritalo")
    p.add_argument("--all", action="store_true", help="Show all matches, not just new ones")
    p.add_argument("--reset", action="store_true", help="Clear seen listings history")
    args = p.parse_args()

    if args.reset:
        if os.path.exists(SEEN_FILE):
            os.remove(SEEN_FILE)
        print("Seen history cleared.")
        return

    city_codes = {"helsinki": "64,6", "espoo": "39,6", "vantaa": "3,6"}
    locs = []
    for city in args.city.split(","):
        city = city.strip()
        code = city_codes.get(city.lower(), "64,6")
        loc_parts = code.split(",")
        locs.append(f'[{loc_parts[0]},{loc_parts[1]},"{city.title()}"]')

    params = {"locations": f'[{",".join(locs)}]'}
    if args.price_min: params["price_min"] = args.price_min
    if args.price_max: params["price_max"] = args.price_max
    if args.size_min: params["size_min"] = args.size_min
    if args.size_max: params["size_max"] = args.size_max
    if args.rooms_min: params["rooms_min"] = args.rooms_min
    if args.rooms_max: params["rooms_max"] = args.rooms_max
    if args.building_type: params["building_type"] = args.building_type

    print("Fetching auth tokens...")
    tokens = get_auth_tokens()

    stations = get_station_range(args.metro_from, args.metro_to)
    print(f"Metro range: {stations[0][0]} → {stations[-1][0]} ({len(stations)} stops)")

    seen = load_seen()
    prev_count = len(seen)

    print("Fetching apartments...")
    results = fetch_and_filter(tokens, params, args.metro_max, stations,
                               args.rooms_min, args.rooms_max, args.max_pages, seen)

    save_seen(seen)

    new_results = [r for r in results if r["new"] == "★"]
    if new_results:
        append_results_csv(new_results)

    if not args.all:
        display = new_results
    else:
        display = results

    new_count = sum(1 for r in results if r["new"] == "★")
    print(f"\n{len(results)} total matches, {new_count} new (tracking {len(seen)} seen listings)")
    if new_count:
        print(f"New results appended to {RESULTS_FILE}")
    print()

    if not display:
        print("No new apartments since last run." if not args.all else "No apartments found matching criteria.")
        return

    table = [
        [
            r["new"], r["district"], r["address"], r["rooms"], r["size_m2"],
            r["price"], r["year"], f'{r["metro"]} ({r["walk_min"]}min)', r["url"],
        ]
        for r in display
    ]
    print(tabulate(
        table,
        headers=["New", "District", "Address", "Rooms", "m²", "Price", "Year", "Nearest Metro", "URL"],
        tablefmt="simple",
    ))


if __name__ == "__main__":
    main()

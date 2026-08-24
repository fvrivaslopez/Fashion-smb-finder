#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASHION SMB FINDER (No Website)
================================
A personal tool to find fashion/clothing stores without a web presence,
group them by high-density streets, and generate exportable routes.

Usage:  python fashion_smb_finder.py

Dependencies:
    pip install requests folium simplekml
"""

import os
import csv
import json
import time
import math
import webbrowser
import requests
import folium
import simplekml
from datetime import datetime
from collections import defaultdict


# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

CONFIG_FILE   = "config.json"
HISTORY_FILE  = "search_history.csv"
OUTPUT_DIR    = "outputs"

CONFIG_DEFAULT = {
    "google_api_key":         "",
    "search_radius_m":        1000,
    "min_stores_per_street":  1,
    "max_results":            60,
}

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in CONFIG_DEFAULT.items():
            cfg.setdefault(k, v)
        return cfg
    return dict(CONFIG_DEFAULT)

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

CONFIG = load_config()


# ─────────────────────────────────────────────
#  TERMINAL UTILITIES
# ─────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def separator(title: str = ""):
    width = 60
    if title:
        padding = max(width - len(title) - 7, 1)
        print(f"\n{'─'*5} {title.upper()} {'─'*padding}")
    else:
        print("─" * 60)

def pause():
    input("\n  [Press ENTER to continue]")

def color(text: str, code: str = "1;36") -> str:
    """Wraps text in ANSI color codes if the terminal supports it."""
    return f"\033[{code}m{text}\033[0m"

def input_option(minimum: int, maximum: int, message: str = "  ➜ Option: ") -> int:
    while True:
        try:
            v = int(input(message).strip())
            if minimum <= v <= maximum:
                return v
            print(f"  [×] Enter a number between {minimum} and {maximum}")
        except ValueError:
            print(f"  [×] Enter a valid number")

def input_text(message: str, required: bool = False) -> str:
    while True:
        v = input(message).strip()
        if v or not required:
            return v
        print(f"  [×] This field cannot be empty")


# ─────────────────────────────────────────────
#  GEOCODING
# ─────────────────────────────────────────────

def geocode(location: str) -> tuple | None:
    """Converts a place name to (lat, lon)."""
    if CONFIG.get("google_api_key"):
        url    = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address":  location,
            "language": "en",
            "key":      CONFIG["google_api_key"],
        }
        try:
            r    = requests.get(url, params=params, timeout=10)
            data = r.json()
            if data.get("status") == "OK":
                loc = data["results"][0]["geometry"]["location"]
                return loc["lat"], loc["lng"]
            else:
                print(f"  [Geocoding WARNING] {data.get('status')}: {data.get('error_message', '')}")
        except Exception as e:
            print(f"  [Geocoding ERROR] {e}")

    url     = "https://nominatim.openstreetmap.org/search"
    params  = {"q": location, "format": "json", "limit": 1}
    headers = {"User-Agent": "FashionSMBFinder/1.0"}
    try:
        r    = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        print("  [WARNING] Location not found on OpenStreetMap")
    except Exception as e:
        print(f"  [Fallback geocoding ERROR] {e}")
    return None


# ─────────────────────────────────────────────
#  GOOGLE PLACES API SEARCH
# ─────────────────────────────────────────────

FASHION_TYPES = [
    "clothing_store",
    "shoe_store",
    "jewelry_store",
    "shopping_mall",
]

FASHION_KEYWORDS = [
    "clothing store",
    "fashion boutique",
    "women's fashion",
    "men's fashion",
    "fashion accessories",
    "shoe shop",
    "jewelry shop",
    "children's clothing",
    "tailor",
    "outlet fashion",
    "plus size clothing",
    "lingerie",
    "sportswear",
]

# Known chains → always have a website, skip without calling Details
KNOWN_CHAINS = {
    "zara", "mango", "h&m", "hm", "pull&bear", "pull and bear", "pull bear",
    "bershka", "stradivarius", "massimo dutti", "oysho",
    "lefties", "primark", "c&a", "cortefiel", "springfield",
    "women'secret", "women secret", "pedro del hierro",
    "inside", "blanco", "shana", "kiabi",
    "el corte inglés", "corte ingles", "el corte ingles",
    "sfera", "uterqüe", "cos", "uniqlo",
    "nike", "adidas", "puma", "reebok", "new balance",
    "decathlon", "sprinter", "intersport",
    "deichmann", "pikolinos", "camper",
    "panama jack", "superdry", "tommy hilfiger", "calvin klein",
    "guess", "levi's", "levis", "wrangler", "carhartt",
    "skechers", "geox", "gap", "forever 21", "urban outfitters",
    "anthropologie", "abercrombie", "hollister", "express",
}

def _nearby_search_google(lat: float, lon: float, radius: int,
                           place_type: str = None, keyword: str = None) -> list:
    """Google Places Nearby Search with pagination (max 60 results)."""
    url    = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lon}",
        "radius":   radius,
        "language": "en",
        "key":      CONFIG["google_api_key"],
    }
    if place_type:
        params["type"] = place_type
    if keyword:
        params["keyword"] = keyword

    results = []
    page    = 0
    max_pages = 3

    while page < max_pages:
        try:
            r    = requests.get(url, params=params, timeout=15)
            data = r.json()
            status = data.get("status")

            if status == "OK":
                results.extend(data.get("results", []))
            elif status == "ZERO_RESULTS":
                break
            elif status == "INVALID_REQUEST":
                break
            elif status in ("OVER_QUERY_LIMIT", "REQUEST_DENIED"):
                print(f"\n  [Google Places ERROR] {status}: {data.get('error_message', '')}")
                if status == "OVER_QUERY_LIMIT":
                    print("  You have exceeded the daily quota. Wait 24h or configure billing.")
                break
            else:
                print(f"  [WARNING] Unexpected status: {status}")
                break

            next_token = data.get("next_page_token")
            if not next_token:
                break

            page += 1
            time.sleep(2.0)
            params = {"pagetoken": next_token, "key": CONFIG["google_api_key"]}

        except requests.exceptions.Timeout:
            print("  [ERROR] Timeout calling Google Places")
            break
        except Exception as e:
            print(f"  [Google Places call ERROR] {e}")
            break

    return results


def _text_search_google(lat: float, lon: float, radius: int, keyword: str) -> list:
    """Google Places Text Search to catch what Nearby misses."""
    url    = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query":    keyword,
        "location": f"{lat},{lon}",
        "radius":   radius,
        "language": "en",
        "key":      CONFIG["google_api_key"],
    }
    results = []
    page    = 0

    while page < 3:
        try:
            r    = requests.get(url, params=params, timeout=15)
            data = r.json()
            if data.get("status") == "OK":
                results.extend(data.get("results", []))
            else:
                break

            next_token = data.get("next_page_token")
            if not next_token:
                break
            page += 1
            time.sleep(2.0)
            params = {"pagetoken": next_token, "key": CONFIG["google_api_key"]}
        except Exception:
            break

    return results


def _is_known_chain(name: str) -> bool:
    """Returns True if the store belongs to a chain known to have a website."""
    name_lower = name.lower().strip()
    for chain in KNOWN_CHAINS:
        if chain in name_lower:
            return True
    return False


def _get_website_place_details(place_id: str) -> str:
    """Place Details → website. Costs 1 API credit."""
    url    = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields":   "website,url",
        "language": "en",
        "key":      CONFIG["google_api_key"],
    }
    try:
        r    = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("status") == "OK":
            return data.get("result", {}).get("website", "") or ""
    except Exception:
        pass
    return ""


def _normalize_place(place: dict, check_website: bool = True) -> dict | None:
    """Converts a Google Places result to internal format.
       Returns None if the store has a website or is a known chain."""
    name = place.get("name", "Unknown")

    # Quick filter: known chains always have a website
    if _is_known_chain(name):
        return None

    geo = place.get("geometry", {}).get("location", {})
    lat = geo.get("lat")
    lng = geo.get("lng")
    if not lat or not lng:
        return None

    # Extract address
    vicinity = place.get("vicinity", "")
    address = place.get("formatted_address", "") or vicinity

    # Try to extract street name from address
    street = _extract_street(address, name)

    # Types
    types = place.get("types", [])
    primary_type = types[0].replace("_", " ") if types else "fashion"

    # Rating
    rating = place.get("rating", 0)

    # Verify website via Place Details (expensive, only if enabled)
    website = ""
    if check_website and CONFIG.get("google_api_key"):
        place_id = place.get("place_id", "")
        if place_id:
            website = _get_website_place_details(place_id)
            time.sleep(0.05)  # soft rate limiting

    if website:
        return None  # Has website → not a target prospect

    return {
        "id":            place.get("place_id", ""),
        "name":          name,
        "address":       address,
        "street":        street,
        "lat":           lat,
        "lng":           lng,
        "type":          primary_type,
        "rating":        rating,
        "total_ratings": place.get("user_ratings_total", 0),
        "has_website":   bool(website),
    }


def _extract_street(address: str, name: str) -> str:
    """Extracts the street name from a Google-style address."""
    if not address:
        return "Unknown street"

    # Remove house number and city
    address = address.split(",")[0].strip()

    # Normalize street prefixes
    prefixes = [
        "street ", "st ", "avenue ", "ave ", "boulevard ", "blvd ",
        "road ", "rd ", "drive ", "dr ", "lane ", "ln ",
        "place ", "pl ", "court ", "ct ", "way ", "terrace ",
        "close ", "crescent ", "grove ", "square ", "park ",
    ]

    for prefix in prefixes:
        if address.lower().startswith(prefix):
            rest = address[len(prefix):]
            if rest:
                return address  # keep full address
            break

    if address:
        return address
    return "Unknown street"


# ─────────────────────────────────────────────
#  FULL SEARCH
# ─────────────────────────────────────────────

def search_stores(city: str, progress=None) -> list:
    """Searches for fashion stores without a website in a city.
       Returns a list of normalized dicts."""
    if progress:
        progress("Geocoding city...")
    else:
        print("\n  Geocoding city...")

    coords = geocode(city)
    if not coords:
        print(f"  [×] Could not geocode '{city}'")
        return []

    lat, lon = coords
    radius = CONFIG.get("search_radius_m", 1000)
    print(f"\n  📍 {city} → {lat:.4f}, {lon:.4f}  (radius: {radius}m)")
    print(f"  {'─' * 50}")

    # Phase 1: Nearby Search by type
    all_places = []
    used_types = set()

    for i, place_type in enumerate(FASHION_TYPES):
        msg = f"  [{i+1}/{len(FASHION_TYPES)}] Searching {place_type.replace('_',' ')}..."
        if progress:
            progress(msg)
        print(f"\n  {msg}")
        results = _nearby_search_google(lat, lon, radius, place_type=place_type)
        if results:
            print(f"    → {len(results)} results")
            all_places.extend(results)
            used_types.add(place_type)
        time.sleep(0.3)

    # Phase 2: Text Search by keywords (to catch what Nearby misses)
    for i, kw in enumerate(FASHION_KEYWORDS):
        msg = f"  [{i+1}/{len(FASHION_KEYWORDS)}] Searching '{kw}'..."
        if progress:
            progress(msg)
        print(f"\n  {msg}")
        results = _text_search_google(lat, lon, radius, kw)
        if results:
            print(f"    → {len(results)} results")
            all_places.extend(results)
        time.sleep(0.3)

    # Phase 3: Normalize and filter
    print(f"\n  {'─' * 50}")
    print(f"  Total raw results: {len(all_places)}")
    print(f"  Normalizing and filtering (removing chains + stores with website)...")

    # Deduplicate by place_id
    seen = set()
    stores = []
    for p in all_places:
        pid = p.get("place_id", "")
        if pid in seen:
            continue
        seen.add(pid)

        t = _normalize_place(p, check_website=True)
        if t:
            stores.append(t)

    print(f"  ✅ Stores without website found: {len(stores)}")

    # Sort by street for visual grouping
    stores.sort(key=lambda t: t["street"].lower())

    return stores


def group_by_street(stores: list) -> dict:
    """Groups stores by street name. Returns dict {street: [stores]}."""
    groups = defaultdict(list)
    for t in stores:
        groups[t["street"]].append(t)
    return dict(groups)


def high_density_streets(groups: dict, minimum: int = None) -> list:
    """Returns list of (street, stores) sorted by descending density."""
    if minimum is None:
        minimum = CONFIG.get("min_stores_per_street", 1)
    filtered = [(street, ts) for street, ts in groups.items() if len(ts) >= minimum]
    filtered.sort(key=lambda x: len(x[1]), reverse=True)
    return filtered


# ─────────────────────────────────────────────
#  MAP GENERATION
# ─────────────────────────────────────────────

def generate_map(stores: list, name: str, center: tuple = None) -> str:
    """Generates an HTML map with folium and returns the file path."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if center is None and stores:
        avg_lat = sum(t["lat"] for t in stores) / len(stores)
        avg_lon = sum(t["lng"] for t in stores) / len(stores)
        center = (avg_lat, avg_lon)
    elif center is None:
        center = (51.5074, -0.1278)  # London as default

    map_ = folium.Map(location=center, zoom_start=15,
                      tiles="CartoDB Positron")

    # Group by street for color coding
    groups = group_by_street(stores)
    streets_ordered = sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)

    # Assign color per street (densest first)
    colors = [
        "#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#1abc9c",
        "#3498db", "#9b59b6", "#e84393", "#00b894", "#6c5ce7",
        "#fd79a8", "#00cec9", "#a29bfe", "#ff7675", "#fab1a0",
    ]

    for idx, (street, ts) in enumerate(streets_ordered):
        for t in ts:
            popup_text = f"""
            <b>{t['name']}</b><br>
            {t['address']}<br>
            ⭐ {t['rating']} ({t['total_ratings']} ratings)<br>
            <i>{t['type']}</i>
            """
            folium.Marker(
                location=[t["lat"], t["lng"]],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=t["name"],
                icon=folium.Icon(color="red" if idx == 0 else None,
                                 icon_color="white",
                                 icon="shop",
                                 prefix="fa"),
            ).add_to(map_)

    # Heat layer for density (as a named, toggleable overlay)
    heat_data = [[t["lat"], t["lng"]] for t in stores]
    try:
        from folium.plugins import HeatMap
        heat_layer = folium.FeatureGroup(name="🔥 Heat Map (density)", show=True)
        HeatMap(heat_data, radius=25, blur=15).add_to(heat_layer)
        heat_layer.add_to(map_)
        folium.LayerControl(collapsed=False).add_to(map_)
    except ImportError:
        pass  # HeatMap not available, continue without it

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{OUTPUT_DIR}/{name}_{timestamp}.html"
    map_.save(filename)
    full_path = os.path.abspath(filename)
    print(f"\n  🗺️  Map saved: {filename}")
    print(f"      Full path: {full_path}")
    print(f"      Open it in any browser — use the layer switch (top-right)")
    print(f"      to toggle the 🔥 Heat Map on/off.")
    return filename


def generate_kml_route(stores: list, name: str) -> str:
    """Generates a KML file with stores as points and returns the file path."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    kml = simplekml.Kml(name=name)

    if not stores:
        return ""

    doc = kml.newdocument(name="Route")

    # Sort stores for optimal route (nearest neighbour)
    ordered = _sort_optimal_route(stores)

    line_coords = []
    for i, t in enumerate(ordered):
        point = doc.newpoint(
            name=f"{i+1}. {t['name']}",
            description=f"{t['address']}\n{t['type']}\n⭐ {t['rating']}",
            coords=[(t["lng"], t["lat"])],
        )
        point.style.iconstyle.icon.href = (
            "http://maps.google.com/mapfiles/kml/paddle/"
            f"{['red','grn','blu','ylw','pnk','wht'][i % 6]}-circle.png"
        )
        line_coords.append((t["lng"], t["lat"]))

    # Route line
    line = doc.newlinestring(
        name="Recommended route",
        description="Visit order (nearest neighbour)",
        coords=line_coords,
    )
    line.style.linestyle.color = simplekml.Color.red
    line.style.linestyle.width = 3

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{OUTPUT_DIR}/{name}_{timestamp}.kml"
    kml.save(filename)
    print(f"  📍 KML saved: {filename}")
    return filename


def _sort_optimal_route(stores: list) -> list:
    """Sorts stores using nearest neighbour (approximate TSP).
       Starts from the first store in the list."""
    if len(stores) <= 2:
        return stores

    remaining = list(stores)
    route = [remaining.pop(0)]

    while remaining:
        last = route[-1]
        best_dist = float("inf")
        best_idx = 0
        for i, t in enumerate(remaining):
            d = _haversine_dist(last["lat"], last["lng"], t["lat"], t["lng"])
            if d < best_dist:
                best_dist = d
                best_idx = i
        route.append(remaining.pop(best_idx))

    return route


def _haversine_dist(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two points using the Haversine formula."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─────────────────────────────────────────────
#  HISTORY
# ─────────────────────────────────────────────

def save_history(city: str, num_stores: int, files: dict):
    """Saves a search entry to the history CSV."""
    write_header = not os.path.exists(HISTORY_FILE)
    with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["date", "city", "stores", "map", "kml"])
        w.writerow([
            datetime.now().isoformat(),
            city, num_stores,
            files.get("map", ""),
            files.get("kml", ""),
        ])


def show_history():
    """Displays the search history."""
    if not os.path.exists(HISTORY_FILE):
        print("\n  📭 No searches in history yet.")
        return

    with open(HISTORY_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("\n  📭 History is empty.")
        return

    print(f"\n  📋 SEARCH HISTORY ({len(rows)} records)\n")
    print(f"  {'#':<4} {'DATE':<22} {'CITY':<20} {'STORES':<8}")
    print(f"  {'─'*4} {'─'*22} {'─'*20} {'─'*8}")

    for i, row in enumerate(rows, 1):
        date   = row.get("date", "?")[:19]
        city   = row.get("city", "?")
        stores = row.get("stores", "?")
        print(f"  {i:<4} {date:<22} {city:<20} {stores:<8}")

    print()
    idx = input_option(0, len(rows),
                       "  View search details (0 = back): ")
    if idx == 0:
        return

    row = rows[idx - 1]
    print(f"\n  Search details:\n")
    print(f"  • Date:   {row.get('date','?')}")
    print(f"  • City:   {row.get('city','?')}")
    print(f"  • Stores: {row.get('stores','?')}")
    map_  = row.get("map", "")
    kml_  = row.get("kml", "")
    if map_ and os.path.exists(map_):
        print(f"  • Map:    {map_}")
        if input("\n  Open map in browser? (y/N): ").lower() == "y":
            webbrowser.open(os.path.abspath(map_))
    if kml_ and os.path.exists(kml_):
        print(f"  • KML:    {kml_}")
    pause()


# ─────────────────────────────────────────────
#  SCREENS / MENUS
# ─────────────────────────────────────────────

def welcome_screen():
    clear()
    print(color(f"""
╔══════════════════════════════════════════════════════════════╗
║           FASHION SMB FINDER (No Website)                  ║
║   Find fashion/clothing stores with no web presence in     ║
║   your city, grouped by high-density streets.              ║
╚══════════════════════════════════════════════════════════════╝
""", "1;36"))

    if not CONFIG.get("google_api_key"):
        print(color("  ⚠️  GOOGLE PLACES API KEY NOT CONFIGURED", "1;33"))
        print("  Most features require an API Key.")
        print("  Go to Option 5 → Configuration to set it up.\n")


def main_menu():
    welcome_screen()
    print("  What would you like to do?\n")
    print("   1) 🔍  Search stores without website in a city")
    print("   2) 🗺️   View latest generated routes")
    print("   3) 📋  Search history")
    print("   4) ❓  How to get your Google API Key")
    print("   5) 🔥  How maps & heat maps work (and how to get them)")
    print("   6) ⚙️   Configuration")
    print("   7) 🚪  Exit\n")

    option = input_option(1, 7)

    if option == 1:
        search_menu()
    elif option == 2:
        routes_menu()
    elif option == 3:
        show_history()
        main_menu()
    elif option == 4:
        how_to_get_api_key()
    elif option == 5:
        how_maps_and_heatmaps_work()
    elif option == 6:
        config_menu()
    elif option == 7:
        print(color("\n  Goodbye! 🚀\n", "1;33"))
        return


def search_menu():
    clear()
    separator("NEW SEARCH")
    print()
    city = input_text("  City to explore: ", required=True)

    if not CONFIG.get("google_api_key"):
        print("\n  [×] No API Key configured.")
        print("  Set it up in Option 5 or see the guide in Option 4.")
        pause()
        main_menu()
        return

    print(f"\n  Search radius: {CONFIG['search_radius_m']}m")
    print(f"  Min stores per street: {CONFIG['min_stores_per_street']}")
    print(f"  Max results: {CONFIG['max_results']}")
    print()

    if input("  Start search? (Y/n): ").lower() == "n":
        main_menu()
        return

    # ---- SEARCH ----
    start_time = time.time()
    stores = search_stores(city)

    if not stores:
        print(f"\n  😕 No fashion stores without a website found in '{city}'.")
        print("  Try:")
        print("    • A larger city")
        print("    • A bigger search radius (Configuration)")
        print("    • Checking that your API Key works")
        pause()
        save_history(city, 0, {})
        main_menu()
        return

    elapsed = time.time() - start_time
    groups  = group_by_street(stores)
    dense_streets = high_density_streets(groups)

    # ---- RESULTS ----
    clear()
    separator(f"RESULTS: {city}")
    print(f"\n  ⏱  {elapsed:.1f}s")
    print(f"  🏪  {len(stores)} stores without website found")
    print(f"  📍  {len(groups)} distinct streets")
    print(f"  📊  {len(dense_streets)} streets with ≥{CONFIG['min_stores_per_street']} stores\n")

    separator("TOP STREETS BY DENSITY")
    print(f"\n  {'#':<4} {'STORES':<8} {'STREET'}")
    print(f"  {'─'*4} {'─'*8} {'─'*40}")
    for i, (street, ts) in enumerate(dense_streets[:20], 1):
        print(f"  {i:<4} {len(ts):<8} {street}")

    if len(dense_streets) > 20:
        print(f"  ... and {len(dense_streets) - 20} more streets")

    # Street detail summary
    separator("STORES BY STREET (detail)")
    for street, ts in dense_streets[:10]:
        print(f"\n  📍 {color(street, '1;33')} ({len(ts)} stores)")
        for t in ts[:5]:
            stars = "⭐" * max(1, round(t["rating"])) if t["rating"] else ""
            print(f"    • {t['name']:30s} {stars}")
        if len(ts) > 5:
            print(f"    ... and {len(ts)-5} more")

    # ---- EXPORT ----
    separator("EXPORT RESULTS")
    print(f"\n  a) 🗺️   Generate interactive map (HTML)")
    print(f"  b) 📍  Generate KML route (Google Earth / Maps)")
    print(f"  c) 📄  Export list to CSV")
    print(f"  d) 🚀  Do everything")
    print(f"  e) ↩️   Back to menu\n")

    action = input_text("  What do you want to generate? [a/b/c/d/e]: ").lower()
    generated_files = {}

    if action in ("a", "d"):
        file_name = city.lower().replace(" ", "_")
        map_path = generate_map(stores, file_name, None)
        generated_files["map"] = map_path

    if action in ("b", "d"):
        file_name = f"route_{city.lower().replace(' ', '_')}"
        kml_path = generate_kml_route(stores, file_name)
        generated_files["kml"] = kml_path

    if action in ("c", "d"):
        csv_path = export_csv(stores, city)
        generated_files["csv"] = csv_path

    # Save to history
    save_history(city, len(stores), generated_files)

    # Open map if generated
    if generated_files.get("map") and input("\n  Open map in browser? (y/N): ").lower() == "y":
        webbrowser.open(os.path.abspath(generated_files["map"]))

    print()
    pause()
    main_menu()


def routes_menu():
    clear()
    separator("GENERATED ROUTES")

    if not os.path.exists(OUTPUT_DIR):
        print("\n  📭 No routes generated yet.")
        print("  Run a search first (Option 1).")
        pause()
        main_menu()
        return

    files = os.listdir(OUTPUT_DIR)
    if not files:
        print("\n  📭 No files in the 'outputs/' folder.")
        pause()
        main_menu()
        return

    maps = [f for f in files if f.endswith(".html")]
    kmls = [f for f in files if f.endswith(".kml")]
    csvs = [f for f in files if f.endswith(".csv")]

    print(f"\n  🗺️  HTML Maps: {len(maps)}")
    for m in maps[-10:]:
        print(f"     • {m}")

    print(f"\n  📍 KML Routes: {len(kmls)}")
    for k in kmls[-10:]:
        print(f"     • {k}")

    print(f"\n  📄 CSVs: {len(csvs)}")
    for c in csvs[-10:]:
        print(f"     • {c}")

    print()
    if input("  Open outputs folder? (y/N): ").lower() == "y":
        os.startfile(os.path.abspath(OUTPUT_DIR)) if os.name == "nt" else \
            webbrowser.open(OUTPUT_DIR)

    print()
    if maps and input("  Open latest map? (y/N): ").lower() == "y":
        latest = sorted(maps)[-1]
        webbrowser.open(os.path.abspath(os.path.join(OUTPUT_DIR, latest)))

    pause()
    main_menu()


def export_csv(stores: list, city: str) -> str:
    """Exports the store list to CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = city.lower().replace(" ", "_")
    filename = f"{OUTPUT_DIR}/{file_name}_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=[
            "name", "address", "street", "lat", "lng",
            "type", "rating", "total_ratings",
        ])
        w.writeheader()
        for t in stores:
            w.writerow({
                "name":          t["name"],
                "address":       t["address"],
                "street":        t["street"],
                "lat":           t["lat"],
                "lng":           t["lng"],
                "type":          t["type"],
                "rating":        t["rating"],
                "total_ratings": t["total_ratings"],
            })

    print(f"\n  📄 CSV saved: {filename}")
    return filename


def config_menu():
    clear()
    separator("CONFIGURATION")

    print(f"""
  {'1)':<5} Google Places API Key:   {color(CONFIG['google_api_key'][:20] + '…' if CONFIG['google_api_key'] else '(empty)', '1;33' if not CONFIG['google_api_key'] else '1;32')}
  {'2)':<5} Search radius:          {CONFIG['search_radius_m']}m
  {'3)':<5} Min. stores per street: {CONFIG['min_stores_per_street']}
  {'4)':<5} ← Back to main menu
""")

    option = input_option(1, 4, "  What do you want to change? ")

    if option == 1:
        new_key = input_text("  Enter your Google Places API Key: ", required=True)
        CONFIG["google_api_key"] = new_key
        save_config(CONFIG)
        print(color("  ✅ API Key saved successfully", "1;32"))
        pause()
        config_menu()

    elif option == 2:
        try:
            val = int(input_text(f"  Radius in meters [{CONFIG['search_radius_m']}]: ") or CONFIG['search_radius_m'])
            CONFIG["search_radius_m"] = max(100, min(50000, val))
            save_config(CONFIG)
            print(f"  ✅ Radius updated to {CONFIG['search_radius_m']}m")
        except ValueError:
            print("  [×] Invalid value")
        pause()
        config_menu()

    elif option == 3:
        try:
            val = int(input_text(f"  Minimum [{CONFIG['min_stores_per_street']}]: ") or CONFIG['min_stores_per_street'])
            CONFIG["min_stores_per_street"] = max(1, val)
            save_config(CONFIG)
            print(f"  ✅ Minimum updated to {CONFIG['min_stores_per_street']}")
        except ValueError:
            print("  [×] Invalid value")
        pause()
        config_menu()

    elif option == 4:
        main_menu()


def how_to_get_api_key():
    clear()
    separator("HOW TO GET YOUR GOOGLE PLACES API KEY")
    print(color("""
  Google gives $200 FREE credit every month.
  For personal use you will never reach that limit.
  They ask for a card only to verify identity, NOT to charge you.
  You can set a spending limit of $0 so it is impossible
  for them to charge you anything.
""", "1;33"))
    print("""
  STEP 1 — Create a Google Cloud account
  ──────────────────────────────────────
  · Go to: https://console.cloud.google.com/
  · Sign in with your Google account (Gmail)
  · Accept the terms of service

  STEP 2 — Create a new project
  ──────────────────────────────────────
  · Click the project menu (top left)
  · Click "New project"
  · Give it a name (e.g. "FashionSMBFinder")
  · Click "Create"

  STEP 3 — Enable billing (required, free)
  ──────────────────────────────────────────────────
  · Menu (≡) → "Billing"
  · "Link a billing account"
  · Create your account and add a card
  · Google verifies with $1 which is refunded within 24h

  STEP 4 — Set a spending limit (optional but recommended)
  ────────────────────────────────────────────────────────
  · Billing → "Budgets & alerts"
  · "Create budget"
  · Amount: $1 → enable "Block usage when limit is exceeded"

  STEP 5 — Enable Google Places API
  ──────────────────────────────────
  · https://console.cloud.google.com/apis/library
  · Search "Places API" → "Enable"

  STEP 6 — Create API Key
  ──────────────────────
  · https://console.cloud.google.com/apis/credentials
  · "+ Create credentials" → "API key"
  · Copy it. Recommended: restrict it to Places API only.

  STEP 7 — Configure in this program
  ─────────────────────────────────
  · Return to this program → Option 5 (Configuration)
  · Option 1 → paste your API Key
""")
    input("\n  [Press ENTER to return to menu]")
    main_menu()


def how_maps_and_heatmaps_work():
    clear()
    separator("MAPS & HEAT MAPS — HOW THEY WORK")
    print(f"""
  WHAT GETS CREATED
  ──────────────────
  Every time you run a search and choose to export a map
  (Option 1 → export menu → "a" or "d"), the app builds ONE
  interactive HTML file that contains BOTH:

    • 📍 Store markers   — every store found, clickable, grouped
                            and color-coded by street.
    • 🔥 Heat map layer  — a red/orange/yellow overlay showing
                            WHERE stores are most concentrated.

  These are not two separate files — the heat map is a LAYER
  inside the same map file.

  WHERE THE FILE LIVES
  ─────────────────────
  It is saved automatically to your computer here:

    {color(os.path.abspath(OUTPUT_DIR), '1;36')}/<city>_<timestamp>.html

  That IS the "download" — nothing else to click. As soon as it's
  generated it already exists as a normal file on your disk.

  HOW TO OPEN IT
  ────────────────
  • From this app: after generating, answer "y" when asked
    "Open map in browser?" — or use Option 2 (View latest
    generated routes) any time later.
  • Manually: go to the '{OUTPUT_DIR}/' folder and double-click
    the .html file — it opens in your default web browser.

  HOW TO SEE / TOGGLE THE HEAT MAP
  ───────────────────────────────────
  Once the map is open in your browser, look at the small
  layer-control box in the TOP-RIGHT corner. It lists:

    ☑ 🔥 Heat Map (density)

  Check/uncheck it to show or hide the heat overlay on top of
  the store markers.

  MOVING / SHARING THE MAP OR HEAT MAP
  ───────────────────────────────────────
  The .html file is fully self-contained — copy it, email it,
  or move it to another computer like any normal file, and it
  will still open and work with no internet connection needed
  (only the base map tiles need internet to load images).

  Want an image (PNG) instead of an interactive file?
  Open the .html in your browser, then use your browser's
  "Print → Save as PDF" or a screenshot tool to capture it.
""")
    input("\n  [Press ENTER to return to menu]")
    main_menu()


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(color("\n\n  👋 Goodbye!\n", "1;33"))

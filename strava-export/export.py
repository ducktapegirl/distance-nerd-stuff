"""
Strava Activity Exporter
Exports all Strava activities to a CSV file.

Setup:
  1. Copy .env.example to .env and fill in your client_id and client_secret
     from https://www.strava.com/settings/api
  2. pip install -r requirements.txt
  3. python export.py
"""

import csv
import json
import os
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
TOKEN_FILE = ".strava_tokens.json"
REDIRECT_URI = "http://localhost:8000/callback"
AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
API_BASE = "https://www.strava.com/api/v3"

# Fields to include in the CSV (in order)
CSV_FIELDS = [
    "id", "name", "type", "sport_type", "start_date_local",
    "distance_km", "moving_time_min", "elapsed_time_min",
    "total_elevation_gain_m", "average_speed_kmh", "max_speed_kmh",
    "average_heartrate", "max_heartrate", "average_watts", "max_watts",
    "suffer_score", "calories", "average_cadence",
    "start_latlng", "city", "state", "country",
    "gear_id", "trainer", "commute", "manual",
    "achievement_count", "kudos_count", "comment_count", "athlete_count",
    "pr_count", "map_id",
]


# -- OAuth -------------------------------------------------------------------

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return json.load(f)
    return None


def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)


def refresh_access_token(refresh_token):
    resp = requests.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    })
    resp.raise_for_status()
    return resp.json()


def get_valid_access_token():
    tokens = load_tokens()

    if tokens:
        if tokens["expires_at"] <= time.time() + 60:
            print("Refreshing access token...")
            tokens = refresh_access_token(tokens["refresh_token"])
            save_tokens(tokens)
        return tokens["access_token"]

    # First-time auth — open browser and capture the callback
    return authorize_via_browser()


def authorize_via_browser():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise SystemExit(
            "Missing STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET.\n"
            "Copy .env.example to .env and fill in your credentials."
        )

    auth_code = {"value": None}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            auth_code["value"] = params.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Authorized! You can close this tab.</h2>")

        def log_message(self, *args):
            pass  # suppress request logs

    params = urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": "activity:read_all",
    })
    url = f"{AUTH_URL}?{params}"
    print(f"\nOpening Strava authorization in your browser...")
    print(f"If it doesn't open automatically, visit:\n  {url}\n")
    webbrowser.open(url)

    server = HTTPServer(("localhost", 8000), CallbackHandler)
    server.handle_request()  # wait for exactly one callback

    code = auth_code["value"]
    if not code:
        raise SystemExit("Authorization failed — no code received.")

    resp = requests.post(TOKEN_URL, data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    tokens = resp.json()
    save_tokens(tokens)
    print("Authorized successfully.\n")
    return tokens["access_token"]


# -- API helpers -------------------------------------------------------------

def get_all_activities(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    activities = []
    page = 1

    while True:
        resp = requests.get(
            f"{API_BASE}/athlete/activities",
            headers=headers,
            params={"per_page": 200, "page": page},
        )
        if resp.status_code == 429:
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - int(time.time()), 10)
            print(f"Rate limited — waiting {wait}s...")
            time.sleep(wait)
            continue

        resp.raise_for_status()
        page_data = resp.json()
        if not page_data:
            break

        activities.extend(page_data)
        print(f"  Fetched page {page} ({len(page_data)} activities, {len(activities)} total)")
        page += 1

    return activities


# -- CSV helpers -------------------------------------------------------------

def metres_to_km(m):
    return round(m / 1000, 3) if m else None

def seconds_to_min(s):
    return round(s / 60, 2) if s else None

def ms_to_kmh(ms):
    return round(ms * 3.6, 2) if ms else None

def flatten(activity):
    """Map a raw Strava activity dict to the CSV row dict."""
    loc = activity.get("start_latlng") or []
    location_details = activity.get("location_city") or activity.get("location_country")

    return {
        "id":                       activity.get("id"),
        "name":                     activity.get("name"),
        "type":                     activity.get("type"),
        "sport_type":               activity.get("sport_type"),
        "start_date_local":         activity.get("start_date_local", "").replace("T", " ").replace("Z", ""),
        "distance_km":              metres_to_km(activity.get("distance")),
        "moving_time_min":          seconds_to_min(activity.get("moving_time")),
        "elapsed_time_min":         seconds_to_min(activity.get("elapsed_time")),
        "total_elevation_gain_m":   activity.get("total_elevation_gain"),
        "average_speed_kmh":        ms_to_kmh(activity.get("average_speed")),
        "max_speed_kmh":            ms_to_kmh(activity.get("max_speed")),
        "average_heartrate":        activity.get("average_heartrate"),
        "max_heartrate":            activity.get("max_heartrate"),
        "average_watts":            activity.get("average_watts"),
        "max_watts":                activity.get("max_watts"),
        "suffer_score":             activity.get("suffer_score"),
        "calories":                 activity.get("calories"),
        "average_cadence":          activity.get("average_cadence"),
        "start_latlng":             f"{loc[0]},{loc[1]}" if len(loc) == 2 else None,
        "city":                     activity.get("location_city"),
        "state":                    activity.get("location_state"),
        "country":                  activity.get("location_country"),
        "gear_id":                  activity.get("gear_id"),
        "trainer":                  activity.get("trainer"),
        "commute":                  activity.get("commute"),
        "manual":                   activity.get("manual"),
        "achievement_count":        activity.get("achievement_count"),
        "kudos_count":              activity.get("kudos_count"),
        "comment_count":            activity.get("comment_count"),
        "athlete_count":            activity.get("athlete_count"),
        "pr_count":                 activity.get("pr_count"),
        "map_id":                   (activity.get("map") or {}).get("id"),
    }


def write_csv(activities, output_path):
    rows = [flatten(a) for a in activities]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} activities to {output_path}")


# -- Main --------------------------------------------------------------------

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"strava_activities_{timestamp}.csv"

    print("=== Strava Activity Exporter ===\n")
    access_token = get_valid_access_token()

    print("Fetching activities...")
    activities = get_all_activities(access_token)
    print(f"\nTotal activities: {len(activities)}")

    write_csv(activities, output_path)


if __name__ == "__main__":
    main()

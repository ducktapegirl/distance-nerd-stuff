"""
Strava Comprehensive Data Fetcher

Fetches all available Strava data to local files:
  data/athlete.json             athlete profile
  data/gear.json                gear details keyed by gear_id
  data/activities.csv           enriched activity rows (detail endpoint)
  data/segment_efforts.csv      all segment efforts across all activities
  data/streams/{id}.csv         GPS, HR, power time-series per activity
  data/laps/{id}.csv            lap splits per activity

Rate limits: 100 requests / 15 min, 1000 / day.
The script tracks its own request rate and sleeps automatically to stay
under the 15-minute cap. It is safe to interrupt and resume — already-
fetched activities are skipped based on the presence of their stream file.

Usage:
  python fetch.py                  # fetch everything
  python fetch.py --limit 5        # test with 5 most-recent activities
  python fetch.py --since 2025-01-01  # only activities on/after that date

Auth:
  Reuses ../strava-export/.strava_tokens.json (same credentials).
  If not found, falls back to .strava_tokens.json in this directory.
  Set STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET in ../strava-export/.env
  or a local .env file.
"""

import argparse
import collections
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from tqdm import tqdm

from weather import fetch_weather_temp

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Try parent strava-export dir first, then local
_HERE = Path(__file__).parent
for _env in [_HERE / "../strava-export/.env", _HERE / ".env"]:
    if _env.exists():
        load_dotenv(_env)
        break

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")

TOKEN_FILE_CANDIDATES = [
    _HERE / "../strava-export/.strava_tokens.json",
    _HERE / ".strava_tokens.json",
]
TOKEN_URL = "https://www.strava.com/oauth/token"
API_BASE = "https://www.strava.com/api/v3"

DATA_DIR = _HERE / "data"
STREAMS_DIR = DATA_DIR / "streams"
LAPS_DIR = DATA_DIR / "laps"

STREAM_KEYS = "time,latlng,distance,altitude,velocity_smooth,heartrate,cadence,watts,temp,moving,grade_smooth"

ACTIVITIES_FIELDS = [
    "id", "name", "type", "sport_type", "start_date_local",
    "distance_km", "moving_time_min", "elapsed_time_min",
    "total_elevation_gain_m", "elev_high_m", "elev_low_m",
    "average_speed_kmh", "max_speed_kmh",
    "average_heartrate", "max_heartrate",
    "average_watts", "max_watts", "device_watts",
    "suffer_score", "calories", "average_cadence", "average_temp_c",
    "workout_type",
    "start_latlng", "city", "state", "country",
    "gear_id",
    "trainer", "commute", "manual", "has_heartrate",
    "achievement_count", "kudos_count", "comment_count",
    "athlete_count", "pr_count",
    "photos_count", "total_photo_count",
    "description",
    "device_name",
    "map_id",
]

SEGMENT_EFFORTS_FIELDS = [
    "activity_id", "sport_type", "segment_id", "segment_name",
    "segment_city", "segment_state",
    "segment_distance_m", "segment_avg_grade",
    "segment_start_lat", "segment_start_lng",
    "effort_id", "elapsed_time_s", "moving_time_s",
    "start_date_local",
    "average_heartrate", "max_heartrate",
    "average_watts", "device_watts", "average_cadence",
    "kom_rank", "pr_rank",
]

LAP_FIELDS = [
    "activity_id", "lap_index", "name",
    "elapsed_time_s", "moving_time_s", "distance_km",
    "average_speed_kmh", "max_speed_kmh",
    "average_heartrate", "max_heartrate",
    "average_watts", "average_cadence",
    "total_elevation_gain_m",
    "start_date_local",
]

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _find_token_file():
    for p in TOKEN_FILE_CANDIDATES:
        if p.exists():
            return p
    return TOKEN_FILE_CANDIDATES[-1]  # will be created here if needed


def load_tokens():
    p = _find_token_file()
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return None


def save_tokens(tokens):
    p = _find_token_file()
    with open(p, "w") as f:
        json.dump(tokens, f, indent=2)


def get_access_token():
    tokens = load_tokens()
    if not tokens:
        raise SystemExit(
            "No token file found. Run strava-export/export.py first to authorise."
        )
    if tokens.get("expires_at", 0) <= time.time() + 60:
        print("Refreshing Strava access token...")
        resp = requests.post(TOKEN_URL, data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
        })
        resp.raise_for_status()
        tokens = resp.json()
        save_tokens(tokens)
    return tokens["access_token"]


# ---------------------------------------------------------------------------
# Rate-limit-aware request helper
# ---------------------------------------------------------------------------

class RateLimiter:
    """Tracks requests in a 15-minute sliding window and sleeps as needed."""

    WINDOW = 15 * 60   # seconds
    CAP = 95           # leave 5 req headroom below the 100/15-min limit

    def __init__(self):
        self._timestamps = collections.deque()

    def _prune(self):
        cutoff = time.time() - self.WINDOW
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def wait_if_needed(self):
        self._prune()
        if len(self._timestamps) >= self.CAP:
            oldest = self._timestamps[0]
            sleep_until = oldest + self.WINDOW + 1
            wait = max(sleep_until - time.time(), 0)
            if wait > 0:
                print(f"\nRate limit reached — sleeping {wait:.0f}s "
                      f"({wait/60:.1f} min)...", flush=True)
                time.sleep(wait)
            self._prune()

    def record(self):
        self._timestamps.append(time.time())


_rate = RateLimiter()


def api_get(path, token, params=None, *, retries=3):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE}{path}"
    for attempt in range(retries):
        _rate.wait_if_needed()
        resp = requests.get(url, headers=headers, params=params)
        _rate.record()
        if resp.status_code == 429:
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - int(time.time()), 10)
            print(f"\n429 rate limit — waiting {wait}s...", flush=True)
            time.sleep(wait)
            continue
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Failed after {retries} retries: {url}")


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_all_activities(token):
    activities, page = [], 1
    while True:
        page_data = api_get("/athlete/activities", token,
                            params={"per_page": 200, "page": page})
        if not page_data:
            break
        activities.extend(page_data)
        page += 1
    return activities


def ms_to_kmh(v):
    return round(v * 3.6, 2) if v is not None else None

def m_to_km(v):
    return round(v / 1000, 3) if v is not None else None

def s_to_min(v):
    return round(v / 60, 2) if v is not None else None

def fmt_dt(s):
    return s.replace("T", " ").replace("Z", "") if s else None

def latlng_str(ll):
    return f"{ll[0]},{ll[1]}" if ll and len(ll) == 2 else None


def flatten_activity(d):
    return {
        "id":                    d.get("id"),
        "name":                  d.get("name"),
        "type":                  d.get("type"),
        "sport_type":            d.get("sport_type"),
        "start_date_local":      fmt_dt(d.get("start_date_local")),
        "distance_km":           m_to_km(d.get("distance")),
        "moving_time_min":       s_to_min(d.get("moving_time")),
        "elapsed_time_min":      s_to_min(d.get("elapsed_time")),
        "total_elevation_gain_m": d.get("total_elevation_gain"),
        "elev_high_m":           d.get("elev_high"),
        "elev_low_m":            d.get("elev_low"),
        "average_speed_kmh":     ms_to_kmh(d.get("average_speed")),
        "max_speed_kmh":         ms_to_kmh(d.get("max_speed")),
        "average_heartrate":     d.get("average_heartrate"),
        "max_heartrate":         d.get("max_heartrate"),
        "average_watts":         d.get("average_watts"),
        "max_watts":             d.get("max_watts"),
        "device_watts":          d.get("device_watts"),
        "suffer_score":          d.get("suffer_score"),
        "calories":              d.get("calories"),
        "average_cadence":       d.get("average_cadence"),
        "average_temp_c":        d.get("average_temp"),
        "workout_type":          d.get("workout_type"),
        "start_latlng":          latlng_str(d.get("start_latlng")),
        "city":                  d.get("location_city"),
        "state":                 d.get("location_state"),
        "country":               d.get("location_country"),
        "gear_id":               d.get("gear_id"),
        "trainer":               d.get("trainer"),
        "commute":               d.get("commute"),
        "manual":                d.get("manual"),
        "has_heartrate":         d.get("has_heartrate"),
        "achievement_count":     d.get("achievement_count"),
        "kudos_count":           d.get("kudos_count"),
        "comment_count":         d.get("comment_count"),
        "athlete_count":         d.get("athlete_count"),
        "pr_count":              d.get("pr_count"),
        "photos_count":          d.get("photos", {}).get("count") if d.get("photos") else d.get("photos_count"),
        "total_photo_count":     d.get("total_photo_count"),
        "description":           (d.get("description") or "").replace("\n", " "),
        "device_name":           d.get("device_name"),
        "map_id":                (d.get("map") or {}).get("id"),
    }


def extract_segment_efforts(activity_id, detail):
    rows = []
    for effort in detail.get("segment_efforts") or []:
        seg = effort.get("segment") or {}
        start_ll = seg.get("start_latlng") or []
        rows.append({
            "activity_id":       activity_id,
            "sport_type":        detail.get("sport_type"),
            "segment_id":        seg.get("id"),
            "segment_name":      seg.get("name"),
            "segment_city":      seg.get("city"),
            "segment_state":     seg.get("state"),
            "segment_distance_m": seg.get("distance"),
            "segment_avg_grade": seg.get("average_grade"),
            "segment_start_lat": start_ll[0] if len(start_ll) >= 2 else None,
            "segment_start_lng": start_ll[1] if len(start_ll) >= 2 else None,
            "effort_id":         effort.get("id"),
            "elapsed_time_s":    effort.get("elapsed_time"),
            "moving_time_s":     effort.get("moving_time"),
            "start_date_local":  fmt_dt(effort.get("start_date_local")),
            "average_heartrate": effort.get("average_heartrate"),
            "max_heartrate":     effort.get("max_heartrate"),
            "average_watts":     effort.get("average_watts"),
            "device_watts":      effort.get("device_watts"),
            "average_cadence":   effort.get("average_cadence"),
            "kom_rank":          effort.get("kom_rank"),
            "pr_rank":           effort.get("pr_rank"),
        })
    return rows


def flatten_streams(raw_streams):
    """Convert Strava stream response to a list of row dicts.

    Handles both list format [{type, data}, ...] and keyed dict format
    {type: {data: [...]}, ...} — Strava returns the latter when key_by_type=true.
    """
    if isinstance(raw_streams, dict):
        by_type = {k: v["data"] for k, v in raw_streams.items() if isinstance(v, dict)}
    else:
        by_type = {s["type"]: s["data"] for s in raw_streams}
    n = max((len(v) for v in by_type.values()), default=0)

    def _si(key, i):
        """Safe stream index — None when stream is absent or shorter than others."""
        lst = by_type.get(key, [])
        return lst[i] if i < len(lst) else None

    rows = []
    latlng = by_type.get("latlng", [])
    for i in range(n):
        ll = latlng[i] if i < len(latlng) else None
        rows.append({
            "t":           _si("time", i),
            "lat":         ll[0] if ll else None,
            "lng":         ll[1] if ll else None,
            "distance_m":  _si("distance", i),
            "altitude_m":  _si("altitude", i),
            "velocity_ms": _si("velocity_smooth", i),
            "heartrate":   _si("heartrate", i),
            "cadence":     _si("cadence", i),
            "watts":       _si("watts", i),
            "temp_c":      _si("temp", i),
            "moving":      _si("moving", i),
            "grade_pct":   _si("grade_smooth", i),
        })
    return rows


def flatten_lap(activity_id, lap):
    return {
        "activity_id":           activity_id,
        "lap_index":             lap.get("lap_index"),
        "name":                  lap.get("name"),
        "elapsed_time_s":        lap.get("elapsed_time"),
        "moving_time_s":         lap.get("moving_time"),
        "distance_km":           m_to_km(lap.get("distance")),
        "average_speed_kmh":     ms_to_kmh(lap.get("average_speed")),
        "max_speed_kmh":         ms_to_kmh(lap.get("max_speed")),
        "average_heartrate":     lap.get("average_heartrate"),
        "max_heartrate":         lap.get("max_heartrate"),
        "average_watts":         lap.get("average_watts"),
        "average_cadence":       lap.get("average_cadence"),
        "total_elevation_gain_m": lap.get("total_elevation_gain"),
        "start_date_local":      fmt_dt(lap.get("start_date_local")),
    }


# ---------------------------------------------------------------------------
# CSV helpers (append-friendly)
# ---------------------------------------------------------------------------

def csv_append(path, rows, fieldnames):
    if not rows:
        return
    write_header = not path.exists()
    if not write_header:
        # Guard against schema drift: appending rows under a stale header
        # silently corrupts the file (see KNOWN-ISSUES.md, 2026-06-10).
        with open(path, newline="", encoding="utf-8") as f:
            existing = next(csv.reader(f), [])
        if existing != fieldnames:
            raise SystemExit(
                f"{path.name}: existing header has {len(existing)} cols but the "
                f"schema has {len(fieldnames)} - migrate the file before fetching"
            )
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerows(rows)


def write_stream_csv(path, rows):
    fieldnames = ["t", "lat", "lng", "distance_m", "altitude_m",
                  "velocity_ms", "heartrate", "cadence", "watts",
                  "temp_c", "moving", "grade_pct"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_lap_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LAP_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Fetch comprehensive Strava data.")
    p.add_argument("--limit", type=int, default=None,
                   help="Only process the N most-recent activities (for testing).")
    p.add_argument("--since", type=str, default=None,
                   help="Only process activities on or after YYYY-MM-DD.")
    return p.parse_args()


def main():
    args = parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STREAMS_DIR.mkdir(exist_ok=True)
    LAPS_DIR.mkdir(exist_ok=True)

    token = get_access_token()

    # --- Athlete profile ---
    athlete_path = DATA_DIR / "athlete.json"
    if not athlete_path.exists():
        print("Fetching athlete profile...")
        athlete = api_get("/athlete", token)
        athlete_path.write_text(json.dumps(athlete, indent=2))
        print(f"  Saved {athlete_path}")
    else:
        print(f"  {athlete_path} already exists, skipping.")

    # --- Activity list ---
    print("\nFetching activity list...")
    all_activities = fetch_all_activities(token)
    print(f"  {len(all_activities)} activities total.")

    # Apply --since filter
    if args.since:
        since_dt = datetime.fromisoformat(args.since)
        all_activities = [
            a for a in all_activities
            if datetime.fromisoformat(
                a["start_date_local"].replace("Z", "+00:00")
            ).replace(tzinfo=None) >= since_dt
        ]
        print(f"  {len(all_activities)} activities after {args.since}.")

    # Apply --limit (newest first from the list)
    if args.limit:
        all_activities = all_activities[: args.limit]
        print(f"  Limited to {len(all_activities)} activities (--limit).")

    # Determine which are already fully fetched
    to_fetch = [a for a in all_activities
                if not (STREAMS_DIR / f"{a['id']}.csv").exists()]
    already_done = len(all_activities) - len(to_fetch)
    if already_done:
        print(f"  {already_done} already fetched, skipping.")
    print(f"  {len(to_fetch)} to fetch.\n")

    # --- Per-activity detail + streams + laps ---
    gear_ids = set()
    activities_path = DATA_DIR / "activities.csv"
    segments_path = DATA_DIR / "segment_efforts.csv"

    # Pre-load already-written activity IDs and gear IDs from any existing CSV.
    # This prevents duplicate rows if the script crashed after writing the row
    # but before writing the stream file (the normal completion marker).
    detail_written_ids = set()
    if activities_path.exists():
        with open(activities_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("id"):
                    detail_written_ids.add(str(row["id"]))
                if row.get("gear_id"):
                    gear_ids.add(row["gear_id"])

    for activity in tqdm(to_fetch, unit="activity", ncols=80):
        aid = activity["id"]

        # Detail + segments — skip if already written (crash-recovery guard)
        if str(aid) not in detail_written_ids:
            detail = api_get(f"/activities/{aid}", token)
            if detail is None:
                tqdm.write(f"  Skipping {aid} (404)")
                continue

            if detail.get("gear_id"):
                gear_ids.add(detail["gear_id"])

            act_row = flatten_activity(detail)

            # Fill temperature from Open-Meteo when the device didn't record it
            if not act_row.get("average_temp_c") and act_row.get("start_latlng"):
                parts = str(act_row["start_latlng"]).split(",")
                if len(parts) == 2:
                    try:
                        lat = float(parts[0].strip())
                        lon = float(parts[1].strip())
                        dt_local = datetime.strptime(
                            str(act_row["start_date_local"])[:19], "%Y-%m-%d %H:%M:%S"
                        )
                        temp = fetch_weather_temp(lat, lon, dt_local)
                        if temp is not None:
                            act_row["average_temp_c"] = temp
                    except (ValueError, AttributeError):
                        pass

            csv_append(activities_path, [act_row], ACTIVITIES_FIELDS)
            detail_written_ids.add(str(aid))

            seg_rows = extract_segment_efforts(aid, detail)
            if seg_rows:
                csv_append(segments_path, seg_rows, SEGMENT_EFFORTS_FIELDS)

        # Streams
        raw_streams = api_get(
            f"/activities/{aid}/streams", token,
            params={"keys": STREAM_KEYS, "key_by_type": "false"},
        )
        if raw_streams:
            stream_rows = flatten_streams(raw_streams)
            write_stream_csv(STREAMS_DIR / f"{aid}.csv", stream_rows)
        else:
            # Write empty file so we don't re-attempt on next run
            (STREAMS_DIR / f"{aid}.csv").touch()

        # Laps
        laps = api_get(f"/activities/{aid}/laps", token)
        if laps:
            lap_rows = [flatten_lap(aid, lap) for lap in laps]
            write_lap_csv(LAPS_DIR / f"{aid}.csv", lap_rows)

    # --- Gear ---
    gear_path = DATA_DIR / "gear.json"
    existing_gear = {}
    if gear_path.exists():
        existing_gear = json.loads(gear_path.read_text())

    new_gear_ids = gear_ids - set(existing_gear.keys())
    if new_gear_ids:
        print(f"\nFetching {len(new_gear_ids)} gear items...")
        for gid in new_gear_ids:
            gear = api_get(f"/gear/{gid}", token)
            if gear:
                existing_gear[gid] = gear
        gear_path.write_text(json.dumps(existing_gear, indent=2))
        print(f"  Saved {gear_path}")

    # --- Summary ---
    acts_total = sum(1 for _ in open(activities_path)) - 1 if activities_path.exists() else 0
    segs_total = sum(1 for _ in open(segments_path)) - 1 if segments_path.exists() else 0
    streams_total = len(list(STREAMS_DIR.glob("*.csv")))
    print(f"\nDone.")
    print(f"  activities.csv       {acts_total} rows")
    print(f"  segment_efforts.csv  {segs_total} rows")
    print(f"  streams/             {streams_total} files")
    print(f"  gear.json            {len(existing_gear)} items")


if __name__ == "__main__":
    main()

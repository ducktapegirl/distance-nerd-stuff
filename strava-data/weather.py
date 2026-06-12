"""
Open-Meteo historical temperature lookup — free, no API key required.

Usage:
    from weather import fetch_weather_temp
    temp_c = fetch_weather_temp(lat, lon, datetime_local)   # float | None
"""
import time
from datetime import datetime

import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Minimum gap between calls — stay polite to the free API
_MIN_INTERVAL = 0.15   # seconds
_last_call_at: float = 0.0


def fetch_weather_temp(lat: float, lon: float, dt_local: datetime) -> "float | None":
    """
    Return temperature in °C at *lat/lon* at the hour matching *dt_local*,
    using Open-Meteo's historical archive.

    *dt_local* should be the local time at the activity location (i.e. the
    value from start_date_local in the CSV). Open-Meteo is asked for
    ``timezone=auto`` so its returned hourly times are also in local time —
    we just index by dt_local.hour.

    Returns None if the API call fails, data is unavailable (e.g. too recent),
    or coordinates are missing.
    """
    global _last_call_at

    if lat is None or lon is None:
        return None

    # Throttle
    elapsed = time.time() - _last_call_at
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    date_str = dt_local.strftime("%Y-%m-%d")

    try:
        resp = requests.get(
            ARCHIVE_URL,
            params={
                "latitude":   round(lat, 4),
                "longitude":  round(lon, 4),
                "start_date": date_str,
                "end_date":   date_str,
                "hourly":     "temperature_2m",
                "timezone":   "auto",
            },
            timeout=12,
        )
        _last_call_at = time.time()

        if resp.status_code != 200:
            return None

        data  = resp.json()
        temps = data.get("hourly", {}).get("temperature_2m") or []
        if not temps:
            return None

        # Index by hour — clamp in case of short arrays
        hour = min(dt_local.hour, len(temps) - 1)
        val  = temps[hour]
        return round(val, 1) if val is not None else None

    except Exception:
        _last_call_at = time.time()
        return None

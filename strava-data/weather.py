"""
Open-Meteo historical weather lookup — free, no API key required.

Uses the Historical Forecast API rather than the ERA5-based archive
endpoint: the archive endpoint's reanalysis dataset doesn't carry
uv_index at all (confirmed empirically — empty for every row even when
temperature/apparent_temperature succeeded), while the forecast-model
archive does. It covers 2021-present, which is plenty for our data.

Usage:
    from weather import fetch_weather
    weather = fetch_weather(lat, lon, datetime_local)
    # {"temp_c": float | None, "apparent_temp_c": float | None, "uv_index": float | None}
"""
import time
from datetime import datetime

import requests

ARCHIVE_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
HOURLY_VARS = "temperature_2m,apparent_temperature,uv_index"

# Minimum gap between calls — stay polite to the free API
_MIN_INTERVAL = 0.15   # seconds
_last_call_at: float = 0.0

_EMPTY = {"temp_c": None, "apparent_temp_c": None, "uv_index": None}


def fetch_weather(lat: float, lon: float, dt_local: datetime) -> dict:
    """
    Return temperature, apparent temperature (heat index equivalent), and UV
    index at *lat/lon* at the hour matching *dt_local*, using Open-Meteo's
    historical archive.

    *dt_local* should be the local time at the activity location (i.e. the
    value from start_date_local in the CSV). Open-Meteo is asked for
    ``timezone=auto`` so its returned hourly times are also in local time —
    we just index by dt_local.hour.

    Returns a dict with all values None if the API call fails, data is
    unavailable (e.g. too recent), or coordinates are missing.
    """
    global _last_call_at

    if lat is None or lon is None:
        return dict(_EMPTY)

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
                "hourly":     HOURLY_VARS,
                "timezone":   "auto",
            },
            timeout=12,
        )
        _last_call_at = time.time()

        if resp.status_code != 200:
            return dict(_EMPTY)

        hourly = resp.json().get("hourly", {})
        temps     = hourly.get("temperature_2m") or []
        app_temps = hourly.get("apparent_temperature") or []
        uvs       = hourly.get("uv_index") or []
        if not temps:
            return dict(_EMPTY)

        # Index by hour — clamp in case of short arrays
        hour = min(dt_local.hour, len(temps) - 1)

        def _round(series):
            if hour >= len(series):
                return None
            val = series[hour]
            return round(val, 1) if val is not None else None

        return {
            "temp_c":          _round(temps),
            "apparent_temp_c": _round(app_temps),
            "uv_index":        _round(uvs),
        }

    except Exception:
        _last_call_at = time.time()
        return dict(_EMPTY)

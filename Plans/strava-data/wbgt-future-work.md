# Future work: humidity + a proper WBGT heat-stress analysis

**Status:** proposal / not started · **Created:** 2026-07-11 · **Owner:** unassigned

## Why

The Exploratory tab's **Heat & Sun** charts (V9 `chart_x_heatsun`, V10
`chart_x_heatverdict`) currently answer "does temperature, UV, or a combined
temp+UV score best predict pace?" The combined predictor is labelled — honestly —
as **"WBGT-lite"**, because the sports-science gold standard for environmental
heat stress is **WBGT (Wet-Bulb Globe Temperature)**, which blends dry-bulb
temperature, a **humidity**-driven wet-bulb term, and a **solar/globe** radiant
term. Our dataset has temperature and UV but **no humidity, wind, or solar
irradiance**, so "Combined" is temperature + sun only and cannot be a real WBGT.

This note describes the work to close that gap: acquire the missing weather
inputs and compute an actual (estimated) WBGT, so the horse-race compares
temperature and UV against a legitimate heat-stress index instead of a proxy.

**Honest expectation to set up front:** given the current finding (once distance
and elevation are removed, weather explains only ~2–3% of running pace variance,
and temp∼UV are collinear at r≈0.47), a real WBGT will *probably* still explain
only a few percent. The value of this work is **methodological** — replacing a
proxy with the recognised metric and retiring the "WBGT-lite" caveat — not a
near-certain jump in explanatory power. Frame any resulting captions accordingly.

## Background: what WBGT actually requires

Outdoor WBGT is a weighted blend of three temperatures:

```
WBGT_outdoor = 0.7·Tnwb + 0.2·Tg + 0.1·Ta      (in sun)
WBGT_shade   = 0.7·Tw   + 0.3·Tg               (no direct sun)
```

- **Ta** — dry-bulb air temperature. *We already have this* (`average_temp_c`).
- **Tnwb / Tw** — natural / psychrometric **wet-bulb** temperature. Driven by air
  temperature **and relative humidity** (and, for the *natural* wet bulb, wind and
  radiation). **This is the missing humidity term** — the whole reason "Combined"
  is only "lite" today.
- **Tg** — **globe** temperature: what a black globe reaches under **solar
  radiation** and **wind**. Cannot be measured from our data; must be *estimated*
  from solar irradiance + wind + air temperature.

So a real WBGT needs three new inputs beyond what we store: **relative humidity**,
**wind speed**, and **solar radiation** (shortwave). All three are available from
the same Open-Meteo endpoint we already use.

## Data acquisition (Open-Meteo)

Weather is fetched by [`strava-data/weather.py`](weather.py) from the Open-Meteo
**Historical Forecast API** (chosen because the ERA5 archive endpoint returns no
`uv_index`; see the module docstring). The forecast archive **also carries
humidity, wind, and radiation**, so no new API or key is needed — only more
hourly variables.

### 1. `weather.py` — request and return the new variables

- Extend `HOURLY_VARS`:
  ```python
  HOURLY_VARS = (
      "temperature_2m,apparent_temperature,uv_index,"
      "relative_humidity_2m,wind_speed_10m,shortwave_radiation"
  )
  # Optional extras that improve globe-temp estimation:
  #   dew_point_2m, direct_radiation, diffuse_radiation, cloud_cover, is_day
  ```
- Parse each new series alongside `temps`/`app_temps`/`uvs` and add to the return
  dict (mirror the existing `_round` handling; keep `None` on failure):
  ```python
  return {
      "temp_c":            _round(temps),
      "apparent_temp_c":   _round(app_temps),
      "uv_index":          _round(uvs),
      "relative_humidity": _round(rh),           # %
      "wind_speed_ms":     _round(wind),         # NOTE units — see below
      "shortwave_wm2":     _round(swr),          # W/m²
  }
  ```
- **Units gotcha:** Open-Meteo defaults `wind_speed_10m` to **km/h** and
  `temperature_2m` to °C. Either pass explicit `wind_speed_unit=ms` in the request
  params or convert on read. WBGT formulas below expect **m/s** wind, **°C** temp,
  **%** RH, **W/m²** irradiance. Pin the units in the request to avoid silent drift.

### 2. `backfill_weather.py` — add columns and backfill existing rows

- Add the new fields to `WEATHER_FIELDS` and to the column-insertion loop (columns
  are inserted right after `average_temp_c`):
  ```python
  WEATHER_FIELDS = [
      "average_temp_c", "apparent_temp_c", "uv_index",
      "relative_humidity", "wind_speed_ms", "shortwave_wm2", "wbgt_c",
  ]
  ```
- Extend the per-row fill block to write each new value (same `if not r.get(...)`
  pattern), then **compute `wbgt_c` from the row's inputs** (see next section) and
  store it as a column too, so the dashboard never has to.
- Because these columns are currently **empty for all ~224 activities**, the first
  run re-fetches every geolocated row (throttled at `_MIN_INTERVAL = 0.15s`, so
  ~40–60s). Existing temp/UV values are preserved; only the blank columns fill.

### 3. `fetch.py` — new activities going forward

`fetch.py` calls `fetch_weather(...)` when ingesting new activities. Once
`weather.py` returns the extra fields, thread them into the row dict / CSV writer
there too, and compute `wbgt_c` at write time, so the nightly
`.github/workflows/strava-fetch.yml` run keeps WBGT populated without a manual
backfill.

### 4. CSV schema

`activities.csv` gains: `relative_humidity` (%), `wind_speed_ms` (m/s),
`shortwave_wm2` (W/m²), and the derived `wbgt_c` (°C). Data files **stay metric**
per the units policy — WBGT is displayed in °F at chart time.

## Computing WBGT (recommended: at ingestion, stored as a column)

**Architectural rule:** the dashboard build is restricted to
**stdlib + plotly + numpy** (see `CLAUDE.md`). WBGT estimation needs a few
transcendental formulas and, ideally, a solar-position calc — cleaner to do it
**once at fetch/backfill time** (where extra deps like `pvlib`/`astral`/`thermofeel`
are fine) and store `wbgt_c` in the CSV. The dashboard then just reads a number.

Two levels of fidelity — start with A, optionally graduate to B:

### Option A — shade/psychrometric WBGT (simple, no solar model)

Estimate the wet-bulb from temperature + humidity with **Stull (2011)** (valid for
RH 5–99%, T −20…50 °C), then approximate a shade WBGT. Pure formula, no
solar-geometry needed:

```python
import math
def wet_bulb_stull(T, RH):          # T °C, RH %  -> Tw °C
    return (T*math.atan(0.151977*(RH+8.313659)**0.5)
            + math.atan(T+RH) - math.atan(RH-1.676331)
            + 0.00391838*RH**1.5*math.atan(0.023101*RH) - 4.686035)

# Shade approximation (no globe term available): WBGT ≈ 0.7·Tw + 0.3·Ta
def wbgt_shade(T, RH):
    Tw = wet_bulb_stull(T, RH)
    return 0.7*Tw + 0.3*T
```

This already **incorporates humidity** — the missing ingredient — and is a
defensible "shade WBGT" proxy. Its weakness: it ignores direct sun (no globe
term), so it under-reads on clear, high-UV days.

### Option B — full outdoor WBGT with an estimated globe temperature

Use solar irradiance + wind to estimate globe temperature, then the full
`0.7·Tnwb + 0.2·Tg + 0.1·Ta`. The reference implementation is **Liljegren et al.
(2008)** (an energy-balance solve for Tnwb and Tg). Rather than re-derive it:

- Use a maintained library at ingestion time — e.g. **`thermofeel`** (ECMWF) or a
  `pywbgt`/Liljegren port — passing `temperature`, `relative_humidity`,
  `wind_speed`, `shortwave_radiation`, and a **solar zenith angle**.
- Solar zenith is a function of lat/lon/date/UTC-time — compute with **`pvlib`** or
  **`astral`** from the already-stored `start_latlng` + `start_date_local`. (We only
  need one value per activity, at its start hour.)

Option B is the honest "proper WBGT". Budget most of the effort here for the
globe-temp/solar-position plumbing and validating it against known values.

## Dashboard / analysis changes

Once `wbgt_c` is a column, the chart work is small and local to
[`strava-data/dashboard/charts_exploratory.py`](dashboard/charts_exploratory.py):

- **`_heatsun_prep`** — read `wbgt_c` (convert to °F for display: `wbgt_c*9/5+32`).
  Add a WBGT partial-R² alongside the existing temp/UV/combined ones:
  `R²(resid ~ wbgt)` on the distance+elevation residual, same pattern as the others.
- **V10 `chart_x_heatverdict`** — replace the proxy "Combined" bar with a real
  **WBGT** category (or keep Combined *and* add WBGT to show the proxy-vs-real
  gap). Update the caption: drop "WBGT-lite / no humidity available"; state WBGT is
  an **estimated shade/outdoor WBGT** and name the method (Stull / Liljegren).
- **V9 `chart_x_heatsun`** — optionally add a third toggle view (**Temp / UV /
  WBGT**). This means going from 2 views to 3: extend the trace-index layout, the
  `toggleHeatSun` JS in [`dashboard/template.py`](dashboard/template.py) (visibility
  arrays + x-axis title + annotation swap), and the seg-filter buttons in
  [`dashboard/page.py`](dashboard/page.py). Mirror the V1/V4 three-state patterns.
- **Captions / attribution** in `page.py` — retire the "WBGT-lite" language; note
  the WBGT is *estimated* (globe temp modelled, not measured) and observational.
- **Spec** — add a dated addendum to
  [`strava-data/dashboard-spec.md`](dashboard-spec.md) documenting the new column,
  the WBGT method + weighting used, and a `Verify vs recipe:` line pinning the new
  partial-R² values.

## Validation checklist

1. **Backfill sanity:** RH ∈ 0–100%, wind ≥ 0, shortwave ≥ 0 (0 at night),
   `wbgt_c` typically a few °C **below** air temp in dry/shade and near/above it in
   humid sun. Spot-check a hot humid day vs a hot dry day — WBGT should separate them
   where plain temperature doesn't (the whole point).
2. **Coverage:** report how many activities got all inputs; the historical-forecast
   archive is 2021-present, so pre-2021 rows (if any) stay blank — surface an
   auto-computed `~X% fewer` caveat like the apparent-temp views already do.
3. **Method check:** verify a handful of `wbgt_c` values against an independent
   WBGT calculator / library for the same T/RH/wind/solar inputs.
4. **Units policy:** WBGT displayed in **°F**; running pace min/mi `M:SS` reversed;
   MTB mph. Data stays metric. Grep the new code to confirm.
5. **Numbers:** independently recompute the WBGT partial R² (stdlib+numpy) and
   confirm it matches the spec's `Verify vs recipe:` values, as done for V9/V10.
6. **Visual QA:** render check + light/dark + mobile, same as the existing
   Heat & Sun charts. (Note: live Plotly rendering needs the CDN; if the
   environment blocks `cdn.plot.ly`, swap in the `plotly` package's bundled
   `plotly.min.js` to screenshot offline — see how V9/V10 were verified.)

## Effort estimate & sequencing

| Step | Work | Rough size |
|---|---|---|
| 1 | `weather.py` + `backfill_weather.py` + `fetch.py`: new vars, columns, units | S–M |
| 2 | WBGT compute — **Option A** (Stull shade) stored as `wbgt_c` | S |
| 3 | Re-run backfill; validate coverage + ranges | S |
| 4 | Wire WBGT into V9/V10 + captions + spec | M |
| 5 | (Optional) **Option B** full outdoor WBGT: solar zenith + globe temp | M–L |

Recommended path: ship **Option A end-to-end first** (it already introduces
humidity and retires the hard "no humidity" caveat), then decide whether the
solar/globe refinement of Option B is worth it based on whether WBGT's partial R²
meaningfully beats plain temperature.

## References

- Stull, R. (2011). *Wet-Bulb Temperature from Relative Humidity and Air
  Temperature.* J. Appl. Meteor. Climatol. 50(11). — the wet-bulb approximation.
- Liljegren, J. C., et al. (2008). *Modeling the Wet Bulb Globe Temperature Using
  Standard Meteorological Measurements.* J. Occ. Env. Hygiene 5(10). — outdoor WBGT
  from met data (globe/natural-wet-bulb energy balance).
- ACSM / OSHA WBGT activity-modification guidance — interpretation of WBGT bands.
- Open-Meteo Historical Forecast API — hourly variables
  (`relative_humidity_2m`, `wind_speed_10m`, `shortwave_radiation`, `dew_point_2m`,
  `direct_radiation`, `cloud_cover`, `is_day`).
- El Helou et al. (2012), *PLoS ONE* — air temperature as the primary predictor of
  marathon pace (the literature basis for the current Heat & Sun framing).

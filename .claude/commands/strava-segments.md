Read the file `strava-data/data/segments_summary.csv` and use it to answer questions about Strava segment performance.

The CSV has these columns:
- segment_id, segment_name, segment_city, segment_state
- segment_distance_m, segment_avg_grade
- start_lat, start_lng
- sport_types — comma-separated activity types for this segment (e.g. "Run", "MountainBikeRide")
- effort_count — total times this segment has been run
- first_effort, last_effort — date range of efforts
- best_time_s — PR elapsed time in seconds
- worst_time_s
- pr_date — date the PR was set
- recent_trend — slope of last-5 efforts in seconds/effort (negative = getting faster, positive = getting slower)
- avg_heartrate

If the user invoked this with arguments (e.g. `/strava-segments fastest` or `/strava-segments "Torrey Pines"` or `/strava-segments runs`), use those as the question. Otherwise, present a summary and ask what they'd like to know.

Default analysis to offer:
1. **Most-run segments** — top 10 by effort_count with best time and trend
2. **PR progression** — for a named segment, list all efforts chronologically and show improvement
3. **Trend report** — segments where recent_trend < -2 (getting faster) vs > 2 (getting slower)
4. **Untapped potential** — segments with high effort count but recent_trend showing no improvement
5. **By sport type** — filter any of the above by sport_types (e.g. only Run segments, only MountainBikeRide)

Format times as M:SS. Show trends with ↓ (faster) / ↑ (slower) / → (flat) arrows.
If the CSV doesn't exist, tell the user to run `python strava-data/fetch.py` then `python strava-data/analyze_segments.py` first.

$ARGUMENTS

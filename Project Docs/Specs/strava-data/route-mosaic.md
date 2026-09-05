I'm interested in making some printable wall art based on my Strava data. The inspiration for this project is the "route mosaic", item 32 in Project Docs/Plans/strava-data/epaper-feed-brainstorm.md.

I'm thinking of using "40 for 40" as the base idea: 40 routes in my 40th year of life (2025), also as something like a mosaic. This would be static, not rotating though.

For this work, assume that I can make full a color, 16" x 20" print.

I'd like to capture the variety of activity types that I did while maintaining an artistic/aesthetically pleasing look. 

Your task:
* Investigate all the GPS data I have for the year 2025 and understand what information is available
* Review the "route mosaic" idea, image, and related code:
	* **strava-data/feed/cards.py:866** — `c37_mosaic`, the card itself. Picks 32 tracks, lays out an 8×4 grid, scales each track to fit its cell preserving aspect, and emits one `polyline` per route.
	* **strava-data/feed/places.py** — `all_tracks()` supplies the data: reads up to 400 stream CSVs, downsamples each to 64 points, and normalises via `normalise()` so the dominant axis spans 0..1. It's `@lru_cache`'d because the full read is ~1.8s and several cards want it.
	* **strava-data/feed/svg.py** — `polyline()` does the actual drawing.
* Do a light amount of research into minimalist art or line art for inspiration
* Propose 3-4 designs as proofs for me to choose from. Then we can make an implementation plan.

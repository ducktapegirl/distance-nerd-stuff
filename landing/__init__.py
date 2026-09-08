"""The landing page — the site's front door at running-log/index.html.

Two glass tiles, one per dashboard, each fronted by an artistic SVG derived from
that dashboard's own data. Running log on the left, Strava on the right.

Dependency rule, deliberately tighter than either dashboard's: this package
imports **only the standard library and nerd_common**. It never imports
`running-log/dashboard/` or `strava-data/dashboard/` — those pull in Plotly and
a MapTiler key, and the landing page must stay the fastest page on the site
(no Plotly, no MapLibre, no CDN beyond the two webfonts). Data comes from the
CSVs directly, the same way strava-data/feed/ reads them.
"""

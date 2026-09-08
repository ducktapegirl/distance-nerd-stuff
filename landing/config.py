"""Paths and per-tile metadata for the landing page."""

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# running-log/ is the GitHub Pages publish root — that is the only reason the
# Strava artifacts live inside a directory named for the other dashboard.
PUBLISH_DIR = os.path.join(_ROOT, "running-log")
OUT_PATH    = os.path.join(PUBLISH_DIR, "index.html")

# Inputs. All read directly; neither dashboard's build package is imported.
RUNNING_LOG_CSV = os.path.join(PUBLISH_DIR, "running_log.csv")   # has a BOM
ACTIVITIES_CSV  = os.path.join(_ROOT, "strava-data", "data", "activities.csv")

# Per-activity GPS/elevation time-series, for the Strava tile's art. These are
# committed (379 tracked files, ~42 MB), so CI, fork PRs and fresh clones all
# have them and the art needs no precomputed asset — reading all 378 costs
# ~1.5 s, which is nothing beside the rest of a deploy. landing/geometry.py is
# the only thing that touches them.
STREAMS_DIR = os.path.join(_ROOT, "strava-data", "data", "streams")

SITE_TITLE = "distance nerd stuff"
SITE_BLURB = "A project to teach myself agentic coding tools."

# The one link that isn't a dashboard. Points at the repo, where the issue
# templates live under .github/ISSUE_TEMPLATE/.
REPO_URL = "https://github.com/ducktapegirl/distance-nerd-stuff"

# Tile identity. `accent` seeds the placeholder art and the tile's hover glow;
# the real art (see Project Docs/Plans/landing-art.md) may use more than this.
TILES = [
    {
        "key":    "college",
        "href":   "college.html",
        "title":  "College Running Log",
        "kicker": "2003 – 2007",
        "blurb":  "The life of a middle-of-the-road, D3 distance runner. Four years of paper training logs, transcribed and made interactive.",
        "accent": "#a78bfa",   # violet — the running log's --long
    },
    {
        "key":    "strava",
        "href":   "strava.html",
        "title":  "Strava Dashboard",
        "kicker": "2019 – present",
        "blurb":  "The life of a middle-aged, suburban mom. All the data, none of the training.",
        "accent": "#f59e0b",   # amber — the Strava dashboard's --mtb
    },
]

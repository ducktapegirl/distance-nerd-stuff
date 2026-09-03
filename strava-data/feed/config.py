"""Paths, panel constants, and the grayscale tone ramp for the e-paper feed."""

import os

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR    = os.path.join(_HERE, "data")
ACT_CSV     = os.path.join(DATA_DIR, "activities.csv")
SEG_CSV     = os.path.join(DATA_DIR, "segments_summary.csv")
GEAR_JSON   = os.path.join(DATA_DIR, "gear.json")
ATHLETE_JSON = os.path.join(DATA_DIR, "athlete.json")
STREAMS_DIR = os.path.join(DATA_DIR, "streams")

# running-log/ is the GitHub Pages publish root. These three files are
# gitignored exactly like index.html / strava.html.
_OUT_DIR  = os.path.normpath(os.path.join(_HERE, "..", "running-log"))
OUT_RSS   = os.path.join(_OUT_DIR, "feed.xml")
OUT_PAGE  = os.path.join(_OUT_DIR, "epaper.html")
OUT_SHEET = os.path.join(_OUT_DIR, "epaper-all.html")
OUT_JSON  = os.path.join(_OUT_DIR, "feed.json")

SITE = "https://ducktapegirl.github.io/distance-nerd-stuff"

# --- Panel ---------------------------------------------------------------
# reTerminal Sticky: 3.97", 800x480, 4-level grayscale, 235 PPI.
# The whole screen is ~3.4" x 2.0", so 1 mm is ~9.3 px. Nothing below MIN_TEXT
# is legible at arm's length; nothing below MIN_STROKE survives e-ink.
W, H       = 800, 480
MIN_TEXT   = 26
MIN_STROKE = 3
PAD        = 30

# The panel's four native tones. Every fill in the output snaps to one of
# these (or to a dither pattern built from two of them) so we never depend on
# the device's own dithering of an arbitrary colour.
BLACK = "#000000"
DARK  = "#555555"
LIGHT = "#AAAAAA"
WHITE = "#FFFFFF"
TONES = (BLACK, DARK, LIGHT, WHITE)

# Bundled-everywhere stacks only: the panel has no webfonts and no network.
FONT = "Helvetica, Arial, sans-serif"

KM_TO_MI = 0.621371
M_TO_FT  = 3.28084

RUN_TYPES  = ("Run", "TrailRun")
BIKE_TYPES = ("MountainBikeRide", "Ride", "EBikeRide")

"""Paths, panel constants, and the grayscale tone ramp for the e-paper feed."""

import os

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR    = os.path.join(_HERE, "data")
ACT_CSV     = os.path.join(DATA_DIR, "activities.csv")
SEG_CSV     = os.path.join(DATA_DIR, "segments_summary.csv")
SEG_EFF_CSV = os.path.join(DATA_DIR, "segment_efforts.csv")
GEAR_JSON   = os.path.join(DATA_DIR, "gear.json")
ATHLETE_JSON = os.path.join(DATA_DIR, "athlete.json")
STREAMS_DIR = os.path.join(DATA_DIR, "streams")

# The 2003-2007 paper-era log, parsed by running-log/parse_log.py. It is the
# other dashboard's *input*, not its output, so reading it here couples the
# feed to a checked-in CSV rather than to that build. It carries a BOM.
RUNLOG_CSV  = os.path.normpath(os.path.join(_HERE, "..", "running-log", "running_log.csv"))

# running-log/ is the GitHub Pages publish root. These three files are
# gitignored exactly like index.html / strava.html.
_OUT_DIR  = os.path.normpath(os.path.join(_HERE, "..", "running-log"))
OUT_RSS   = os.path.join(_OUT_DIR, "feed.xml")
OUT_PAGE  = os.path.join(_OUT_DIR, "epaper.html")
OUT_SHEET = os.path.join(_OUT_DIR, "epaper-all.html")
OUT_JSON  = os.path.join(_OUT_DIR, "feed.json")
# One static page per card, for pinning a single card by URL.
OUT_CARD_DIR = os.path.join(_OUT_DIR, "epaper")

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

# Strava's sport_type values are API enums - "MountainBikeRide",
# "WeightTraining" - and printing one on a card leaks a database value onto a
# fridge magnet. Two forms, because the cards use them in two grammars: a
# label standing on its own ("Mountain bike" in a row or a tag), and a gerund
# inside a sentence ("9.9 mi of mountain biking"). Only the entries that need
# special casing are listed - fmt.sport falls back to splitting the camel
# case, so a sport Strava adds later still reads sensibly with no edit here.
SPORT_LABELS = {
    "TrailRun": "Trail run",
    "MountainBikeRide": "Mountain bike",
    "EBikeRide": "E-bike",
    "StandUpPaddling": "Paddleboard",
}
SPORT_ACTIVITY = {
    "Run": "running",
    "TrailRun": "trail running",
    "Walk": "walking",
    "Hike": "hiking",
    "Ride": "riding",
    "MountainBikeRide": "mountain biking",
    "EBikeRide": "e-biking",
    "RockClimbing": "rock climbing",
    "WeightTraining": "weight training",
    "AlpineSki": "alpine skiing",
    "NordicSki": "nordic skiing",
    "Snowboard": "snowboarding",
    "IceSkate": "ice skating",
    "StandUpPaddling": "paddleboarding",
    "Pickleball": "pickleball",
    "Pilates": "pilates",
    "Workout": "a workout",
}

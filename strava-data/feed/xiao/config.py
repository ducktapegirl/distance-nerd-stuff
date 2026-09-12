"""Panel constants and the color roles for the 2.9" four-color XIAO panel.

A second, smaller e-paper target beside the reTerminal Sticky: Seeed's 2.9"
Quadruple Color ePaper (296x128, black / white / red / yellow) on the XIAO
ePaper Display Board, driven by SenseCraft HMI's Web function exactly like
the Sticky. Same data, same rotation, a different drawing surface.

The floors below are derived from the Sticky's, not guessed. That panel is
235 PPI and its 26 px text floor is 2.8 mm of em; this one is 112 PPI
(66.9 x 29.1 mm active area), so the same 2.8 mm is 12.4 px. It is rounded
*up* to 14 because there is no anti-aliasing here to soften a 12 px stem:
every pixel is one of four solid colors. Likewise the Sticky's 3 px stroke is
0.32 mm, which is 1.4 px here; 2 px, because a 1 px line on e-ink is a coin
toss.
"""

import os
from collections import namedtuple

from ..config import _OUT_DIR

# --- Panel ---------------------------------------------------------------
# Landscape. The product page says 128x296; SenseCraft lists it as 296x128
# and a desk or fridge strip is landscape.
W, H       = 296, 128
MIN_TEXT   = 14
MIN_STROKE = 2
PAD        = 6
PPI        = 112

# --- Outputs ---------------------------------------------------------------
# Mirrors the Sticky's trio and lives beside it in the Pages publish root;
# gitignored the same way.
OUT_PAGE     = os.path.join(_OUT_DIR, "epaper_xiao.html")
OUT_SHEET    = os.path.join(_OUT_DIR, "epaper_xiao-all.html")
OUT_CARD_DIR = os.path.join(_OUT_DIR, "epaper_xiao")

# --- The four colors ---------------------------------------------------------
# Pure primaries on purpose: whatever nearest-color quantizer SenseCraft runs
# maps these exactly, and anything in between would be a gamble. There is no
# gray on this panel and no dithering worth the pixels at 112 PPI, so there is
# no tone ramp either - svg.py raises on any other value.
BLACK  = "#000000"
WHITE  = "#FFFFFF"
RED    = "#FF0000"
YELLOW = "#FFFF00"
PALETTE = (BLACK, WHITE, RED, YELLOW)

# --- Color roles -------------------------------------------------------------
# Cards never name a hex; they ask for a role, and a model is a table. Two
# physical facts shape every model: yellow reads *light* on these panels
# (near white in luminance - an area wash, never text or a thin stroke) and
# red reads mid-dark (fine for shapes and large numerals, risky under ~20 px).
#
#   ink     text, rules, primary marks
#   accent  the one thing to look at: now, here, today, an alert
#   wash    an area fill for reference / past / rest - the light tone
#   run     sport-family color for a run-coded mark
#   bike    sport-family color for a bike-coded mark
#   ramp    four steps for quantity, light to dark, where a card needs one
Palette = namedtuple("Palette", "name ink accent wash run bike ramp")

# A: the Sticky's rule translated. Red is reserved for the single accent,
# yellow is the light tone, categories are still carried by shape.
SEMANTIC = Palette("semantic", BLACK, RED, YELLOW, BLACK, BLACK,
                   (WHITE, YELLOW, RED, BLACK))
# B: no reserved accent; color only ever means *more*.
HEAT = Palette("heat", BLACK, BLACK, YELLOW, BLACK, BLACK,
               (WHITE, YELLOW, RED, BLACK))
# C: the dashboard's teal / amber sport split, re-tabled as black / red.
SPORT = Palette("sport", BLACK, RED, YELLOW, BLACK, RED,
                (WHITE, YELLOW, RED, BLACK))

MODELS = {p.name: p for p in (SEMANTIC, HEAT, SPORT)}
DEFAULT = SEMANTIC

# Same font policy as the Sticky: bundled-everywhere stacks only.
FONT = "Helvetica, Arial, sans-serif"

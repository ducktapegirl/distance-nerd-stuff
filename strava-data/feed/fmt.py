"""Display formatting: dates that work on every platform, and sport names.

``strftime("%-d")`` and ``"%-H"`` — the no-leading-zero forms — are a glibc
extension. They raise ``ValueError`` on Windows, which meant the feed could be
built on the CI runner but not on the machine it is developed on. Nothing in
here is a preference: it is the portable spelling of "9 Aug 2026", not
"09 Aug 2026".

Use ``fmt.day`` / ``fmt.hm`` in this package. Never ``%-d`` or ``%-H``.

``sport`` / ``sport_activity`` are here for the same reason: a raw Strava
``sport_type`` is an API enum, and no card should ever print one.
"""

import re

from .config import SPORT_ACTIVITY, SPORT_LABELS

# A character no locale's month or weekday name can contain, so the
# substitution below cannot collide with the rest of the formatted string.
# Stripping a leading zero by text search would: "%Y-%m-%d" on 2005-01-05
# finds the "05" inside "2005" first.
_MARK = "\x1f"


def day(d, fmt="%d %b %Y"):
    """``strftime`` with the day-of-month unpadded, as ``%-d`` would give.

    ``fmt`` is written with the ordinary padded ``%d``; this swaps it for the
    bare number.
    """
    return d.strftime(fmt.replace("%d", _MARK)).replace(_MARK, str(d.day))


def hm(t):
    """``H:MM`` on a 24-hour clock, hour unpadded — what ``%-H:%M`` gave."""
    return f"{t.hour}:{t.minute:02d}"


# "MountainBikeRide" -> "Mountain", "Bike", "Ride". Also splits a run of
# capitals off cleanly, so "SUPRide" would give "SUP", "Ride".
_CAMEL = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[0-9]+")


def sport(sport_type):
    """A sport name that can stand on its own: "Mountain bike", "Hike".

    Anything not in ``SPORT_LABELS`` has its camel case split and is written
    as a sentence-case phrase, so an unmapped sport degrades to readable
    English instead of leaking the enum.
    """
    st = (sport_type or "").strip()
    if not st:
        return "Activity"
    if st in SPORT_LABELS:
        return SPORT_LABELS[st]
    words = _CAMEL.findall(st)
    if not words:
        return st
    return " ".join([words[0].capitalize()] + [w.lower() for w in words[1:]])


def sport_activity(sport_type):
    """The form that fits inside a sentence: "9.9 mi of mountain biking"."""
    st = (sport_type or "").strip()
    return SPORT_ACTIVITY.get(st) or sport(st).lower()

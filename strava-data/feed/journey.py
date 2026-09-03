"""Idea 19 - the Journey ladder: cumulative mileage as a road trip out of 92129.

An escalating ladder of real destinations at their approximate *driving*
distance from Rancho Penasquitos. The card auto-selects the leg you are on, so
early on it talks about Los Angeles and at 2,000 mi it talks about New York.

The distances are hand-curated approximations (the build makes no network
calls, a repo rule) and are good to roughly +/-5% - invisible in a "58% of the
way to Portland" framing. Edit them here; nothing else reads them.

Both ladders end at Boston on purpose: the dashboard's Places section already
tells a two-homes story (San Diego / Boston), so "running home" is the long arc
this card quietly builds toward.
"""

# (city label, approximate road miles from 92129). Must stay sorted by miles.
RUN_LADDER = [
    ("Los Angeles",              125),
    ("Las Vegas",                330),
    ("Grand Canyon, South Rim",  490),
    ("Salt Lake City",           750),
    ("Portland, Oregon",       1_100),
    ("Seattle",                1_255),
    ("Vancouver, BC",          1_400),
    ("Chicago",                2_080),
    ("New York City",          2_780),
    ("Boston",                 3_000),
]

BIKE_LADDER = [
    ("Palm Springs",             140),
    ("Phoenix",                  355),
    ("San Francisco",            500),
    ("Salt Lake City",           750),
    ("Denver",                 1_090),
    ("Austin",                 1_320),
    ("Chicago",                2_080),
    ("New York City",          2_780),
    ("Boston",                 3_000),
    ("Anchorage",              3_300),
]

ORIGIN = "92129"


def leg(total_mi, ladder):
    """Locate ``total_mi`` on ``ladder``.

    Returns a dict with the rung behind you, the rung ahead, how far is left,
    and the fraction of the current leg completed. Handles both ends:
    before the first rung there is nothing behind you (``behind`` is None, and
    the leg starts at 0 mi); past the last rung the journey laps, so the leg
    runs from the final city back to itself.
    """
    if not ladder:
        raise ValueError("ladder must not be empty")

    behind = None
    ahead = None
    for city, miles in ladder:
        if miles <= total_mi:
            behind = (city, miles)
        elif ahead is None:
            ahead = (city, miles)

    if ahead is not None:
        start_mi = behind[1] if behind else 0.0
        span = ahead[1] - start_mi
        frac = (total_mi - start_mi) / span if span > 0 else 1.0
        return {
            "behind": behind,
            "ahead": ahead,
            "remaining_mi": ahead[1] - total_mi,
            "frac": max(0.0, min(1.0, frac)),
            "lapped": False,
            "total_mi": total_mi,
            "ladder": ladder,
        }

    # Past the far end: report laps of the full route rather than breaking.
    final_city, final_mi = ladder[-1]
    laps = total_mi / final_mi
    return {
        "behind": (final_city, final_mi),
        "ahead": (final_city, final_mi),
        "remaining_mi": 0.0,
        "frac": laps - int(laps),
        "lapped": True,
        "laps": laps,
        "total_mi": total_mi,
        "ladder": ladder,
    }

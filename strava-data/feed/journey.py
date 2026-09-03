"""Idea 19 - the Journey: cumulative mileage as a road trip out of 92129.

Running heads east on I-8 → I-10 → I-40 to Boston; riding heads southeast on
I-8 → I-10 to Austin. Both follow **real interstate geometry**, shortest-pathed
across Natural Earth's US highway network by ``tools/gen_journey.py`` and cached
in ``assets/journey_routes.json``. Mileages are measured along that road, not
estimated: the build does no routing and no network I/O.

Mileposts are whatever cities the road actually passes, so nothing here is
hand-maintained. To change where a journey goes, edit ``CORRIDORS`` in
``tools/gen_journey.py`` and re-run it.

Ending the running corridor at Boston is deliberate: the dashboard's Places
section already tells a two-homes story (San Diego / Boston), so "running home"
is the long arc this card quietly builds toward.
"""

from . import geo

ORIGIN = "92129"


def corridor(group):
    """The cached corridor for 'run' or 'bike'."""
    return geo.load_routes()["corridors"][group]


def point_at(cor, miles):
    """Interpolate the (lat, lng) reached at a given road mileage."""
    path, cum = cor["path"], cor["cum_mi"]
    if miles <= 0:
        return tuple(path[0])
    if miles >= cum[-1]:
        return tuple(path[-1])
    for i in range(1, len(cum)):
        if cum[i] >= miles:
            span = cum[i] - cum[i - 1]
            f = (miles - cum[i - 1]) / span if span else 0.0
            (la1, lo1), (la2, lo2) = path[i - 1], path[i]
            return (la1 + (la2 - la1) * f, lo1 + (lo2 - lo1) * f)
    return tuple(path[-1])


def split_index(cor, miles):
    """Index in the path where the travelled portion ends."""
    cum = cor["cum_mi"]
    for i, v in enumerate(cum):
        if v >= miles:
            return i
    return len(cum) - 1


def position(total_mi, group):
    """Locate ``total_mi`` along a corridor.

    Returns the milepost behind, the one ahead, miles remaining to it, the
    fraction of the current leg completed, and the interpolated position. Two
    ends are handled explicitly: before the first milepost nothing is behind
    you and the leg starts at home; past the destination the journey laps.
    """
    cor = corridor(group)
    posts = cor["mileposts"]
    total_route = cor["total_mi"]

    behind = None
    ahead = None
    for p in posts:
        if p["mi"] <= total_mi:
            behind = p
        elif ahead is None:
            ahead = p

    lapped = total_mi >= total_route
    if ahead is None:
        ahead = {"mi": total_route, "name": cor["destination"]}

    start = behind["mi"] if behind else 0.0
    span = ahead["mi"] - start
    frac = (total_mi - start) / span if span > 0 else 1.0

    return {
        "corridor": cor,
        "behind": behind,
        "ahead": ahead,
        "remaining_mi": max(ahead["mi"] - total_mi, 0.0),
        "frac": max(0.0, min(1.0, frac)),
        "route_frac": max(0.0, min(1.0, total_mi / total_route)) if total_route else 0.0,
        "lapped": lapped,
        "laps": (total_mi / total_route) if total_route else 0.0,
        "total_mi": total_mi,
        "here": point_at(cor, total_mi),
        "split": split_index(cor, total_mi),
    }

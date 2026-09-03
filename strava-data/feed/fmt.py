"""Date and time formatting that works on every platform.

``strftime("%-d")`` and ``"%-H"`` — the no-leading-zero forms — are a glibc
extension. They raise ``ValueError`` on Windows, which meant the feed could be
built on the CI runner but not on the machine it is developed on. Nothing in
here is a preference: it is the portable spelling of "9 Aug 2026", not
"09 Aug 2026".

Use ``fmt.day`` / ``fmt.hm`` in this package. Never ``%-d`` or ``%-H``.
"""

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

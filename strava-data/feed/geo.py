"""Map projection and basemap drawing for the Journey cards.

Reads two checked-in *assets* - ``assets/basemap.json`` (Natural Earth coastline
and state lines, shared with the dashboard's Places hero) and
``assets/journey_routes.json`` (road corridors, written by
``tools/gen_journey.py``). Assets, not modules: ``feed/`` still imports nothing
from ``dashboard/``.

``basemap.json`` is shared, so never regenerate it from here.
"""

import json
import math
import os
from functools import lru_cache

from .config import DARK, LIGHT

_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets")
BASEMAP = os.path.join(_ASSETS, "basemap.json")
ROUTES = os.path.join(_ASSETS, "journey_routes.json")


@lru_cache(maxsize=1)
def load_basemap():
    """Layers of (lat, lng) polylines, keyed coast / admin / lakes."""
    with open(BASEMAP, encoding="utf-8") as f:
        d = json.load(f)
    return {layer: [[(p[i + 1], p[i]) for i in range(0, len(p) - 1, 2)] for p in polys]
            for layer, polys in d.items()}


@lru_cache(maxsize=1)
def load_routes():
    with open(ROUTES, encoding="utf-8") as f:
        return json.load(f)


# Both Journey cards frame on this fixed extent rather than on their own
# route's bounding box. The bike corridor is a thin east-west band, so a
# tight frame renders an unrecognisable sliver; the map here is for
# orientation only (the milepost strip carries the precision), so a
# consistent, recognisable continental silhouette is worth more than filling
# the box.
CONUS = (25.0, 49.5, -125.0, -67.0)


class Frame:
    """Equirectangular projection with a cos(lat) correction at mid-latitude.

    The same treatment ``places.normalise()`` gives GPS tracks. A conic would be
    prettier across the whole continent but buys nothing at 800x480.
    """

    def __init__(self, lat0, lat1, lng0, lng1, x, y, w, h, pad=0.06):
        dlat, dlng = lat1 - lat0, lng1 - lng0
        lat0 -= dlat * pad
        lat1 += dlat * pad
        lng0 -= dlng * pad
        lng1 += dlng * pad
        self.lat0, self.lat1, self.lng0, self.lng1 = lat0, lat1, lng0, lng1
        self.cos = math.cos(math.radians((lat0 + lat1) / 2)) or 1.0
        gw = max((lng1 - lng0) * self.cos, 1e-9)
        gh = max(lat1 - lat0, 1e-9)
        self.k = min(w / gw, h / gh)
        self.ox = x + (w - gw * self.k) / 2
        self.oy = y + (h - gh * self.k) / 2
        self.box = (x, y, w, h)

    @classmethod
    def around(cls, pts, x, y, w, h, pad=0.10):
        lats = [p[0] for p in pts]
        lngs = [p[1] for p in pts]
        return cls(min(lats), max(lats), min(lngs), max(lngs), x, y, w, h, pad)

    def xy(self, lat, lng):
        return (self.ox + (lng - self.lng0) * self.cos * self.k,
                self.oy + (self.lat1 - lat) * self.k)

    def inside(self, lat, lng, m=0.0):
        return (self.lat0 - m <= lat <= self.lat1 + m
                and self.lng0 - m <= lng <= self.lng1 + m)


def draw_basemap(card, frame, S, layers=("admin", "coast")):
    """Add basemap polylines, split wherever they leave the frame.

    Strokes are **solid greys, never svg.tone()**: a dither pattern used as a
    stroke renders as a dotted chain and turns a coastline into noise.
    """
    bm = load_basemap()
    tones = {"coast": (DARK, 4), "admin": (LIGHT, 3), "lakes": (LIGHT, 3)}
    x, y, w, h = frame.box
    for layer in layers:
        stroke, sw = tones[layer]
        for poly in bm.get(layer, []):
            run = []
            for lat, lng in poly:
                if frame.inside(lat, lng, m=2.0):
                    px, py = frame.xy(lat, lng)
                    if x - 40 <= px <= x + w + 40 and y - 40 <= py <= y + h + 40:
                        run.append((px, py))
                        continue
                if len(run) > 1:
                    card.add(S.polyline(run, stroke=stroke, sw=sw))
                run = []
            if len(run) > 1:
                card.add(S.polyline(run, stroke=stroke, sw=sw))
    return card


def project(frame, pts):
    """Project a lat/lng path, dropping points outside the frame."""
    return [frame.xy(la, lo) for la, lo in pts if frame.inside(la, lo, m=1.0)]

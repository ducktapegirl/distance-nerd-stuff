"""Regenerate the Places hero Terrain-mode shaded-relief asset
(strava-data/assets/hillshade.png).

Fetches Mapzen/AWS Terrarium PNG-encoded elevation tiles (Web Mercator),
resamples them onto the hero's EQUIRECTANGULAR frame (so the relief registers
with the routes/basemap with no reprojection at runtime), computes a hillshade,
and writes a compact RGBA PNG where alpha tracks slope -- so flats/ocean stay
transparent and only rugged terrain ("mountains show through", pre-spec 6.1)
paints. The build inlines this as a base64 data URI; the hero draws it faintly
under the vector basemap in Terrain mode only.

Run manually (needs network + Pillow; not a deploy dependency):

    uv run --with 'pillow,numpy' python strava-data/tools/gen_hillshade.py

Elevation source (public domain): AWS Terrain Tiles (terrarium encoding),
elevation_m = R*256 + G + B/256 - 32768.
"""
import io, math, os, urllib.request

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "assets", "hillshade.png"))
TILE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

# Same clip box as the vector basemap (gen_basemap.py) so the two layers align.
LAT0, LAT1 = 24.0, 55.0
LNG0, LNG1 = -135.0, -60.0
Z = 5                      # mercator source zoom (world = 2^Z * 256 px)
OW, OH = 768, 384          # output resolution (stretched to the frame box)

# Hillshade illumination (deg) + vertical exaggeration.
AZIMUTH, ALTITUDE, ZFACTOR = 315.0, 45.0, 1.6
MAX_ALPHA = 0.62           # peak per-pixel alpha in the PNG (drawn fainter still)


def _merc_y_to_lat(yn):
    """Normalized mercator y (0=top/north .. 1=bottom/south) -> latitude deg."""
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yn))))


def _lat_to_merc_y(lat):
    s = math.sin(math.radians(lat))
    return (1 - math.log((1 + s) / (1 - s)) / (2 * math.pi)) / 2


def _fetch_tile(z, x, y):
    url = TILE.format(z=z, x=x, y=y)
    with urllib.request.urlopen(url, timeout=60) as r:
        return np.asarray(Image.open(io.BytesIO(r.read())).convert("RGB"), dtype=np.float64)


def _mercator_elevation():
    n = 2 ** Z
    x0 = int((LNG0 + 180) / 360 * n)
    x1 = int((LNG1 + 180) / 360 * n)
    y0 = int(_lat_to_merc_y(LAT1) * n)     # north
    y1 = int(_lat_to_merc_y(LAT0) * n)     # south
    print("  z=%d tiles x[%d..%d] y[%d..%d] = %d tiles"
          % (Z, x0, x1, y0, y1, (x1 - x0 + 1) * (y1 - y0 + 1)))
    rows = []
    for ty in range(y0, y1 + 1):
        cols = []
        for tx in range(x0, x1 + 1):
            rgb = _fetch_tile(Z, tx, ty)
            cols.append(rgb[:, :, 0] * 256 + rgb[:, :, 1] + rgb[:, :, 2] / 256 - 32768)
        rows.append(np.hstack(cols))
    elev = np.vstack(rows)                  # [merc rows, merc cols]
    return elev, x0, y0, n


def _resample_to_equirect(elev, x0, y0, n):
    """Nearest-sample the mercator elevation mosaic onto a regular lat/lng grid
    over the clip box (top=LAT1). Registration is exact because the hero draws
    this in the same equirectangular frame."""
    mh, mw = elev.shape
    gx0 = x0 * 256                          # global mercator px origin of mosaic
    gy0 = y0 * 256
    world = n * 256

    lngs = np.linspace(LNG0, LNG1, OW)
    px = ((lngs + 180) / 360 * world - gx0).astype(np.int64)
    px = np.clip(px, 0, mw - 1)

    lats = np.linspace(LAT1, LAT0, OH)      # row 0 = north
    merc_y = np.array([_lat_to_merc_y(la) for la in lats])
    py = (merc_y * world - gy0).astype(np.int64)
    py = np.clip(py, 0, mh - 1)

    return elev[np.ix_(py, px)]             # [OH, OW]


def _hillshade(elev):
    # Cell size in meters (approx; lat-dependent x). Good enough for a faint relief.
    lat_mid = math.radians((LAT0 + LAT1) / 2)
    dx = (LNG1 - LNG0) / OW * 111320 * math.cos(lat_mid)
    dy = (LAT1 - LAT0) / OH * 111320
    gy, gx = np.gradient(elev, dy, dx)
    slope = np.arctan(ZFACTOR * np.hypot(gx, gy))
    aspect = np.arctan2(gy, -gx)
    zen = math.radians(90 - ALTITUDE)
    az = math.radians(AZIMUTH)
    hs = (math.cos(zen) * np.cos(slope)
          + math.sin(zen) * np.sin(slope) * np.cos(az - aspect))
    hs = np.clip(hs, 0, 1)
    # alpha tracks ruggedness: flats/ocean -> ~transparent, mountains -> visible.
    strength = np.clip(np.tanh(slope * 3.0), 0, 1)
    return hs, strength


def main():
    print("  fetching + decoding elevation tiles ...")
    elev, x0, y0, n = _mercator_elevation()
    grid = _resample_to_equirect(elev, x0, y0, n)
    hs, strength = _hillshade(grid)

    lum = (hs * 255).astype(np.uint8)                       # grayscale relief
    alpha = (strength * MAX_ALPHA * 255).astype(np.uint8)
    # Drop alpha over water (elevation <= 0) so oceans/lakes stay clean.
    alpha = np.where(grid <= 0, 0, alpha).astype(np.uint8)
    # Posterize (faint decorative relief) so PNG deflate compresses hard: lum to
    # 16 levels, alpha to 8. Cuts file size ~3x with no visible loss at low alpha.
    lum = (lum & 0xF0)
    alpha = (alpha & 0xE0).astype(np.uint8)

    la = np.dstack([lum, alpha])                            # LA (grayscale+alpha)
    img = Image.fromarray(la, mode="LA")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    print("wrote %s (%dx%d, %.1f KB)"
          % (OUT, OW, OH, os.path.getsize(OUT) / 1024.0))


if __name__ == "__main__":
    main()

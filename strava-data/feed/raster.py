"""Rasterize a card to pixels: the PNG codec both panels share, and the
Sticky's own 1-bit output for TRMNL.

resvg does the SVG rendering (a pure wheel, no browser). The PNG codec is
stdlib ``zlib`` + ``struct`` because there is no Pillow in this venv; numpy
does the pixel work. ``xiao/raster.py`` imports the codec from here and adds
the four-color snap; this module adds the Sticky's black-and-white reduction.

Why the Sticky needs pixels at all: reflashed to TRMNL firmware it never
fetches our pages - the device polls trmnl.com, whose server screenshots a
Liquid template and sends the panel a 1-bit image. So each card also ships as
``epaper/<id>.png``, and the template embeds the hour's card by URL. The
reduction happens *here* rather than in TRMNL's screenshot pipeline so the
file that leaves this build already is black and white: the two grays and the
dither patterns become an ordered Bayer 4x4 texture, deterministic, and
whatever TRMNL would dither afterwards has nothing left to do.
"""

import struct
import zlib

import numpy as np
import resvg_py

from .config import H, W, WHITE


def decode_png(d):
    """8-bit non-interlaced PNG bytes -> (h, w, channels) uint8."""
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("resvg did not return a PNG")
    idat, i = bytearray(), 8
    w = h = nch = 0
    while i < len(d):
        ln = struct.unpack(">I", d[i:i + 4])[0]
        typ, body = d[i + 4:i + 8], d[i + 8:i + 8 + ln]
        if typ == b"IHDR":
            w, h, bd, ct, _c, _f, inter = struct.unpack(">IIBBBBB", body)
            if bd != 8 or inter:
                raise ValueError("only 8-bit non-interlaced PNG is supported")
            nch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
        i += 12 + ln
    raw = zlib.decompress(bytes(idat))
    stride = w * nch
    out = np.zeros((h, stride), dtype=np.uint8)
    prev = np.zeros(stride, dtype=np.uint8)
    pos = 0
    # Sub and Up vectorize; Average and Paeth depend on the pixel to the
    # left, so they run as a Python loop - over a bytearray, which is an
    # order of magnitude faster than indexing numpy scalars one at a time
    # (resvg emits Paeth rows on the busier cards).
    for y in range(h):
        ft = raw[pos]
        pos += 1
        cur = np.frombuffer(raw[pos:pos + stride], dtype=np.uint8).copy()
        pos += stride
        if ft == 1:
            cur = (np.cumsum(cur.reshape(w, nch), axis=0, dtype=np.uint32) & 0xFF
                   ).astype(np.uint8).reshape(stride)
        elif ft == 2:
            cur = (cur.astype(np.int16) + prev.astype(np.int16)).astype(np.uint8)
        elif ft in (3, 4):
            c_ = bytearray(cur.tobytes())
            p_ = prev.tobytes()
            for x in range(stride):
                a = c_[x - nch] if x >= nch else 0
                b = p_[x]
                if ft == 3:
                    add = (a + b) >> 1
                else:
                    c = p_[x - nch] if x >= nch else 0
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    add = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                c_[x] = (c_[x] + add) & 0xFF
            cur = np.frombuffer(bytes(c_), dtype=np.uint8)
        out[y] = cur
        prev = cur
    return out.reshape(h, w, nch)


def chunk(typ, body):
    return (struct.pack(">I", len(body)) + typ + body
            + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF))


def encode_indexed(idx, palette_rgb, bit_depth):
    """(h, w) uint8 of palette indices -> indexed PNG bytes at ``bit_depth``
    bits per pixel (1, 2 or 4), MSB first, one filter byte per row.
    ``palette_rgb`` is a sequence of (r, g, b) in index order."""
    h, w = idx.shape
    rows = bytearray()
    for y in range(h):
        packed = np.packbits(np.unpackbits(idx[y].astype(np.uint8)[:, None], axis=1)
                             [:, 8 - bit_depth:].reshape(-1))
        rows += b"\x00" + packed.tobytes()
    plte = b"".join(bytes(c) for c in palette_rgb)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, bit_depth, 3, 0, 0, 0))
            + chunk(b"PLTE", plte)
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
            + chunk(b"IEND", b""))


def render_rgb(svg_string, w, h, background):
    """Render an SVG with resvg and return (h, w, 3) int32 RGB, alpha
    flattened onto white and single-channel gray expanded."""
    png = resvg_py.svg_to_bytes(svg_string=svg_string, width=w, height=h,
                                background=background)
    img = decode_png(png)
    rgb = img[:, :, :3].astype(np.int32)
    if img.shape[2] in (2, 4):
        a = img[:, :, -1].astype(np.int32)[:, :, None]
        rgb = (rgb * a + 255 * (255 - a)) // 255
    if img.shape[2] == 1:
        rgb = np.repeat(rgb, 3, axis=2)
    return rgb


# ── the Sticky's 1-bit output ───────────────────────────────────────────

# Bayer 4x4: the standard ordered-dither matrix. Tiled over the image, each
# cell's threshold is (M + 0.5) / 16 of full scale, so a flat #555 (33%)
# lights about a third of each 4x4 cell and #AAA (67%) about two thirds -
# a regular texture, not noise, which is what the cards' own dither
# patterns already look like at panel scale.
_BAYER4 = np.array([[0, 8, 2, 10],
                    [12, 4, 14, 6],
                    [3, 11, 1, 9],
                    [15, 7, 13, 5]], dtype=np.float64)
_PALETTE_1BIT = ((0, 0, 0), (255, 255, 255))   # index 0 black, 1 white


def bayer4(gray):
    """(h, w) luminance 0-255 -> (h, w) bool, True where the pixel is white."""
    h, w = gray.shape
    thr = (_BAYER4 + 0.5) / 16.0 * 255.0
    tiled = np.tile(thr, (h // 4 + 1, w // 4 + 1))[:h, :w]
    return gray > tiled


def png_1bit(card):
    """A Sticky card as an 800x480 1-bit indexed PNG for TRMNL."""
    rgb = render_rgb(card.svg(standalone=True), W, H, WHITE)
    # The card is achromatic by construction (four tones), so a plain mean
    # is the luminance; anti-aliased edges land between tones and dither.
    gray = rgb.mean(axis=2)
    return encode_indexed(bayer4(gray).astype(np.uint8), _PALETTE_1BIT, 1)

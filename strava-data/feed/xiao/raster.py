"""Rasterize a card to the panel's four colors: a PNG, a raw framebuffer, base64.

SenseCraft's Image widget takes an image URL or base64, so the card has to
exist as pixels, not markup. Rendering it here rather than leaving it to the
cloud also settles the one thing the docs never say - how a page gets
quantized to four colors - because the file that leaves this build already
*is* four colors: every pixel is snapped to the nearest of black, white, red
and yellow, and the PNG is written with a four-entry palette. Whatever
dithering the cloud would apply has nothing left to do.

resvg does the SVG rendering (a pure wheel, no browser); the PNG codec is
stdlib ``zlib`` + ``struct`` because there is no Pillow in this venv; numpy
does the nearest-color snap.

Three outputs from one card:

- ``png``    indexed 2-bit PNG, ~2 KB, for the Image widget URL / base64
- ``raw``    packed 2-bit framebuffer, 296 x 128 x 2 bits = 9,472 bytes, for
             a XIAO running its own firmware; index order black, white,
             yellow, red - the GDEY029F51 / JD79661 convention, worth
             verifying against the driver before trusting it on glass
- ``b64``    the PNG as base64, for the RSS item
"""

import base64
import struct
import zlib

import numpy as np
import resvg_py

from .config import BLACK, H, RED, W, WHITE, YELLOW

# Palette order is the framebuffer order. PNG index == raw 2-bit value.
PALETTE = (BLACK, WHITE, YELLOW, RED)
_RGB = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in PALETTE], dtype=np.int32)


def _decode_png(d):
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
    for y in range(h):
        ft = raw[pos]
        pos += 1
        cur = np.frombuffer(raw[pos:pos + stride], dtype=np.uint8).copy()
        pos += stride
        if ft == 2:
            cur = (cur.astype(np.int16) + prev.astype(np.int16)).astype(np.uint8)
        elif ft != 0:
            for x in range(stride):
                a = int(cur[x - nch]) if x >= nch else 0
                b = int(prev[x])
                c = int(prev[x - nch]) if x >= nch else 0
                if ft == 1:
                    add = a
                elif ft == 3:
                    add = (a + b) >> 1
                else:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    add = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[x] = (int(cur[x]) + add) & 0xFF
        out[y] = cur
        prev = cur
    return out.reshape(h, w, nch)


def _chunk(typ, body):
    return (struct.pack(">I", len(body)) + typ + body
            + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF))


def _encode_indexed(idx):
    """(h, w) uint8 of palette indices -> 2-bit indexed PNG bytes."""
    h, w = idx.shape
    rows = bytearray()
    for y in range(h):
        packed = np.packbits(np.unpackbits(idx[y].astype(np.uint8)[:, None], axis=1)[:, 6:]
                             .reshape(-1))
        rows += b"\x00" + packed.tobytes()
    plte = b"".join(bytes(c) for c in _RGB.astype(np.uint8))
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 2, 3, 0, 0, 0))
            + _chunk(b"PLTE", plte)
            + _chunk(b"IDAT", zlib.compress(bytes(rows), 9))
            + _chunk(b"IEND", b""))


def indices(card):
    """Render a card and snap every pixel to a palette index, (H, W) uint8."""
    png = resvg_py.svg_to_bytes(svg_string=card.svg(standalone=True), width=W, height=H,
                                background=WHITE)
    img = _decode_png(png)
    rgb = img[:, :, :3].astype(np.int32)
    if img.shape[2] in (2, 4):
        a = img[:, :, -1].astype(np.int32)[:, :, None]
        rgb = (rgb * a + 255 * (255 - a)) // 255
    if img.shape[2] == 1:
        rgb = np.repeat(rgb, 3, axis=2)
    # Nearest palette color by plain RGB distance. The four are cube corners,
    # so for the anti-aliased edge pixels this is a per-channel threshold.
    d = ((rgb[:, :, None, :] - _RGB[None, None, :, :]) ** 2).sum(axis=3)
    return d.argmin(axis=2).astype(np.uint8)


def png(card):
    return _encode_indexed(indices(card))


def raw(card):
    """Packed 2 bits per pixel, MSB first, row-major, no padding (W is a
    multiple of four)."""
    idx = indices(card)
    bits = np.unpackbits(idx[:, :, None], axis=2)[:, :, 6:].reshape(-1)
    return np.packbits(bits).tobytes()


def b64(png_bytes):
    return base64.b64encode(png_bytes).decode("ascii")

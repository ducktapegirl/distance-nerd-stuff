"""Rasterize a card to the panel's four colors: a PNG, a raw framebuffer, base64.

SenseCraft's Image widget takes an image URL or base64, so the card has to
exist as pixels, not markup. Rendering it here rather than leaving it to the
cloud also settles the one thing the docs never say - how a page gets
quantized to four colors - because the file that leaves this build already
*is* four colors: every pixel is snapped to the nearest of black, white, red
and yellow, and the PNG is written with a four-entry palette. Whatever
dithering the cloud would apply has nothing left to do.

The rendering (resvg) and the PNG codec (stdlib ``zlib`` + ``struct``, no
Pillow in this venv) live in ``feed/raster.py``, shared with the Sticky's own
1-bit output; this module is only the four-color snap and the framebuffer.

Three outputs from one card:

- ``png``    indexed 2-bit PNG, ~2 KB, for the Image widget URL / base64
- ``raw``    packed 2-bit framebuffer, 296 x 128 x 2 bits = 9,472 bytes, for
             a XIAO running its own firmware; index order black, white,
             yellow, red - the GDEY029F51 / JD79661 convention, worth
             verifying against the driver before trusting it on glass
- ``b64``    the PNG as base64, for the RSS item
"""

import base64

import numpy as np

from ..raster import encode_indexed, render_rgb
from .config import BLACK, H, RED, W, WHITE, YELLOW

# Palette order is the framebuffer order. PNG index == raw 2-bit value.
PALETTE = (BLACK, WHITE, YELLOW, RED)
_RGB = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in PALETTE], dtype=np.int32)


def indices(card):
    """Render a card and snap every pixel to a palette index, (H, W) uint8."""
    rgb = render_rgb(card.svg(standalone=True), W, H, WHITE)
    # Nearest palette color by plain RGB distance. The four are cube corners,
    # so for the anti-aliased edge pixels this is a per-channel threshold.
    d = ((rgb[:, :, None, :] - _RGB[None, None, :, :]) ** 2).sum(axis=3)
    return d.argmin(axis=2).astype(np.uint8)


def png(card):
    return encode_indexed(indices(card), _RGB.astype(np.uint8), 2)


def raw(card):
    """Packed 2 bits per pixel, MSB first, row-major, no padding (W is a
    multiple of four)."""
    idx = indices(card)
    bits = np.unpackbits(idx[:, :, None], axis=2)[:, :, 6:].reshape(-1)
    return np.packbits(bits).tobytes()


def b64(png_bytes):
    return base64.b64encode(png_bytes).decode("ascii")

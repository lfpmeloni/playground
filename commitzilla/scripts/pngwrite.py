"""Minimal dependency-free PNG encoder (8-bit truecolour RGB).

Pillow is not installed on this machine and we do not want the nightly job to
depend on a wheel being installable, so we emit the handful of chunks a valid
PNG needs ourselves: IHDR, IDAT, IEND.
"""

import struct
import zlib


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path, pixels, width, height):
    """pixels: flat list/bytearray of RGB triples, row-major, len == w*h*3."""
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter type 0 (None) for this scanline
        raw += pixels[y * stride:(y + 1) * stride]

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )
    with open(path, "wb") as fh:
        fh.write(png)
    return path


class Canvas:
    """Tiny RGB canvas with the couple of primitives the renderer needs."""

    def __init__(self, width, height, bg=(13, 17, 23)):
        self.w = width
        self.h = height
        self.px = bytearray(bytes(bg) * (width * height))

    def rect(self, x, y, w, h, color):
        c = bytes(color)
        for yy in range(max(0, y), min(self.h, y + h)):
            base = (yy * self.w + max(0, x)) * 3
            span = min(self.w, x + w) - max(0, x)
            if span > 0:
                self.px[base:base + span * 3] = c * span

    def rrect(self, x, y, w, h, color, r=2):
        """Rounded rectangle, GitHub-square style."""
        self.rect(x + r, y, w - 2 * r, h, color)
        self.rect(x, y + r, r, h - 2 * r, color)
        self.rect(x + w - r, y + r, r, h - 2 * r, color)
        for dy in range(r):
            for dx in range(r):
                if (dx - r + 0.5) ** 2 + (dy - r + 0.5) ** 2 <= r * r:
                    self.rect(x + dx, y + dy, 1, 1, color)
                    self.rect(x + w - 1 - dx, y + dy, 1, 1, color)
                    self.rect(x + dx, y + h - 1 - dy, 1, 1, color)
                    self.rect(x + w - 1 - dx, y + h - 1 - dy, 1, 1, color)

    def save(self, path):
        return write_png(path, self.px, self.w, self.h)

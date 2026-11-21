"""Decode the controller's display image (no Home Assistant dependency).

The terminal region of the controller exposes the 128x64 pixel LCD in registers
41000..41511 (512 registers). The screen is cut into 8 strips of 8 pixel rows;
inside a strip, each register holds two pixel columns: the low byte is the left
column, the high byte the right one, and bit 0 of a byte is the top pixel.
Reading register 41000 makes the controller take a fresh snapshot.
"""

from __future__ import annotations

import struct
import zlib

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAY_REGISTERS = 512

# LCD-like colours: dark pixels on a light green background.
COLOR_ON = (20, 30, 20)
COLOR_OFF = (190, 215, 185)


def decode_display(values: list[int]) -> list[list[int]]:
    """Turn 512 register values into a 64 x 128 matrix of 0/1 pixels."""
    if len(values) != DISPLAY_REGISTERS:
        raise ValueError(f"Expected {DISPLAY_REGISTERS} registers, got {len(values)}")
    pixels = [[0] * DISPLAY_WIDTH for _ in range(DISPLAY_HEIGHT)]
    for index, value in enumerate(values):
        strip, block = divmod(index, DISPLAY_WIDTH // 2)
        for half, byte in enumerate((value & 0xFF, (value >> 8) & 0xFF)):
            x = block * 2 + half
            for bit in range(8):
                if (byte >> bit) & 1:
                    pixels[strip * 8 + bit][x] = 1
    return pixels


def _chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def render_png(
    pixels: list[list[int]],
    scale: int = 4,
    on: tuple[int, int, int] = COLOR_ON,
    off: tuple[int, int, int] = COLOR_OFF,
) -> bytes:
    """Encode the pixel matrix as an RGB PNG, each pixel enlarged ``scale`` times."""
    height, width = len(pixels), len(pixels[0])
    on_px, off_px = bytes(on) * scale, bytes(off) * scale
    raw = bytearray()
    for row in pixels:
        line = b"\x00" + b"".join(on_px if p else off_px for p in row)
        raw += line * scale
    header = struct.pack(">IIBBBBB", width * scale, height * scale, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


# --- Text recognition (diagnostic use: reading the menus) -------------------------------
#
# The controller draws its menus with a small bitmap font (5 x 7 pixels, 6 pixel pitch).
# ``extract_text`` cuts the screen into text lines and glyphs and looks every glyph up in
# ``font`` (key: the glyph's columns written in hexadecimal, bit 0 = top row of the line).
# Glyphs that are not in the table are returned as ``{key}`` together with their ASCII art, so
# the table can be completed from the screens themselves.

# Glyphs learned from the real controller (key -> character); extended over time.
FONT: dict[str, str] = {}

MAX_LINE_HEIGHT = 10  # 7 pixel capitals + descenders (+ accents)


def _rows(pixels: list[list[int]], top: int, bottom: int) -> list[list[int]]:
    return [pixels[y] for y in range(top, bottom + 1)]


def _glyph_key(columns: list[int]) -> str:
    return ".".join(f"{c:x}" for c in columns)


def glyph_art(key: str) -> list[str]:
    """Draw a glyph key as rows of '#' and '.' (for display in a diagnostic answer)."""
    columns = [int(c, 16) for c in key.split(".")]
    height = max(max(c.bit_length() for c in columns), 7)
    return ["".join("#" if (c >> y) & 1 else "." for c in columns) for y in range(height)]


def _split_tall_run(pixels: list[list[int]], top: int, bottom: int) -> list[tuple[int, int]]:
    """Two text lines without a blank row between them: cut at the sparsest row."""
    best, best_ink = None, None
    for y in range(top + 6, bottom - 5):
        ink = sum(pixels[y])
        if best_ink is None or ink < best_ink:
            best, best_ink = y, ink
    if best is None:
        return []
    parts = [(top, best - 1), (best + 1, bottom)]
    return [p for p in parts if 0 < p[1] - p[0] + 1 <= MAX_LINE_HEIGHT]


def _remove_thin_lines(pixels: list[list[int]]) -> list[list[int]]:
    """Erase frames and rules (1-2 pixel lines, 10+ pixels long) so only text is left.

    Filled areas (highlighted menu lines) are thicker and are kept.
    """
    height, width = len(pixels), len(pixels[0])
    hrun = [[0] * width for _ in range(height)]
    vrun = [[0] * width for _ in range(height)]
    for y in range(height):
        x = 0
        while x < width:
            if pixels[y][x]:
                e = x
                while e < width and pixels[y][e]:
                    e += 1
                for i in range(x, e):
                    hrun[y][i] = e - x
                x = e
            else:
                x += 1
    for x in range(width):
        y = 0
        while y < height:
            if pixels[y][x]:
                e = y
                while e < height and pixels[e][x]:
                    e += 1
                for i in range(y, e):
                    vrun[i][x] = e - y
                y = e
            else:
                y += 1
    out = [row[:] for row in pixels]
    for y in range(height):
        for x in range(width):
            if pixels[y][x] and (
                (hrun[y][x] >= 10 and vrun[y][x] <= 2) or (vrun[y][x] >= 10 and hrun[y][x] <= 2)
            ):
                out[y][x] = 0
    # leftovers of corners / junctions: isolated pixels touching a removed line
    for y in range(height):
        for x in range(width):
            if not out[y][x]:
                continue
            near = [
                (yy, xx)
                for yy in range(max(0, y - 1), min(height, y + 2))
                for xx in range(max(0, x - 1), min(width, x + 2))
                if (yy, xx) != (y, x)
            ]
            if any(pixels[yy][xx] and not out[yy][xx] for yy, xx in near) and not any(
                out[yy][xx] for yy, xx in near
            ):
                out[y][x] = 0
    return out


def extract_text(
    pixels: list[list[int]], font: dict[str, str]
) -> tuple[list[dict], dict[str, list[str]]]:
    """Return (lines, unknown glyphs). Each line: {"y", "x", "inverted", "text"}."""
    pixels = _remove_thin_lines(pixels)
    height, width = len(pixels), len(pixels[0])
    lines: list[dict] = []
    unknown: dict[str, list[str]] = {}
    runs: list[tuple[int, int]] = []
    y = 0
    while y < height:
        if not any(pixels[y]):
            y += 1
            continue
        top = y
        while y < height and any(pixels[y]):
            y += 1
        bottom = y - 1
        size = bottom - top + 1
        if size <= MAX_LINE_HEIGHT:
            runs.append((top, bottom))
        elif size <= 2 * MAX_LINE_HEIGHT:
            runs.extend(_split_tall_run(pixels, top, bottom))
    for top, bottom in runs:
        band = _rows(pixels, top, bottom)
        used = [x for x in range(width) if any(row[x] for row in band)]
        left, right = used[0], used[-1]
        cells = (bottom - top + 1) * (right - left + 1)
        ink = sum(row[x] for row in band for x in range(left, right + 1))
        inverted = ink > 0.55 * cells
        if inverted:
            band = [[1 - row[x] for x in range(left, right + 1)] for row in band]
        else:
            band = [row[left : right + 1] for row in band]
        rows_with_ink = [i for i, row in enumerate(band) if any(row)]
        if not rows_with_ink:
            continue
        band = band[rows_with_ink[0] : rows_with_ink[-1] + 1]
        w = len(band[0])
        col_ints = [sum(band[r][x] << r for r in range(len(band))) for x in range(w)]
        text, x, previous_end, wide = "", 0, None, False
        while x < w:
            if col_ints[x] == 0:
                x += 1
                continue
            start = x
            while x < w and col_ints[x]:
                x += 1
            if previous_end is not None:
                gap = start - previous_end
                text += " " * max(0, round((gap - 1) / 6))
            key = _glyph_key(col_ints[start:x])
            char = font.get(key)
            if char is None and x - start > 7:
                text += "[img]"  # a picture, not a character
                previous_end = x
                continue
            if char is None:
                text += "{" + key + "}"
                if len(unknown) < 40:
                    unknown.setdefault(key, glyph_art(key))
            else:
                text += char
            previous_end = x
        lines.append({"y": top, "x": left, "inverted": inverted, "text": text})
    return lines, unknown

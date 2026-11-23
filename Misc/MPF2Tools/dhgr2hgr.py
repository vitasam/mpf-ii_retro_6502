#!/usr/bin/env python3
#
# Copyright (c) 2026 The Random DIY
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# SPDX-License-Identifier: MIT

"""Convert an Apple IIe double hi-res (DHGR) image to a standard hi-res image.

The MPF-II has standard hi-res (280x192, 6 colors) but no double hi-res, so a
16 KB DHGR picture must be converted on the PC before loading.

Input
-----
  16384 bytes: two 8 KB halves in hi-res screen layout. By default the
  auxiliary-memory half comes first (A2FC / Dazzledraw "BIN" order); use
  --main-first if the main-memory half comes first.

  Each screen row is 80 bytes in display order aux0, main0, aux1, main1, ...
  Bits 0-6 of each byte are shown left to right (bit 7 is ignored), giving
  560 dots. Every 4 dots form one of 140 pixels with one of 16 colors.

Output
------
  8192 bytes of standard hi-res, to be loaded at $2000 ($2000-$3FFF).
  Each byte holds 7 pixels (bit 0 leftmost) and a palette bit (bit 7):
  palette 0 = violet/green, palette 1 = blue/orange. A lone lit pixel shows
  violet or blue in even columns and green or orange in odd columns; two lit
  pixels side by side show white.

  The 140x192 DHGR image maps 1:1 onto hi-res pixel pairs. For each byte the
  palette with the smaller error is chosen, then each pair is quantized with
  Floyd-Steinberg error diffusion. --mono dithers to black and white at the
  full 280x192 instead.

Usage
-----
  python3 dhgr2hgr.py monarch_appleii.bin -o monarch.hgr --preview monarch.png
  python3 mpf2wav.py monarch.hgr -s 2000 -n MONARC
  then on the MPF-II, in the Monitor:  2000.3FFFR  and start playback.
"""

import argparse
import struct
import zlib
from pathlib import Path

SCREEN_SIZE = 8192
WIDTH_DHGR = 140  # color pixels per row
WIDTH_HGR = 280
HEIGHT = 192

# Apple II lo-res / double hi-res palette (index = lo-res color number).
PALETTE = [
    (0, 0, 0),  # 0  black
    (227, 30, 96),  # 1  magenta
    (96, 78, 189),  # 2  dark blue
    (255, 68, 253),  # 3  purple (= hi-res violet)
    (0, 163, 96),  # 4  dark green
    (156, 156, 156),  # 5  grey 1
    (20, 207, 253),  # 6  medium blue (= hi-res blue)
    (208, 195, 255),  # 7  light blue
    (96, 114, 3),  # 8  brown
    (255, 106, 60),  # 9  orange (= hi-res orange)
    (156, 156, 156),  # 10 grey 2
    (255, 160, 208),  # 11 pink
    (20, 245, 60),  # 12 green (= hi-res green)
    (208, 221, 141),  # 13 yellow
    (114, 255, 208),  # 14 aqua
    (255, 255, 255),  # 15 white
]

BLACK, WHITE = PALETTE[0], PALETTE[15]
# Color of a lone lit pixel: [palette bit][column parity].
LONE_PIXEL = [[PALETTE[3], PALETTE[12]], [PALETTE[6], PALETTE[9]]]

Rgb = tuple[float, float, float]


def _row_offset(y: int) -> int:
    """Offset of screen row y within an 8 KB hi-res page."""
    return (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28


def _distance(a: Rgb, b: Rgb) -> float:
    """Weighted squared RGB distance (approximates perceived difference)."""
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return 2 * dr * dr + 4 * dg * dg + 3 * db * db


def decode_dhgr(data: bytes, main_first: bool = False) -> list[list[Rgb]]:
    """Decodes a 16 KB DHGR image into 192 rows of 140 RGB pixels."""
    if len(data) != 2 * SCREEN_SIZE:
        raise ValueError(f"Expected {2 * SCREEN_SIZE} bytes, got {len(data)}.")
    if main_first:
        main, aux = data[:SCREEN_SIZE], data[SCREEN_SIZE:]
    else:
        aux, main = data[:SCREEN_SIZE], data[SCREEN_SIZE:]

    image = []
    for y in range(HEIGHT):
        offset = _row_offset(y)
        dots = []
        for x in range(40):
            for byte in (aux[offset + x], main[offset + x]):
                dots.extend((byte >> bit) & 1 for bit in range(7))
        row = []
        for p in range(WIDTH_DHGR):
            # DHGR dot d has NTSC color phase (d + 1) mod 4; the lo-res color number
            # has one bit per phase.
            color = 0
            for k in range(4):
                color |= dots[4 * p + k] << ((k + 1) & 3)
            row.append(PALETTE[color])
        image.append(row)
    return image


def _choose_palettes(row: list[Rgb]) -> list[int]:
    """Picks the palette bit for each of the 40 bytes of one row."""
    palettes = []
    for byte_index in range(40):
        errors = []
        for palette in (0, 1):
            error = 0.0
            for px in range(7 * byte_index, 7 * byte_index + 7):
                target = row[px // 2]
                candidates = (BLACK, WHITE, LONE_PIXEL[palette][px & 1])
                error += min(_distance(target, c) for c in candidates)
            errors.append(error)
        palettes.append(0 if errors[0] <= errors[1] else 1)
    return palettes


def _diffuse(
    err_rows: list[list[list[float]]], y: int, x: int, width: int, error: Rgb
) -> None:
    """Spreads quantization error to unvisited neighbors (Floyd-Steinberg)."""
    for dy, dx, weight in ((0, 1, 7), (1, -1, 3), (1, 0, 5), (1, 1, 1)):
        ny, nx = y + dy, x + dx
        if ny < HEIGHT and 0 <= nx < width:
            cell = err_rows[ny][nx]
            for c in range(3):
                cell[c] += error[c] * weight / 16


def encode_hgr_color(image: list[list[Rgb]]) -> bytes:
    """Quantizes a 140x192 image to hi-res colors with error diffusion."""
    screen = bytearray(SCREEN_SIZE)
    errors = [[[0.0, 0.0, 0.0] for _ in range(WIDTH_DHGR)] for _ in range(HEIGHT)]

    for y in range(HEIGHT):
        row = image[y]
        palettes = _choose_palettes(row)
        offset = _row_offset(y)
        pixels = [0] * WIDTH_HGR
        for q in range(WIDTH_DHGR):
            want = tuple(row[q][c] + errors[y][q][c] for c in range(3))
            even_pal = palettes[(2 * q) // 7]
            odd_pal = palettes[(2 * q + 1) // 7]
            options = (
                ((0, 0), BLACK),
                ((1, 1), WHITE),
                ((1, 0), LONE_PIXEL[even_pal][0]),
                ((0, 1), LONE_PIXEL[odd_pal][1]),
            )
            bits, shown = min(options, key=lambda o: _distance(want, o[1]))
            pixels[2 * q], pixels[2 * q + 1] = bits
            _diffuse(
                errors, y, q, WIDTH_DHGR, tuple(want[c] - shown[c] for c in range(3))
            )
        for byte_index in range(40):
            value = palettes[byte_index] << 7
            for bit in range(7):
                value |= pixels[7 * byte_index + bit] << bit
            screen[offset + byte_index] = value
    return bytes(screen)


def encode_hgr_mono(image: list[list[Rgb]], full_width: bool = False) -> bytes:
    """Dithers an image to black and white at 280x192.

    The image is 140 pixels wide (each pixel becomes two dots), or 280 pixels
    wide with full_width=True.
    """
    screen = bytearray(SCREEN_SIZE)
    repeat = 1 if full_width else 2
    luma = [
        [0.299 * r + 0.587 * g + 0.114 * b for (r, g, b) in row for _ in range(repeat)]
        for row in image
    ]

    for y in range(HEIGHT):
        offset = _row_offset(y)
        pixels = [0] * WIDTH_HGR
        for x in range(WIDTH_HGR):
            value = luma[y][x]
            pixels[x] = 1 if value >= 128 else 0
            error = value - (255 if pixels[x] else 0)
            for dy, dx, weight in ((0, 1, 7), (1, -1, 3), (1, 0, 5), (1, 1, 1)):
                ny, nx = y + dy, x + dx
                if ny < HEIGHT and 0 <= nx < WIDTH_HGR:
                    luma[ny][nx] += error * weight / 16
        for byte_index in range(40):
            value = 0
            for bit in range(7):
                value |= pixels[7 * byte_index + bit] << bit
            screen[offset + byte_index] = value
    return bytes(screen)


def render_hgr(screen: bytes, mono: bool = False) -> list[list[Rgb]]:
    """Approximates how a hi-res screen looks on a color or mono display."""
    image = []
    for y in range(HEIGHT):
        offset = _row_offset(y)
        bits, palettes = [], []
        for byte_index in range(40):
            byte = screen[offset + byte_index]
            for bit in range(7):
                bits.append((byte >> bit) & 1)
                palettes.append(byte >> 7)
        row = []
        for x in range(WIDTH_HGR):
            if not bits[x]:
                row.append(BLACK)
            elif mono:
                row.append(WHITE)
            elif (x > 0 and bits[x - 1]) or (x < WIDTH_HGR - 1 and bits[x + 1]):
                row.append(WHITE)
            else:
                row.append(LONE_PIXEL[palettes[x]][x & 1])
        image.append(row)
    return image


def write_png(path: Path, image: list[list[Rgb]], x_scale: int, y_scale: int) -> None:
    """Writes an RGB image as PNG, scaled up by whole numbers."""
    raw = bytearray()
    for row in image:
        line = bytearray(b"\x00")  # filter type: none
        for r, g, b in row:
            pixel = bytes((max(0, min(255, int(v))) for v in (r, g, b)))
            line += pixel * x_scale
        raw += line * y_scale
    width, height = len(image[0]) * x_scale, len(image) * y_scale

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return (
            struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an Apple IIe double hi-res image to standard hi-res."
    )
    parser.add_argument("input", type=Path, help="16 KB DHGR image")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output 8 KB hi-res file (default: input name with .hgr)",
    )
    parser.add_argument(
        "--main-first",
        action="store_true",
        help="input has the main-memory half first (default: aux first)",
    )
    parser.add_argument(
        "--mono", action="store_true", help="dither to black and white instead of color"
    )
    parser.add_argument(
        "--preview", type=Path, help="also write a PNG of the converted hi-res image"
    )
    parser.add_argument(
        "--source-preview", type=Path, help="also write a PNG of the decoded DHGR image"
    )
    args = parser.parse_args()

    try:
        image = decode_dhgr(args.input.read_bytes(), main_first=args.main_first)
    except ValueError as err:
        parser.error(str(err))

    screen = encode_hgr_mono(image) if args.mono else encode_hgr_color(image)
    out_path = args.output or args.input.with_suffix(".hgr")
    out_path.write_bytes(screen)
    print(
        f"Saved: {out_path} ({len(screen)} bytes, "
        f"{'mono' if args.mono else 'color'} hi-res)"
    )

    if args.source_preview:
        write_png(args.source_preview, image, x_scale=4, y_scale=2)
        print(f"Saved: {args.source_preview} (decoded DHGR, 560x384)")
    if args.preview:
        write_png(
            args.preview, render_hgr(screen, mono=args.mono), x_scale=2, y_scale=2
        )
        print(f"Saved: {args.preview} (converted hi-res, 560x384)")
    print("MPF-II Monitor load command: 2000.3FFFR (load at $2000)")


if __name__ == "__main__":
    main()

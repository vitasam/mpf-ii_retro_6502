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

"""Convert a picture into an MPF-II hi-res screen (8 KB, load at $2000).

Input
-----
  A 280x192 picture, already cropped, in any format Pillow reads (PNG, JPEG,
  GIF, BMP, ...). Pictures of another size are stretched to 280x192.
  Transparent areas become black. Requires Pillow (see requirements.txt).

  Preparing a picture: the MPF-II shows 280x192 dots on a roughly 4:3 screen,
  so each dot is slightly taller than wide. To keep circles round, crop the
  original to 4:3 and then scale it to 280x192 without keeping proportions.

Output
------
  8192 bytes of MPF-II hi-res (same encoders as dhgr2hgr.py):
    color   pairs of dots become one of black, white, purple, green, blue or
            orange (140x192 color resolution), Floyd-Steinberg dithered
    --mono  black and white at the full 280x192, Floyd-Steinberg dithered

  This script imports dhgr2hgr.py, so keep both files in the same folder.

Usage
-----
  python3 img2hgr.py photo.png -o photo.hgr --preview photo_preview.png
  python3 hgrdemo.py photo.hgr -o photo_demo.bin
  python3 mpf2wav.py photo_demo.bin -s 9FF0 -n PHOTO
  then on the MPF-II, in the Monitor:  9FF0.BFFFR  then  9FF0G
"""

import argparse
from pathlib import Path

from PIL import Image

from dhgr2hgr import (
    HEIGHT,
    WIDTH_HGR,
    Rgb,
    encode_hgr_color,
    encode_hgr_mono,
    render_hgr,
    write_png,
)


def read_image(path: Path) -> list[list[Rgb]]:
    """Reads a picture as 192 rows of 280 RGB tuples."""
    with Image.open(path) as picture:
        picture = picture.convert("RGBA")
        if picture.size != (WIDTH_HGR, HEIGHT):
            print(
                f"Note: stretching {picture.size[0]}x{picture.size[1]} "
                f"to {WIDTH_HGR}x{HEIGHT}."
            )
            picture = picture.resize((WIDTH_HGR, HEIGHT), Image.Resampling.LANCZOS)
        raw = picture.tobytes()
    rows = []
    for y in range(HEIGHT):
        line = raw[y * WIDTH_HGR * 4 : (y + 1) * WIDTH_HGR * 4]
        rows.append(
            [
                tuple(v * line[i + 3] / 255 for v in line[i : i + 3])
                for i in range(0, len(line), 4)
            ]
        )  # transparent -> black
    return rows


def to_color_pairs(rows: list[list[Rgb]]) -> list[list[Rgb]]:
    """Averages each pair of dots into one of 140 color pixels per row."""
    return [
        [
            tuple((row[2 * q][c] + row[2 * q + 1][c]) / 2 for c in range(3))
            for q in range(WIDTH_HGR // 2)
        ]
        for row in rows
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a 280x192 picture into an MPF-II hi-res screen."
    )
    parser.add_argument("input", type=Path, help="280x192 picture (PNG, JPEG, ...)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output 8 KB hi-res file (default: input name with .hgr)",
    )
    parser.add_argument(
        "--mono", action="store_true", help="dither to black and white instead of color"
    )
    parser.add_argument(
        "--preview", type=Path, help="also write a PNG of the converted hi-res image"
    )
    args = parser.parse_args()

    try:
        rows = read_image(args.input)
    except (OSError, ValueError) as err:
        parser.error(str(err))

    if args.mono:
        screen = encode_hgr_mono(rows, full_width=True)
    else:
        screen = encode_hgr_color(to_color_pairs(rows))

    out_path = args.output or args.input.with_suffix(".hgr")
    out_path.write_bytes(screen)
    print(
        f"Saved: {out_path} ({len(screen)} bytes, "
        f"{'mono' if args.mono else 'color'} hi-res)"
    )
    if args.preview:
        write_png(
            args.preview, render_hgr(screen, mono=args.mono), x_scale=2, y_scale=2
        )
        print(f"Saved: {args.preview} (converted hi-res, 560x384)")
    print(
        "MPF-II Monitor load command: 2000.3FFFR (load at $2000), "
        "or bundle it with hgrdemo.py"
    )


if __name__ == "__main__":
    main()

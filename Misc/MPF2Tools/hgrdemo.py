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

"""Bundle an 8 KB MPF-II hi-res picture with a tiny viewer into one binary.

The result loads with a single Monitor `R` command and runs with `G`.

Memory layout (default, page 2)
-------------------------------
  $9FF0-$9FFF  viewer (16 bytes, padded with $00)
  $A000-$BFFF  picture (hi-res page 2)

  The Monitor draws its text on page 1 ($2000-$3FFF), so a picture on page 2
  is never overwritten. With --page 1 the layout is $1FF0-$1FFF viewer and
  $2000-$3FFF picture instead.

Viewer (6502)
-------------
  LDA $C050   ; display graphics mode (turns color on)
  LDA $C055   ; display page 2 ($C054 for page 1)
  JMP *       ; stay on the picture; press RESET to return

  Soft switches are from the MPF-II manual, Table 2-4. The viewer does not
  read the keyboard, because the MPF-II keyboard is not at the Apple II
  address ($C000).

Usage
-----
  python3 dhgr2hgr.py monarch_appleii.bin -o monarch.hgr
  python3 hgrdemo.py monarch.hgr -o monarch_demo.bin
  python3 mpf2wav.py monarch_demo.bin -s 9FF0 -n MONARC
  then on the MPF-II, in the Monitor:  9FF0.BFFFR  then  9FF0G
"""

import argparse
from pathlib import Path

SCREEN_SIZE = 8192
STUB_SIZE = 16

PAGES = {
    1: {"screen": 0x2000, "switch": 0xC054},
    2: {"screen": 0xA000, "switch": 0xC055},
}
GRAPHICS_SWITCH = 0xC050

OP_LDA_ABS = 0xAD
OP_JMP_ABS = 0x4C


def _abs(opcode: int, address: int) -> bytes:
    return bytes([opcode, address & 0xFF, address >> 8])


def build_viewer(page: int) -> tuple[bytes, int]:
    """Returns (16-byte viewer, load address) for hi-res page 1 or 2."""
    screen = PAGES[page]["screen"]
    start = screen - STUB_SIZE
    code = _abs(OP_LDA_ABS, GRAPHICS_SWITCH) + _abs(OP_LDA_ABS, PAGES[page]["switch"])
    loop = start + len(code)
    code += _abs(OP_JMP_ABS, loop)
    return code.ljust(STUB_SIZE, b"\x00"), start


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bundle an 8 KB hi-res picture with a viewer for the MPF-II."
    )
    parser.add_argument("input", type=Path, help="8 KB hi-res picture")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output binary (default: input name with _demo.bin)",
    )
    parser.add_argument(
        "-p",
        "--page",
        type=int,
        choices=(1, 2),
        default=2,
        help="hi-res page to show the picture on (default 2)",
    )
    args = parser.parse_args()

    picture = args.input.read_bytes()
    if len(picture) != SCREEN_SIZE:
        parser.error(f"Expected {SCREEN_SIZE} bytes, got {len(picture)}.")

    viewer, start = build_viewer(args.page)
    data = viewer + picture
    end = start + len(data) - 1
    out_path = args.output or args.input.with_name(args.input.stem + "_demo.bin")
    out_path.write_bytes(data)

    print(
        f"Saved: {out_path} ({len(data)} bytes, ${start:04X}-${end:04X}, "
        f"picture on page {args.page})"
    )
    print(f"Make the tape:  python3 mpf2wav.py {out_path.name} -s {start:04X}")
    print(
        f"MPF-II Monitor: {start:04X}.{end:04X}R  then  {start:04X}G  "
        "(RESET to exit)"
    )


if __name__ == "__main__":
    main()

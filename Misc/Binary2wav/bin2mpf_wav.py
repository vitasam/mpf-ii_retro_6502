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

"""Convert a binary file into a Multitech MPF-II cassette .wav file.

Verified on real hardware (MPF-II Monitor `R` command).

Tape layout
-----------
  pilot       4400 cycles of bit1 (~4.3 s)
  each block  sync half-cycles (63 before the header, 65 before each data
              block) + one full bit0 start cycle + bytes, MSB first

  header      name[6] | type | 00 | start lo,hi | end lo,hi | csum    (13 bytes)
  data n      name[6] | type | n  | up to 256 data bytes    | csum    (n = 1, 2, ...)

  name   up to 6 characters, uppercased, high bit set, padded with $A0
  type   $02 = binary (Monitor) file
  csum   XOR of every preceding byte of the block, seeded with $FF
  The last data block is short (no padding). There is no gap between blocks:
  the next block's sync follows the previous checksum directly.
  The file ends with one bit1 cycle and 0.5 s of silence.

Signal
------
  One bit = one full cycle. Half-cycles: bit0 235 us, bit1 485 us, sync 650 us.
  The MPF-II output is a flip-flop that toggles every half-cycle, so the wave
  is a square wave. Edge times are rounded from an exact running total, so
  rounding error never accumulates over long files.

  Output: mono WAV, 44100 Hz by default, 8-bit unsigned ($00/$FF, silence
  $80) or 16-bit signed (+/-32767) with --16bit.

Usage
-----
  python3 mpf2wav.py program.bin -s 4000 -n HELLO
  then on the MPF-II, in the Monitor, type the load command the script
  prints (e.g. 4000.412BR) and start playback.

  Note: $2000-$3FFF is hi-res page 1, where the Monitor draws its text, so
  data loaded there is overwritten when the Monitor prints. Use another
  address for test loads.
"""

import argparse
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 44100
BLOCK_SIZE = 256
FILE_TYPE_BINARY = 0x02

BIT0_US = 235
BIT1_US = 485
SYNC_US = 650

PILOT_CYCLES = 4400
HEADER_SYNC_HALVES = 63
DATA_SYNC_HALVES = 65


class SquareWave:
    """Generates the MPF-II cassette signal as a toggling square wave."""

    def __init__(self, sample_rate: int, sixteen_bit: bool, invert: bool) -> None:
        self.sample_rate = sample_rate
        self.sixteen_bit = sixteen_bit
        self.level = invert  # False = start LOW, True = start HIGH
        self._time = 0.0  # exact elapsed time, in samples
        self._written = 0  # samples written so far
        self.pcm = bytearray()
        if sixteen_bit:
            self._high, self._low = struct.pack("<h", 32767), struct.pack("<h", -32767)
            self._silence = struct.pack("<h", 0)
        else:
            self._high, self._low, self._silence = b"\xff", b"\x00", b"\x80"

    def half_cycle(self, us: float) -> None:
        self._time += us * self.sample_rate / 1_000_000
        end = int(self._time + 0.5)
        self.pcm += (self._high if self.level else self._low) * (end - self._written)
        self._written = end
        self.level = not self.level

    def cycle(self, us: float) -> None:
        self.half_cycle(us)
        self.half_cycle(us)

    def byte(self, value: int) -> None:
        for shift in range(7, -1, -1):
            self.cycle(BIT1_US if (value >> shift) & 1 else BIT0_US)

    def block(self, payload: bytes, sync_halves: int) -> None:
        """Writes sync, start bit, payload and the $FF-seeded XOR checksum."""
        for _ in range(sync_halves):
            self.half_cycle(SYNC_US)
        self.cycle(BIT0_US)  # start bit
        checksum = 0xFF
        for value in payload:
            checksum ^= value
        for value in payload + bytes([checksum]):
            self.byte(value)

    def silence(self, seconds: float) -> None:
        n = int(seconds * self.sample_rate)
        self.pcm += self._silence * n
        self._written += n
        self._time += n

    @property
    def duration(self) -> float:
        return self._written / self.sample_rate


def encode_name(name: str) -> bytes:
    """Returns the 6-byte tape name: uppercase, high bit set, $A0-padded."""
    clean = name.upper()
    if len(clean) > 6:
        raise ValueError(f"Tape name {name!r} is longer than 6 characters.")
    if any(not (0x20 <= ord(ch) < 0x7F) for ch in clean):
        raise ValueError(f"Tape name {name!r} must be printable ASCII.")
    return bytes(ord(ch) | 0x80 for ch in clean.ljust(6))


def build_mpf2_tape(
    data: bytes,
    start_addr: int,
    name: str = "",
    sample_rate: int = SAMPLE_RATE,
    sixteen_bit: bool = False,
    invert: bool = False,
    pilot_cycles: int = PILOT_CYCLES,
) -> tuple[bytes, int, int, float]:
    """Builds the PCM data for one MPF-II tape file.

    Returns (pcm, end_addr, data_block_count, duration_seconds).
    """
    if not data:
        raise ValueError("Input file is empty.")
    if not 0 <= start_addr <= 0xFFFF:
        raise ValueError(f"Start address ${start_addr:X} is outside $0000-$FFFF.")
    end_addr = start_addr + len(data) - 1
    if end_addr > 0xFFFF:
        raise ValueError(f"File ends at ${end_addr:X}, past $FFFF.")
    blocks = (len(data) + BLOCK_SIZE - 1) // BLOCK_SIZE
    if blocks > 255:
        raise ValueError("File needs more than 255 data blocks.")

    tape_name = encode_name(name)
    tape = SquareWave(sample_rate, sixteen_bit, invert)

    for _ in range(pilot_cycles):
        tape.cycle(BIT1_US)

    header = (
        tape_name
        + bytes([FILE_TYPE_BINARY, 0])
        + struct.pack("<HH", start_addr, end_addr)
    )
    tape.block(header, HEADER_SYNC_HALVES)

    for number, offset in enumerate(range(0, len(data), BLOCK_SIZE), start=1):
        chunk = data[offset : offset + BLOCK_SIZE]
        tape.block(
            tape_name + bytes([FILE_TYPE_BINARY, number]) + chunk, DATA_SYNC_HALVES
        )

    tape.cycle(BIT1_US)  # clean final edge
    tape.silence(0.5)
    return bytes(tape.pcm), end_addr, blocks, tape.duration


def write_wav(path: Path, pcm: bytes, sample_rate: int, sixteen_bit: bool) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2 if sixteen_bit else 1)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm)


def parse_hex(text: str) -> int:
    text = text.strip()
    for prefix in ("$", "0x", "0X"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    return int(text, 16)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a binary file into an MPF-II cassette .wav file."
    )
    parser.add_argument("input", type=Path, help="input binary file")
    parser.add_argument(
        "-o", "--output", type=Path, help="output .wav (default: input name with .wav)"
    )
    parser.add_argument(
        "-s",
        "--start",
        default="2000",
        help="load address in hex, e.g. 2000, $2000, 0x2000 (default 2000)",
    )
    parser.add_argument(
        "-n",
        "--name",
        default="",
        help="tape file name, up to 6 characters (default: blank)",
    )
    parser.add_argument(
        "-r",
        "--rate",
        type=int,
        default=SAMPLE_RATE,
        help=f"sample rate in Hz (default {SAMPLE_RATE})",
    )
    parser.add_argument(
        "--16bit",
        dest="sixteen_bit",
        action="store_true",
        help="write 16-bit samples (default 8-bit)",
    )
    parser.add_argument("--invert", action="store_true", help="invert signal polarity")
    parser.add_argument(
        "--leader",
        type=int,
        default=PILOT_CYCLES,
        help=f"pilot length in cycles (default {PILOT_CYCLES}, ~1 ms each)",
    )
    args = parser.parse_args()

    if args.rate < 22050:
        print(
            f"Warning: {args.rate} Hz is too coarse for 235 us half-cycles; "
            "44100 Hz or higher is recommended."
        )

    data = args.input.read_bytes()
    start_addr = parse_hex(args.start)
    out_path = args.output or args.input.with_suffix(".wav")

    try:
        pcm, end_addr, blocks, duration = build_mpf2_tape(
            data,
            start_addr,
            name=args.name,
            sample_rate=args.rate,
            sixteen_bit=args.sixteen_bit,
            invert=args.invert,
            pilot_cycles=args.leader,
        )
    except ValueError as err:
        parser.error(str(err))

    write_wav(out_path, pcm, args.rate, args.sixteen_bit)
    print(
        f"Saved: {out_path} ({duration:.1f} s, {len(data)} bytes, "
        f"{blocks} data block(s))"
    )
    print(f"MPF-II Monitor load command: {start_addr:04X}.{end_addr:04X}R")


if __name__ == "__main__":
    main()

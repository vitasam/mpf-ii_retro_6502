import argparse
from pathlib import Path
import struct
import wave

SAMPLE_RATE = 44100
PAGE_SIZE = 256


class _ToggleWave:
    """Models the MPF-II $C020 cassette toggle flip-flop."""

    def __init__(self, sixteen_bit: bool, sample_rate: int, invert: bool) -> None:
        self.sixteen_bit = sixteen_bit
        self.sample_rate = sample_rate
        self.level = invert  # False = LOW first, True = HIGH first
        self.pcm = bytearray()

    def half_cycle(self, us: int) -> None:
        n = max(1, round(self.sample_rate * us / 1_000_000))
        if self.sixteen_bit:
            amp = 32767 if self.level else -32768
            self.pcm.extend(struct.pack("<h", amp) * n)
        else:
            self.pcm.extend((b"\xff" if self.level else b"\x00") * n)
        self.level = not self.level

    def full_cycle(self, us: int) -> None:
        self.half_cycle(us)
        self.half_cycle(us)

    def cycles(self, us: int, count: int) -> None:
        for _ in range(count):
            self.full_cycle(us)

    def half_cycles(self, us: int, count: int) -> None:
        for _ in range(count):
            self.half_cycle(us)

    def encode_bytes(self, buf: bytes, bit0_us: int, bit1_us: int) -> None:
        for byte in buf:
            for shift in range(7, -1, -1):
                self.full_cycle(bit1_us if ((byte >> shift) & 1) else bit0_us)


def _xor_checksum(buf: bytes, seed: int = 0x00) -> int:
    csum = seed
    for byte in buf:
        csum ^= byte
    return csum


def _encode_filename(name: str) -> bytes:
    clean = name.upper()[:6].ljust(6, " ")
    return bytes(ord(ch) | 0x80 for ch in clean)


def build_mpf2_wav(
    data: bytes,
    start_addr: int,
    name: str = "",
    sixteen_bit: bool = False,
    sample_rate: int = SAMPLE_RATE,
    leader_cycles: int = 4500,
    invert: bool = False,
) -> tuple[bytes, int]:
    if not data:
        raise ValueError("Input binary file is empty.")
    end_addr = start_addr + len(data) - 1
    if end_addr > 0xFFFF:
        raise ValueError(f"End address ${end_addr:X} exceeds 64 KB ($FFFF).")

    bit0_us = 235
    bit1_us = 485
    sync_us = 650

    fname_bytes = _encode_filename(name)
    hdr_body = (
        fname_bytes
        + b"\x01\x00"
        + start_addr.to_bytes(2, "little")
        + end_addr.to_bytes(2, "little")
    )
    hdr_block = hdr_body + bytes([_xor_checksum(hdr_body, seed=0xFF)])

    tw = _ToggleWave(sixteen_bit, sample_rate, invert)

    # 1. Pilot tone (~4.5s of ~1000 Hz)
    tw.cycles(bit1_us, leader_cycles)

    # 2. Block 1 (header): 63 sync half-cycles + '0' start bit + 13-byte header
    tw.half_cycles(sync_us, 63)
    tw.full_cycle(bit0_us)
    tw.encode_bytes(hdr_block, bit0_us, bit1_us)

    # 3. Data pages: 256 bytes per block, each with 65 sync half-cycles,
    #    '0' start bit, 6-byte filename, page data, page XOR checksum, and 16-cycle gap.
    total_csum = 0
    for offset in range(0, len(data), PAGE_SIZE):
        page_chunk = data[offset : offset + PAGE_SIZE]
        page_csum = _xor_checksum(page_chunk, seed=0x00)
        total_csum ^= page_csum
        page_block = fname_bytes + page_chunk + bytes([page_csum])

        tw.half_cycles(sync_us, 65)
        tw.full_cycle(bit0_us)
        tw.encode_bytes(page_block, bit0_us, bit1_us)
        tw.cycles(bit1_us, 16)

    silence = (b"\x00\x00" if sixteen_bit else b"\x80") * (sample_rate // 2)
    tw.pcm.extend(silence)
    return bytes(tw.pcm), total_csum


def write_wav_file(
    pcm_bytes: bytes, out_path: Path, sixteen_bit: bool, sample_rate: int
) -> None:
    with wave.open(str(out_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2 if sixteen_bit else 1)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a binary file into an MPF-II cassette .wav file."
    )
    parser.add_argument("input", type=Path, help="Path to input .bin file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path to output .wav file (default: <input>.wav)",
    )
    parser.add_argument(
        "-s",
        "--start",
        default="2000",
        help="Hex load start address (default: 2000)",
    )
    parser.add_argument(
        "-n",
        "--name",
        default="",
        help="Optional tape filename up to 6 characters (default: unnamed)",
    )
    parser.add_argument(
        "--16bit",
        dest="sixteen_bit",
        action="store_true",
        help="Write 16-bit signed PCM instead of 8-bit unsigned PCM",
    )
    parser.add_argument(
        "-r",
        "--rate",
        type=int,
        default=SAMPLE_RATE,
        help="Sample rate in Hz (default: 44100)",
    )
    parser.add_argument(
        "--leader",
        type=int,
        default=4500,
        help="Pilot tone cycle count (default: 4500)",
    )
    parser.add_argument(
        "--invert",
        action="store_true",
        help="Invert high/low polarity",
    )
    args = parser.parse_args()

    data = args.input.read_bytes()
    start_addr = int(args.start, 16)
    end_addr = start_addr + len(data) - 1
    out_path = args.output or args.input.with_suffix(".wav")

    pcm_bytes, csum = build_mpf2_wav(
        data,
        start_addr=start_addr,
        name=args.name,
        sixteen_bit=args.sixteen_bit,
        sample_rate=args.rate,
        leader_cycles=args.leader,
        invert=args.invert,
    )
    write_wav_file(
        pcm_bytes, out_path, sixteen_bit=args.sixteen_bit, sample_rate=args.rate
    )

    bytes_per_sample = 2 if args.sixteen_bit else 1
    duration = len(pcm_bytes) / (args.rate * bytes_per_sample)
    pages = (len(data) + PAGE_SIZE - 1) // PAGE_SIZE
    print(f"Saved: {out_path} ({duration:.1f}s, {pages} page(s), checksum=${csum:02X})")
    print(f"MPF-II Monitor load command: {start_addr:04X}.{end_addr:04X}R")


if __name__ == "__main__":
    main()

import argparse
from pathlib import Path
import wave

RATE = 44100


def pulse(hi_us: int, lo_us: int) -> bytes:
    hi = max(1, round(RATE * hi_us / 1_000_000))
    lo = max(1, round(RATE * lo_us / 1_000_000))
    return (b"\xff" * hi) + (b"\x00" * lo)


def encode_bytes(buf: bytes, bit0: bytes, bit1: bytes) -> bytearray:
    out = bytearray()
    for b in buf:
        for shift in range(7, -1, -1):
            out.extend(bit1 if ((b >> shift) & 1) else bit0)
    return out


def xor_sum(buf: bytes) -> int:
    csum = 0x00
    for b in buf:
        csum ^= b
    return csum


def write_mpf2_wav(data: bytes, out_path: Path, start_addr: int) -> None:
    bit0 = pulse(250, 250)
    bit1 = pulse(500, 500)
    sync_tone = pulse(650, 650)

    # Block 1: 10 zero bytes + 2-byte little-endian length + 1-byte XOR checksum
    hdr_body = (b"\x00" * 10) + len(data).to_bytes(2, "little")
    hdr_block = hdr_body + bytes([xor_sum(hdr_body)])

    # Block 2: 6 space bytes ($A0 x 6) + payload + 1-byte XOR checksum
    data_csum = xor_sum(data)
    data_block = (b"\xa0" * 6) + data + bytes([data_csum])

    out = bytearray()
    # 1. Leader tone (~4.5s of 1000 Hz)
    out.extend(bit1 * 4500)
    # 2. Block 1 (32 cycles of 650 us + '0' start bit + 13-byte header)
    out.extend(sync_tone * 32 + bit0)
    out.extend(encode_bytes(hdr_block, bit0, bit1))
    # 3. 120 ms 1000 Hz buffer while MPF-II prints '------ 00 00 WAIT',
    #    followed by exact 33-cycle 650 us sync + '0' start bit + Block 2
    out.extend(bit1 * 120 + sync_tone * 33 + bit0)
    out.extend(encode_bytes(data_block, bit0, bit1))
    # Trailing 1s + silence
    out.extend(bit1 * 15)
    out.extend(b"\x80" * (RATE // 2))

    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(RATE)
        w.writeframes(out)

    end_addr = start_addr + len(data) - 1
    print(f"Saved: {out_path} ({len(out) / RATE:.1f}s, checksum=${data_csum:02X})")
    print(f"MPF-II Monitor load command: {start_addr:04X}.{end_addr:04X}R")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert binary to native MPF-II WAV.")
    parser.add_argument(
        "input",
        type=Path,
        help="Input binary file",
    )
    parser.add_argument("-o", "--output", type=Path, help="Output .wav file")
    parser.add_argument(
        "-s",
        "--start",
        default="2000",
        help="Hex start address (default: 2000)",
    )
    args = parser.parse_args()

    data = args.input.read_bytes()
    out_path = args.output or args.input.with_suffix(".wav")
    write_mpf2_wav(data, out_path, int(args.start, 16))


if __name__ == "__main__":
    main()

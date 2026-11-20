import argparse
from pathlib import Path
import struct
import wave

SAMPLE_RATE = 44100


def _half_cycle_samples(
    us: int, high: bool, sixteen_bit: bool, sample_rate: int
) -> bytes:
  n = max(1, round(sample_rate * us / 1_000_000))
  if sixteen_bit:
    amp = 32767 if high else -32768
    return struct.pack("<h", amp) * n
  return (b"\xff" if high else b"\x00") * n


def _cycle(
    lo_us: int, hi_us: int, sixteen_bit: bool, sample_rate: int
) -> bytes:
  return _half_cycle_samples(
      lo_us, False, sixteen_bit, sample_rate
  ) + _half_cycle_samples(hi_us, True, sixteen_bit, sample_rate)


def _encode_bits(buf: bytes, bit0: bytes, bit1: bytes) -> bytearray:
  out = bytearray()
  for byte in buf:
    for shift in range(7, -1, -1):
      out.extend(bit1 if ((byte >> shift) & 1) else bit0)
  return out


def _xor_checksum(buf: bytes) -> int:
  csum = 0
  for byte in buf:
    csum ^= byte
  return csum


def build_mpf2_wav(
    data: bytes,
    start_addr: int,
    sixteen_bit: bool = False,
    sample_rate: int = SAMPLE_RATE,
) -> tuple[bytes, int]:
  # MPF-II tape timings:
  # - ~1000 Hz leader & '1' bit: ~500 us half-cycles
  # - '0' bit & start bit: ~250 us half-cycles
  # - Sync tone between leader/blocks: ~650 us half-cycles
  bit0 = _cycle(250, 250, sixteen_bit, sample_rate)
  bit1 = _cycle(500, 500, sixteen_bit, sample_rate)
  sync = _cycle(650, 650, sixteen_bit, sample_rate)
  silence = (b"\x00\x00" if sixteen_bit else b"\x80") * (sample_rate // 2)

  # Block 1: 10 zero bytes + 2-byte little-endian length + 1-byte XOR checksum
  hdr_body = (b"\x00" * 10) + len(data).to_bytes(2, "little")
  hdr_block = hdr_body + bytes([_xor_checksum(hdr_body)])

  # Block 2: 6 space bytes ($A0 x 6) + payload + 1-byte XOR checksum
  payload_csum = _xor_checksum(data)
  data_block = (b"\xa0" * 6) + data + bytes([payload_csum])

  pcm = bytearray()
  pcm.extend(bit1 * 4500)  # ~4.5s pilot tone
  pcm.extend(sync * 32 + bit0 + _encode_bits(hdr_block, bit0, bit1))
  pcm.extend(sync * 33 + bit0 + _encode_bits(data_block, bit0, bit1))
  pcm.extend(bit1 * 16)
  pcm.extend(silence)

  return bytes(pcm), payload_csum


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
      help="Hex load start address for display info (default: 2000)",
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
  args = parser.parse_args()

  data = args.input.read_bytes()
  start_addr = int(args.start, 16)
  end_addr = start_addr + len(data) - 1
  out_path = args.output or args.input.with_suffix(".wav")

  pcm_bytes, csum = build_mpf2_wav(
      data, start_addr, sixteen_bit=args.sixteen_bit, sample_rate=args.rate
  )
  write_wav_file(
      pcm_bytes, out_path, sixteen_bit=args.sixteen_bit, sample_rate=args.rate
  )

  bytes_per_sample = 2 if args.sixteen_bit else 1
  duration = len(pcm_bytes) / (args.rate * bytes_per_sample)
  print(f"Saved: {out_path} ({duration:.1f}s, checksum=${csum:02X})")
  print(f"MPF-II Monitor load command: {start_addr:04X}.{end_addr:04X}R")


if __name__ == "__main__":
  main()

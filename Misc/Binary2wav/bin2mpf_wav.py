import argparse
from pathlib import Path
import struct
import wave

SAMPLE_RATE = 44100


def _half_cycle_samples(
    us: int, high: bool, sixteen_bit: bool, sample_rate: int, invert: bool
) -> bytes:
  eff_high = (not high) if invert else high
  n = max(1, round(sample_rate * us / 1_000_000))
  if sixteen_bit:
    amp = 32767 if eff_high else -32768
    return struct.pack("<h", amp) * n
  return (b"\xff" if eff_high else b"\x00") * n


def _cycle(
    lo_us: int,
    hi_us: int,
    sixteen_bit: bool,
    sample_rate: int,
    invert: bool,
) -> bytes:
  return _half_cycle_samples(
      lo_us, False, sixteen_bit, sample_rate, invert
  ) + _half_cycle_samples(hi_us, True, sixteen_bit, sample_rate, invert)


def _encode_bits(buf: bytes, bit0: bytes, bit1: bytes) -> bytearray:
  out = bytearray()
  for byte in buf:
    for shift in range(7, -1, -1):
      out.extend(bit1 if ((byte >> shift) & 1) else bit0)
  return out


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
    sync2_cycles: int = 33,
    invert: bool = False,
) -> tuple[bytes, int]:
  if not data:
    raise ValueError("Input binary file is empty.")
  end_addr = start_addr + len(data) - 1
  if end_addr > 0xFFFF:
    raise ValueError(f"End address ${end_addr:X} exceeds 64 KB ($FFFF).")

  bit0 = _cycle(250, 250, sixteen_bit, sample_rate, invert)
  bit1 = _cycle(500, 500, sixteen_bit, sample_rate, invert)
  sync = _cycle(650, 650, sixteen_bit, sample_rate, invert)
  silence = (b"\x00\x00" if sixteen_bit else b"\x80") * (sample_rate // 2)

  # Block 1 (13-byte MPF-II header):
  #   [0..5]   6-char Apple ASCII filename ($A0-padded)
  #   [6]      $01 = Binary memory block ($00 = BASIC)
  #   [7]      $00
  #   [8..9]   Start address (little-endian)
  #   [10..11] End address (little-endian)
  #   [12]     $FF-seeded XOR checksum of bytes [0..11]
  fname_bytes = _encode_filename(name)
  hdr_body = (
      fname_bytes
      + b"\x01\x00"
      + start_addr.to_bytes(2, "little")
      + end_addr.to_bytes(2, "little")
  )
  hdr_block = hdr_body + bytes([_xor_checksum(hdr_body, seed=0xFF)])

  # Block 2 (data block):
  #   [0..5]   6-char Apple ASCII filename ($A0-padded)
  #   [6..N+5] Raw binary payload
  #   [N+6]    $00-seeded XOR checksum of payload
  payload_csum = _xor_checksum(data, seed=0x00)
  data_block = fname_bytes + data + bytes([payload_csum])

  pcm = bytearray()
  pcm.extend(bit1 * leader_cycles)
  pcm.extend(sync * 32 + bit0 + _encode_bits(hdr_block, bit0, bit1))
  pcm.extend(sync * sync2_cycles + bit0 + _encode_bits(data_block, bit0, bit1))
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
      "--sync2",
      type=int,
      default=33,
      help="Block 2 sync cycle count (default: 33)",
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
      sync2_cycles=args.sync2,
      invert=args.invert,
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
  

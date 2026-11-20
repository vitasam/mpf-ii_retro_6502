import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import wave

SOFT_SWITCHES = {
    0x50: "TXTCLR / Graphics (MPF-II: Color ON - OK)",
    0x51: "TXTSET / Text     (MPF-II: Monochrome - PATCH)",
    0x52: "MIXCLR / Full     (MPF-II: Cassette Motor A - PATCH)",
    0x53: "MIXSET / Mixed    (MPF-II: Cassette Motor A - PATCH)",
    0x54: "TXTPAGE1 / Page 1 (MPF-II: Page 1 $2000 - OK)",
    0x55: "TXTPAGE2 / Page 2 (MPF-II: Page 2 $A000 - CHECK)",
    0x56: "LORES             (MPF-II: Cassette Motor B - PATCH)",
    0x57: "HIRES             (MPF-II: Cassette Motor B - PATCH)",
}

# 6502 opcodes that take a 16-bit absolute address (LDA/LDX/LDY/STA/STX/STY/BIT/AND/ORA)
ABS_OPCODES = {0xAD, 0xAE, 0xAC, 0x8D, 0x8E, 0x8C, 0x2C, 0x2D, 0x2E, 0x0D, 0x0E}


def print_hex_block(data, base_addr, offset, length, label=None):
  if label:
    print(f"\n[{label}]")
  end = min(len(data), offset + length)
  for pos in range(offset, end, 16):
    chunk = data[pos : min(pos + 16, end)]
    hex_str = " ".join(f"{b:02X}" for b in chunk)
    asc_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
    print(f"  ${base_addr + pos:04X}: {hex_str:<47}  |{asc_str}|")


def inspect_binary(data, base_addr):
  size = len(data)
  end_addr = base_addr + size - 1
  print(f"File size : {size} bytes (${size:04X})")
  print(f"Mem range : ${base_addr:04X} - ${end_addr:04X}")

  # 1. Print first 128 bytes
  print_hex_block(
      data, base_addr, 0, 128, "First 128 bytes (Header / Entry Point)"
  )

  # 2. Check Apple II Hi-Res Page 1 screen holes for hidden demo code
  if size >= 0x0400:
    holes = [0x0078 + (i * 0x80) for i in range(8)]
    non_empty = [h for h in holes if any(b != 0x00 for b in data[h : h + 8])]
    if non_empty:
      print("\n[Non-zero Hi-Res Screen Holes (Possible Loader Code)]")
      for h in non_empty:
        print_hex_block(data, base_addr, h, 8)

  # 3. Scan for $C050-$C057 video soft-switch accesses
  hits = []
  for i in range(len(data) - 2):
    if (
        data[i] in ABS_OPCODES
        and data[i + 2] == 0xC0
        and data[i + 1] in SOFT_SWITCHES
    ):
      sw = data[i + 1]
      hits.append((base_addr + i, data[i], sw, SOFT_SWITCHES[sw]))

  if hits:
    print("\n[Detected $C050-$C057 Soft-Switch Instructions]")
    for addr, op, sw, desc in hits[:20]:
      print(f"  ${addr:04X}: {op:02X} {sw:02X} C0  ->  $C0{sw:02X} ({desc})")
    if len(hits) > 20:
      print(f"  ... and {len(hits) - 20} more occurrences.")


def write_wav(data, out_path: Path, start_addr: int, sample_rate: int = 44100):
  out = bytearray()

  def add_cycle(hi_us, lo_us):
    hi_n = max(1, round(sample_rate * hi_us / 1_000_000))
    lo_n = max(1, round(sample_rate * lo_us / 1_000_000))
    out.extend(b"\xe0" * hi_n)
    out.extend(b"\x20" * lo_n)

  # ~5s 770 Hz leader tone
  for _ in range(3850):
    add_cycle(650, 650)

  # Sync pulse
  add_cycle(200, 250)

  # Data + XOR checksum (initialized to $FF)
  csum = 0xFF
  for b in data:
    csum ^= b
    for bit in range(7, -1, -1):
      add_cycle(500, 500) if ((b >> bit) & 1) else add_cycle(250, 250)

  for bit in range(7, -1, -1):
    add_cycle(500, 500) if ((csum >> bit) & 1) else add_cycle(250, 250)

  out.extend(b"\x80" * (sample_rate // 2))

  with wave.open(str(out_path), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(1)
    w.setframerate(sample_rate)
    w.writeframes(out)

  end_addr = start_addr + len(data) - 1
  duration = len(out) / sample_rate
  print(f"\nSaved: {out_path} ({duration:.1f}s, checksum=${csum:02X})")
  print(f"MPF-II Monitor load command: {start_addr:04X}.{end_addr:04X}R")


def play_wav(wav_path: Path):
  path_str = str(wav_path)

  if sys.platform == "win32":
    import winsound

    winsound.PlaySound(path_str, winsound.SND_FILENAME)
  elif sys.platform == "darwin":
    subprocess.run(["afplay", path_str], check=True)
  else:
    player = shutil.which("paplay") or shutil.which("aplay")
    if not player:
      raise RuntimeError(
          "No audio player found (install alsa-utils or pulseaudio-utils)."
      )
    subprocess.run([player, path_str], check=True)


def main():
  parser = argparse.ArgumentParser(
      description="Inspect Apple II binary & convert to MPF-II WAV."
  )
  parser.add_argument("input", type=Path, help="Input binary file (e.g. monarch)")
  parser.add_argument(
      "-o", "--output", type=Path, help="Output .wav file (default: <input>.wav)"
  )
  parser.add_argument(
      "-s",
      "--start",
      default="2000",
      help="Hex load start address (default: 2000)",
  )
  parser.add_argument(
      "--split",
      action="store_true",
      help="Split 16KB into $2000-$3FFF (Page 1) and $A000-$BFFF (MPF-II Page 2)",
  )
  parser.add_argument(
      "--play",
      action="store_true",
      help="Play the generated WAV file(s) after creation",
  )
  args = parser.parse_args()

  data = args.input.read_bytes()
  start_addr = int(args.start, 16)
  inspect_binary(data, start_addr)

  base_out = args.output or args.input.with_suffix(".wav")
  generated_files = []

  if args.split and len(data) == 16384:
    p1_out = base_out.with_name(f"{base_out.stem}_p1{base_out.suffix}")
    p2_out = base_out.with_name(f"{base_out.stem}_p2{base_out.suffix}")
    write_wav(data[:8192], p1_out, 0x2000)
    write_wav(data[8192:], p2_out, 0xA000)
    generated_files.extend([p1_out, p2_out])
  else:
    write_wav(data, base_out, start_addr)
    generated_files.append(base_out)

  if args.play:
    for wav_file in generated_files:
      input(
          f"\nType the Monitor load command on MPF-II, then press Enter here to play {wav_file.name}..."
      )
      print("Playing leader tone — press RETURN on MPF-II within 2 seconds...")
      play_wav(wav_file)


if __name__ == "__main__":
  main()

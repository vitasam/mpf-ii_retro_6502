# MPF-II cassette and hi-res tools

Python tools for getting programs and pictures onto a **Multitech Micro-Professor II (MPF-II)**, an Apple II clone, through its cassette input.

| Tool | What it does |
|---|---|
| `mpf2wav.py` | Converts any binary into an MPF-II cassette `.wav` file |
| `dhgr2hgr.py` | Converts an Apple IIe double hi-res (DHGR) picture into a standard hi-res picture the MPF-II can show |
| `hgrdemo.py` | Bundles a hi-res picture with a tiny viewer program, so it loads and runs as one file |

All three are tested on real MPF-II hardware.

## Requirements

- Python 3.9 or later
- No extra packages (standard library only)

## Quick start: show a double hi-res picture on the MPF-II

```
python3 dhgr2hgr.py monarch_appleii.bin -o monarch.hgr --preview monarch.png
python3 hgrdemo.py monarch.hgr -o monarch_demo.bin
python3 mpf2wav.py monarch_demo.bin -s 9FF0 -n MONARC
```

On the MPF-II, in the Monitor:

1. Type `9FF0.BFFFR`, press RETURN, and play `monarch_demo.wav`.
2. When the status line shows `OK`, type `9FF0G` to show the picture.
3. Press RESET to return to the Monitor.

![mpf-ii_with_new_psu](../../Images/demo.jpg)

> **Note:** The Monarch butterfly picture used in these examples is not included
> in this repository. It is third-party artwork (the well-known butterfly from the
> Dazzledraw slideshow disk) and is not ours to redistribute. Any 16 KB Apple IIe
> double hi-res picture works the same way; use `--source-preview` to check that
> your file decodes correctly before converting it.

## mpf2wav.py

Converts a binary file into a `.wav` file in the MPF-II's native cassette format.

```
python3 mpf2wav.py program.bin -s 4000 -n HELLO
```

| Option | Meaning |
|---|---|
| `-s`, `--start` | Load address in hex: `4000`, `$4000` or `0x4000` (default `2000`) |
| `-n`, `--name` | Tape file name, up to 6 characters (default: blank) |
| `-o`, `--output` | Output file (default: input name with `.wav`) |
| `-r`, `--rate` | Sample rate in Hz (default 44100; 22050 or more recommended) |
| `--16bit` | Write 16-bit samples (default 8-bit) |
| `--invert` | Invert the signal polarity |
| `--leader` | Pilot tone length in cycles (default 4400, about 4.3 s) |

The script prints the Monitor command to load the file, for example `4000.412BR`. Type it in the MPF-II Monitor, press RETURN, and start playback. After a successful load, the status line shows the file name, the file type (`02`), the last block number in hex, and `OK`.

## dhgr2hgr.py

Converts a 16 KB Apple IIe double hi-res picture (560×192, 16 colors) into an 8 KB standard hi-res picture (280×192, 6 colors). The MPF-II has no double hi-res mode.

```
python3 dhgr2hgr.py picture.bin -o picture.hgr --preview picture.png
```

| Option | Meaning |
|---|---|
| `-o`, `--output` | Output file (default: input name with `.hgr`) |
| `--mono` | Dither to black and white instead of color |
| `--main-first` | The input has its main-memory half first (default: auxiliary half first, as in A2FC / Dazzledraw files) |
| `--preview` | Also write a PNG of the converted picture |
| `--source-preview` | Also write a PNG of the decoded double hi-res picture (useful to check the input) |

Colors that standard hi-res can't show, such as pink, are approximated by dithering with white, purple, blue, green and orange.

## hgrdemo.py

Puts a tiny viewer (9 bytes of 6502 code, padded to 16) in front of an 8 KB hi-res picture, giving one binary that loads with a single `R` command and runs with `G`.

```
python3 hgrdemo.py picture.hgr -o picture_demo.bin
```

| Option | Meaning |
|---|---|
| `-o`, `--output` | Output file (default: input name with `_demo.bin`) |
| `-p`, `--page` | Hi-res page for the picture: `2` (default, `$9FF0–$BFFF`) or `1` (`$1FF0–$3FFF`) |

The viewer switches to graphics mode (`$C050`), selects the picture's page (`$C055` or `$C054`), and then loops. Press RESET to exit. Page 2 is the default because the Monitor draws its text on page 1, which would overwrite part of the picture.

## MPF-II notes

**Tape format.** The tape starts with a pilot tone, then a 13-byte header block (name, type, start and end address), then data blocks of up to 256 bytes. Every block carries the 6-character name, the file type (`$02` for binary), a block number and an XOR checksum. Bits are full square-wave cycles: 235 µs half-cycles for 0, 485 µs for 1, and 650 µs for sync. The details are in the docstring of `mpf2wav.py`.

**Screen memory.** Hi-res page 1 is `$2000–$3FFF` and page 2 is `$A000–$BFFF`. The MPF-II has no hardware text mode: text, low-res and hi-res all share the same memory, and the Monitor draws its text into page 1. Data loaded at `$2000` is fine, but the rows the Monitor prints on get overwritten. Use another address, such as `$4000`, for test loads.

**Color.** The Monitor runs in text mode (`$C051`), which turns color off. To see a picture in color, read `$C050` (graphics mode): type `C050` at the Monitor prompt, or let `hgrdemo.py`'s viewer do it. If colors still don't appear on a color TV, the MPF-II manual describes a color trimmer screw on the main board, reachable from the bottom of the case.

**Soft switches** (from the MPF-II manual):

| Address | Function |
|---|---|
| `$C050` | Graphics mode (color on) |
| `$C051` | Text mode |
| `$C054` | Show page 1 |
| `$C055` | Show page 2 |

## License

MIT License. Copyright (c) 2026 The Random DIY. See the header of each script.
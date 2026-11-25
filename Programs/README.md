# Programs for MPF-II

Programs are in audio format (`.wav`). Play them from a PC, phone or digital recorder into the MPF-II's cassette input, the same way you would play a cassette tape. They were made with [`mpf2wav.py`](../Misc/MPF2Tools/).

## How to load

Every program loads at `$4000`. There are two ways to load and start it.

**From BASIC** (no addresses to type):
1. Type `LOADT` and press RETURN.
2. Play the `.wav` file. Wait until the status line shows the program name, the file type `02` and `OK`.
3. Type `CALL 16384` and press RETURN (`16384` = `$4000`).

**From the Monitor:**
1. Type the load command given for the program, for example `4000.4BC9R`, and press RETURN.
2. Play the `.wav` file and wait for `OK`.
3. Type `4000G` and press RETURN.

Press RESET to leave a program.

## Keyscan

A keyboard test. It shows which key of the keyboard matrix is pressed, so you can check that every key works.

| | |
|---|---|
| Binary File | `keyscan.bin` | 
| Audio File | [`keyscan.wav`](keyscan.wav) (21 s) |
| Tape name | `KEYSCA` |
| Size | 3018 bytes, `$4000–$4BC9` |
| Load from BASIC | `LOADT`, then `CALL 16384` |
| Load from Monitor | `4000.4BC9R`, then `4000G` |

### What you see

The screen is in black-and-white hi-res mode. It shows:

- **ROW 0–7**: one line per keyboard row. Six cells show bits 0–5 of that row: `.` when the key is up, `#` when it is down. Next to them are the raw value read from the keyboard port and the keys that belong to each bit (`SH` = Shift, `SP` = Space, `LT`/`RT`/`DN`/`UP` = arrows, `CR` = Return).
- **CTRL**: `1` while the Ctrl key is held.
- **LAST KEY**: the name and code of the last key pressed, and a **COUNT** of key presses in hex.

Press the keys one at a time:
- The `#` should appear under the key's label.
- Each press should add exactly 1 to COUNT. If a single press adds more, the key contacts bounce.
- Ctrl does not change COUNT, because it is not part of the matrix.

### How the MPF-II keyboard works

The keyboard is not read like the Apple II's. The MPF-II has an 8-bit output port and an input port wired directly to the key matrix:

1. Write a row mask with one bit set (`$01`, `$02`, `$04` … `$80`) to **`$C000`**.
2. Read **`$C010`**. Bits 0–5 are the keys of the selected row, `1` = pressed. Bit 6 is the printer busy line and bit 7 the cassette input, so mask them off.

| Row | Mask | bit 0 | bit 1 | bit 2 | bit 3 | bit 4 | bit 5 |
|---|---|---|---|---|---|---|---|
| 0 | `$01` | SHIFT | B | V | C | X | Z |
| 1 | `$02` | – | G | F | D | S | A |
| 2 | `$04` | SPACE | T | R | E | W | Q |
| 3 | `$08` | ← | 5 | 4 | 3 | 2 | 1 |
| 4 | `$10` | → | 6 | 7 | 8 | 9 | 0 |
| 5 | `$20` | ↓ | Y | U | I | O | P |
| 6 | `$40` | ↑ | H | J | K | L | : |
| 7 | `$80` | RETURN | N | M | , | . | ? |

**Ctrl** is read separately: read `$C05F`, then `$C010` bit 0 is the Ctrl key; read `$C05E` to switch back to normal.

**RESET** is wired to the CPU reset line and is not part of the matrix.

## License

MIT License. Copyright (c) 2026 The Random DIY.
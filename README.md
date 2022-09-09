# MPF-II Micro-Professor 8-bit 6502 Retro Computer

**Microprofessor II** (**MPF II**), introduced in 1982, was Multitech's (later renamed [Acer](https://en.wikipedia.org/wiki/Acer_Inc.)) second branded computer product and also one of the [earliest](https://en.wikipedia.org/wiki/List_of_Apple_II_clones) [Apple II](https://en.wikipedia.org/wiki/Apple_II) clones. It does not look like most other computers.

![mpf-ii-plus-zx-taper](Photos/mpf-ii-plus-zx-taper.jpg)

## Technical information

- CPU: MOS Technology 6502
- Clock rate: 1 MHz
- RAM: 64 KB (including 16KB RAM mapped at the same address as the ROM)
- ROM: 16 KB (12 KB of which is a BASIC interpreter)
- Text modes: 40×24 (using graphics mode)
- Graphics modes: 280×192
- Colours: 8 colours
- Sound: 1 channel of 1-bit sound
- Connectors: Keyboard, Printer, Expansion port, cassette recorded input and output, Composite and TV-out
- Optional peripherals: 55 key full-size keyboard, Floppy disc drive, Thermal and Dot-matrix printers, Joystick
- Power supply: External PSU, 5,12V

## Differences to Apple II
- The MPF II was not totally compatible with the Apple II.
- The MPF II did not have Apple II's text mode. All the text was drawn on the screen by software rather than generated by hardware. It was the only cost-effective way to generate Chinese text on the screen at a time when a hardware-based Chinese character generator could cost hundreds of U.S. dollars.
- Like Apple II, MPF II had two graphics buffers. However, the second buffer was at address A000H while with Apple II it was at 4000H. The keyboard input was mapped to a different address than the Apple II making impossible to play Apple's games on the MPF II.
- MPF-II keyboard interface was very simple and consisted of an 8-bit output port and an input port that was directly connected to the keyboard matrix. The Apple joystick interface was not there, and instead, the joystick appeared as a keyboard with arrow keys and two other buttons.
- The external slot interface was also not compatible with the Apple II and could not use any standard interface cards including the Disk II controller.

([source](https://en.wikipedia.org/wiki/Microprofessor_II)).

## Backlog-list of making the MPF-II Micro-Professor computer fit for modern life:

- [ ] Modify [Apple II VGA Card](https://github.com/markadev/AppleII-VGA) project for MPF-II architecture. See [details.](VGA-card)

- [ ] Add MPF-II support in to [c2t](https://github.com/datajerk/c2t) utility. `c2t` is a command line tool that can convert binary code/data and/or Apple-1/II Monitor text, as well as 140K disk images, into audio files suitable for use with the Apple-1 and II (II, II+, //e) cassette interface.

- [x] Modify MIC output level to be compatible with an input of [ZXTapeRecorderV2](https://trolsoft.ru/en/sch/zx-tapper). See [details.](Docs/Modifications/MIC_level)

- [x] Printer Port Binary Data Loader (a proof-of-concept). See [details.](BasicDataLoader)

- [ ] Add a volume control to the speaker (because the speaker is very loud by default)





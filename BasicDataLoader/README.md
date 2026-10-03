# BASIC Binary Data Loader — Proof of Concept

## MPF-II Printer Port

On the left panel of the MPF-II, there is a connector marked `PRINTER`. This connector provides a parallel printer interface for the MPF-II printer or other printers with a parallel interface. The pinout of the printer connector is illustrated below:

![printer_port](../Images/printer_port.jpg)

Below is a description of an experiment for loading binary data into MPF-II memory using the STROBE and BUSY lines of the printer port and an Arduino as a server.

## Arduino Server Schematics

Since I had a [Nano Data Logger](https://publiclab.org/wiki/nano-data-logger) board lying around, I decided to use it for this purpose, in case I need the SD card interface or battery-operated real-time clock. The connection diagram of the OLED display, user-interface buttons, and MPF-II printer port is illustrated below:

![port_server_schematics](../Images/port_server_schematics.png)

## Load and Run 6502 Asm "Hello World"

Below is a "Hello World" assembly program example that uses the MPF-II standard Monitor subroutine `FDEDh` to output a character:

```hex
0400: A2 00 BD 11 04 C9 FF D0
0408: 01 60 20 ED FD E8 4C 02
0410: 04 C8 C5 CC CC CF A0 D7
0418: CF D2 CC C4 8D FF FF 00
```

Disassembled listing, using the [virtual 6502 disassembler](https://www.masswerk.at/6502/disassembler.html):

```assembly
                            * = $0000
0000   A2 00                LDX #$00
0002   BD 11 04             LDA $0411,X
0005   C9 FF                CMP #$FF
0007   D0 01                BNE L000A
0009   60                   RTS
000A   20 ED FD   L000A     JSR $FDED
000D   E8                   INX
000E   4C 02 04             JMP $0402
0011   C8                   INY
0012   C5 CC                CMP $CC
0014   CC CF A0             CPY $A0CF
0017   D7                   ???                ;11010111
0018   CF                   ???                ;11001111
0019   D2                   ???                ;11010010
001A   CC C4 8D             CPY $8DC4
001D   FF                   ???                ;11111111
001E   FF                   ???                ;11111111
001F   00                   BRK
                            .END

;auto-generated symbols and labels
 L000A        $0A
```

## Set Up Arduino Server

- Build and program the Arduino Nano with the following [code](BLoadServer.ino), where "Hello World" is hardcoded into a constant array of *unsigned int8* bytes.

- Set up the hardware according to the schematics.

- Power the board on. If everything is correct, the OLED display should show the `READY` message:

![arduino_server_start](../Images/arduino_server_start.jpg)

## BASIC Loader

- Enter the following BASIC [program](DLOA17.BAS) into the MPF-II, either manually or from the [.BAW](DLOA17.BAW) file using ZXTapeRecorder2.

- If everything is OK, the program should show the READY message:

![basic_start](../Images/basic_start.jpg)

## The "Protocol"

The protocol is a simplified SPI-like bus. The Arduino Server sets the current bit on the BUSY pin on every 0→1 strobe signal:

![getting_bytes_to_MPF](../Images/getting_bytes_to_MPF.png)

## Loading Process

- Press `ENTER` on the Arduino Server.

- Press `ENTER` on the MPF-II.

- Enjoy the slow process and press `ENTER` at the end:

![basic_loading_1](../Images/basic_loading_1.jpg)

![basic_loading_2](../Images/basic_loading_2.jpg)

![sent_oled](../Images/sent_oled.jpg)

## Conclusion

Theoretically, one can use the printer port for binary data loading, but there is little practical use in this case:

- The data transfer speed is slow (because the "protocol" uses large enough delays).

- There is no error control.

For full-fledged work, it is better to use a more advanced protocol (for example, Manchester [encoding](https://en.wikipedia.org/wiki/Manchester_code)) or use a [tool](https://github.com/datajerk/c2t) to convert binary data into a .WAV file (the MPF-II supports saving and loading data to cassette in Apple II format).
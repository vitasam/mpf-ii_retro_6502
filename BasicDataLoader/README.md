### BASIC Binary Data Loader, a Proof Of Concept

On the left panel of the MPF-II, there is a connector marked PRINTER. The connector provides printer interface to MPF-II printer or other printers with parallel interface. The pin-out of printer connector is illustrated below:

<img src="../Photos/printer_port.JPG" alt="printer_port" style="zoom:50%;" />

Below is a description of the experiment for loading binary data into MPF-II memory by using STROBE and BUSY lines of a printer port and Arduino as a server.

#### Arduino Server schematics

Since I had *Nano Data [Logger](https://publiclab.org/wiki/nano-data-logger)* board lying around, I decided to use it for these purposes, in case I will need SD-card interface or battery operated Real-Time clock. The connection diagram of OLED display, user-interface buttons and MPF-II printer port is illustrated below:

<img src="../Photos/port_server_schematics.png" alt="port_server_schematics" style="zoom:50%;" />

#### Load and run 6502 Asm "Hello World"

##### The Code

Below is  "Hello World" Asm program example that uses MPF-II standard Monitor subroutine (FDEDh) to output a character out:
```hex
0400: A2 00 BD 11 04 C9 FF D0
0408: 01 60 20 ED FD E8 4C 02
0410: 04 C8 C5 CC CC CF A0 D7
0418: CF D2 CC C4 8D FF FF 00
```
Disassembled listing, with a use of [virtual 6502 disassembler](https://www.masswerk.at/6502/disassembler.html):

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

##### Arduino Server

- Build and program Arduino Nano with following [code](https://gitlab.com/vitasam/mpf-ii-retro-computer/-/blob/main/BasicDataLoader/BLoadServer.ino), where "Hello World" is hardcoded in to constant array of *unsigned int8* bytes

- Sort the hardware out according to schematics
- Power the board on. If everything is correct the OLED display should show the READY-message:

<img src="../Photos/arduino_server_start.jpg" alt="arduino_server_start" style="zoom:50%;" />

##### BASIC Loader

- Enter the following BASIC [program](https://gitlab.com/vitasam/mpf-ii-retro-computer/-/blob/main/BasicDataLoader/DLOA17.BAS) in to MPF-II, either manually or from .[BAW](https://gitlab.com/vitasam/mpf-ii-retro-computer/-/blob/main/BasicDataLoader/DLOA17.BAW) file with [ZXTapeRecorder2](https://trolsoft.ru/en/sch/zx-tapper)

- If everything is Ok, the program should show the READY-message:

  <img src="../Photos/basic_start.jpg" alt="basic_start" style="zoom:50%;" />

  

##### The "protocol"

The protocol is a kind of simplified SPI bus, the Arduino Server sets a current bit on BUSY pin on every 0->1 strobe signal:

<img src="../Photos/getting_bytes_to_MPF.png" alt="getting_bytes_to_MPF" style="zoom:50%;" />

##### Loading Process

- Press ENTER on Arduino Server

- Press ENTER on MPF-II

- Enjoy the slow process and press ENTER in the end:

  <img src="../Photos/basic_loading_1.jpg" alt="basic_loading_1" style="zoom:40%;" />

  <img src="../Photos/basic_loading_2.jpg" alt="basic_loading_2" style="zoom:40%;" />

  <img src="../Photos/sent_oled.jpg" alt="sent_oled" style="zoom:40%;" />



#### Conclusion

Theoretically, one can use the printer port for binary data loading, but there is little practical use in this case:

- the data transfer speed is slow (because the "protocol" just uses big enough delays)

- there is no error control

For full-fledged work, it is better to use more advanced protocol (for example, Manchester [encoding](https://en.wikipedia.org/wiki/Manchester_code)) or use a [tool](https://github.com/datajerk/c2t) to convert a binary data in to .WAV file (MPF-II computer supports saving and loading data to cassette in Apple-II format)

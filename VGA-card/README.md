## Microprofessor-II VGA Card

This project is a VGA card for Microprofessor-II computers to output a crisp RGB signal to a VGA monitor instead of relying on the composite video output. This is accomplished by snooping the 6502 bus and creating a shadow copy of the video memory within a Raspberry Pi Pico, then processing the raw video memory contents to output a "perfect" signal.

The project is based on [Apple II VGA Card](https://github.com/markadev/AppleII-VGA) project.

* [Apple-II and MPF-II bus pinouts](../Docs/appli-ii_mpf-ii_bus_pinouts.pdf)
  
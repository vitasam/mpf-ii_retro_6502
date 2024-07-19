# Microprofessor-II VGA Card

This project is a VGA card for Microprofessor-II computers to output a crisp RGB signal to a VGA monitor instead of relying on the composite video output. This is accomplished by snooping the 6502 bus and creating a shadow copy of the video memory within a Raspberry Pi Pico, then processing the raw video memory contents to output a "perfect" signal.

The project is based on [Apple II VGA Card](https://github.com/markadev/AppleII-VGA) project.

## MPF-II to Apple II Bus Adapter Board

## Overview

This adapter board provides a physical interface between the MPF-II (Micro-Professor II) and Apple II expansion ecosystems. It adapts the MPF-II peripheral bus connector to an Apple II-style bus connector, potentially allowing MPF-II users to connect certain Apple II expansion cards and peripherals.

Important Note: This adapter provides a simple electrical connection between the two bus systems. It does not perform full signal or timing conversion from MPF-II to Apple II standards. Compatibility with Apple II peripherals may be limited and may require additional modifications or custom software/firmware solutions.

### Key Features

1. Physical Adaptation: Transforms the MPF-II bus connector layout to match the Apple II bus connector layout.

2. Potential Compatibility: May enable the use of some Apple II expansion cards on the MPF-II system, subject to compatibility limitations.

3. Vertical Expansion: Unlike the original MPF-II's horizontal expansion, this adapter allows for vertical plugging of extension cards, including VGA cards. This can lead to a more compact and flexible system setup.


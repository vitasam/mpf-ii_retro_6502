# MPF-II Modern Power Supply Replacement

![MPF-II Modern Power Supply Overview](../../Images/new_psu.jpg)

## Description

This modification replaces the original Multitech Micro-Professor II (MPF-II) power supply with a modern, high-efficiency switching power supply housed in a custom 3D-printed enclosure.

Aging original MPF-II power supplies suffer from degraded electrolytic capacitors, thermal inefficiency, and limited current capacity. Upgrading to a modern 66W triple-output AC/DC converter (`+5V`, `+12V`, `-5V`) ensures clean, stable power delivery and provides the necessary current headroom for power-hungry expansions such as:
* Floppy Disk Drive controller cards and floppy drives
* VGA video output cards
* Additional memory and peripheral expansions

---

## 3D-Printed Enclosure Files (STL)

<!-- Placeholder: Update relative paths (e.g., ./stl/filename.stl or ./filename.stl) to match your repository structure -->

| File | Description | Qty to Print |
| :--- | :--- | :---: |
| [`print_half_bottom_V03.stl`](../../Docs/3D/print_half_bottom_V03.stl) | Bottom shell half of the PSU enclosure | 1 |
| [`print_half_top_V03.stl`](../../Docs/3D/print_half_top_V03.stl) | Top shell half of the PSU enclosure | 1 |
| [`print_cap_in_V03.stl`](../../Docs/3D/print_cap_in_V03.stl) | Input-side end cap (AC mains / IEC C14 entry) | 1 |
| [`print_cap_out_V03.stl`](../../Docs/3D/print_cap_out_V03.stl) | Output-side end cap (DC output / cable gland) | 1 |
| [`print_gland_body_V03.stl`](../../Docs/3D/print_gland_body_V03.stl) | Strain-relief cable gland body | 1 |
| [`print_gland_dome_V03.stl`](../../Docs/3D/print_gland_dome_V03.stl) | Strain-relief cable gland dome / sealing nut | 1 |
| [`print_gland_nut_V03.stl`](../../Docs/3D/print_gland_nut_V03.stl) | Strain-relief cable gland locknut | 1 |

---

## Bill of Materials (BOM)

*Note: Quantities listed below reflect the exact order quantities from the build manifest (some components include spares or multi-packs).*

| Component / Description | Manufacturer Part Number | Distributor / Supplier | Supplier Part Number | Qty | Notes |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **AC/DC Converter 5V, 12V, -5V (66W)**      | `RT-65A` (Mean Well)       | DigiKey  | `1866-4310-ND`    | 1 | Main triple-output switching PSU |
| **Power Entry Module IEC320-C14 w/ Switch** | `BZM27/Z0000/53B` (Bulgin) | DigiKey  | `708-1878-ND`     | 1 | Panel-mount AC inlet with integrated rocker switch |
| **D-Sub Receptacle 9-Pos Solder Cup**       | `MHDB9SS`                  | DigiKey  | `4672-MHDB9SS-ND` | 1 | Female DB9 connector for DC power output |
| **D-Sub Backshell 9-Pos 180°**              | `40-9709H`                 | DigiKey  | `116-40-9709H-ND` | 1 | Cable hood/strain relief for DB9 connector |
| **M3x5.7 Heat-Set Threaded Inserts**        | `RX-M3x5.7` (`GE-M3X57-001`) | Ruthex | —                 | 6 | Brass threaded inserts for the 3D-printed enclosure  |
| **M3x30 DIN 965 Flat Head Screw** | — | — | — | 4 | Countersunk head screws for the enclosure |
| **M3x5 Stainless Steel Phillips Pan Head Screw** | — | — | — | 2 | Screws for mounting the PSU inside the enclosure |
| **4-Conductor Power Output Cable**          | —                          | Generic / Local | — | ~30 cm | 4 wires (`+5V`, `+12V`, `-5V`, `GND`), ~6–7 mm outer diameter to fit the cable gland |

---

## Wiring & Assembly Notes

> **⚠️ Safety Warning:** Working with mains AC voltage (`110V–240V AC`) carries a risk of electric shock or fire. Ensure all mains connections are properly insulated, verify continuity and ground bonding before applying power, and double-check output rail voltages (`+5V`, `+12V`, `-5V`) with a multimeter before connecting the PSU to the MPF-II mainboard.

* **3D-Printed Enclosure:** Install the Ruthex `M3x5.7` brass heat-set inserts into the designated mounting bosses using a soldering iron (recommended hole diameter: `3.5 - 4.0 mm`, minimum depth: `6.7 mm`).

* **DC Output Cable & Pinout:** Route the ~20-25 cm 4-core cable (`~6–7 mm` outer diameter) through the printed strain-relief cable gland (`print_gland_*`). Solder the wires to the `DB9` connector (`MHDB9SS`) and ensure the pinout strictly matches the original MPF-II power connector specification before plugging it into the computer:

![MPF-II DB9 Power Connector Pinout](../../Images/power_connector_pinout.jpg)

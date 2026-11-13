# Hardware

KiCad project for the `thriller` prototype board: Pango PG2L50H-6IFBG484, ST33KTPM2X TPM, QSPI NOR flash, ESP-PSRAM64H, YSN8130E RTC, LAN8742A, 2× NAU88C22, MicroSD, LCD, sensor and host connectors.
Built for JLCPCB assembly with LCSC-sourced parts.

| File | Contents |
|---|---|
| `thrilr_top.kicad_pro` | Project file (named after the root sheet, as KiCad expects) |
| `thrilr_top.kicad_sch` | Root sheet, A3: block diagram, design notes from the Logos2 hardware design guide (UG040012), sheet list, and the sheet symbols. No components |
| `power.kicad_sch` | 5 V input, always-on 3.3 V LDO, power control (WAKE, pushbutton, RTC alarm), step-down switchers for 1.0 V, 1.8 V and 3.3 V |
| `fpga_power.kicad_sch` | FPGA power pins and decoupling; unused HSST and VCCB handling |
| `fpga_config.kicad_sch` | Configuration bank, QSPI config flash, JTAG, oscillator, WAKE and wake sources |
| `fpga_io.kicad_sch` | I/O banks with hierarchical labels to the peripheral sheets |
| `secure.kicad_sch` | ST33KTPM2X TPM on SPI with its reset from the FPGA (3V3, inside the FIPS boundary); YSN8130E RTC on I2C on the always-on rail |
| `memory.kicad_sch` | QSPI NOR, PSRAM, MicroSD |
| `ethernet.kicad_sch` | RMII PHY and RJ45 |
| `audio.kicad_sch` | CODECs, front-end connectors, speaker |
| `display_ui.kicad_sch` | LCD, buttons, LEDs, enclosure switch |
| `sensor_host.kicad_sch` | Sensor connector and link interface, USB-C and USB-UART |

The FPGA symbol is in `../fpga/logos2/KiCAD/`. The sub-sheets are placeholders with a one-line description each; the sheet split is a first guess.

The files were written in the KiCad 9 schematic format (version 20250114); KiCad 10 opens them and converts on save.

Power architecture: 5 V is always on. A low-quiescent 3.3 V LDO (3V3_AO) powers the RTC and the power-control logic; the TPM runs from the switched 3.3 V with the FPGA, since all its state is non-volatile. The switchers are enabled by WAKE from the FPGA, the power
pushbutton, or the RTC's open-drain /INT; the boot ROM asserts WAKE early, the loader clears the alarm flag, and power-down is the loader programming the next alarm and dropping WAKE (`../doc/hw.md`, Real-time clock).

TPM connection (`../doc/tpm.md`, Part): SPI from the loader domain's bank, `CS` with the 56 pF capacitor ST recommends so `SPI_CLK` is low at the falling edge of `CS`, optional 33 Ω series
resistors; `RST` driven by an FPGA output with a pull-down, so the TPM stays in reset until the boot ROM runs; `GPI_I2C_Select` open (SPI); `GPIO_PP` at its internal pull-down; `PIRQ`
unconnected; 100 nF plus 1 µF on VCC; exposed pad to ground. The dashed outline on the top sheet is the tamper-evident region around the FPGA and the TPM, the two FIPS 140-3 modules
(`../doc/fips.md`, boundary B); the flash sits in its notch, outside both.

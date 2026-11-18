# KiCad: Logos2 symbols and the thriller module schematic

| Path | Contents |
|---|---|
| `FPGA_Pango_Logos2.kicad_sym` | Symbols for PG2L50H-6IFBG484 (earlier choice) and **PG2L50H-6IMBG324** (current). The 324 has eight units: banks L3, L4, L5, R4, R5; configuration/JTAG/ADC; core and auxiliary power; ground. Generated from `../pinout324.json` (ball → bank, pin name, pair) taken from the PK04006 pinout |
| `../pinout324.json` | Ball table of the 324 package |
| `../pinout324-assignment.csv` | Every ball with the net the module schematic puts on it (generated) |
| `thriller/` | **The module schematic** (`hw/module.md`): what is on the potted 20 × 40 mm card and nothing else |
| `tools/` | The scripts that produced the module schematic from the earlier one-board project, and the pinout tables |

## The module schematic (`thriller/`)

KiCad 9 format (version 20250114); KiCad 10 opens it and converts on save. Rev 0.2. Sheets:

| Sheet | File | Contents |
|---|---|---|
| Root | `thriller.kicad_sch` | Title, notes, the sheet symbols |
| Power Supplies | `th_power.kicad_sch` | 5 V from J1 (`+5V_IN`), PTC and TVS, 3V3_AO LDO, 1V0/1V8/3V3 bucks, power control from `PB_N_AO` and `RTC_INT_N_AO` |
| Base | `th_base.kicad_sch` | Configuration straps and filters, QSPI NOR flash, **ST33KTPM2X TPM** (SPI, RST pull-down), YSN8130E RTC with level shifting to the always-on rail, the **25 MHz oscillator** (`SYS_CLK`, the module's only clock) |
| FPGA banks L | `th_userA.kicad_sch` (A2) | Units L3, L4, L5 with their nets as global labels; bank decoupling |
| FPGA banks R | `th_userB.kicad_sch` (A2) | Units R4, R5; bank decoupling |
| FPGA config and power | `th_fpga.kicad_sch` | Configuration/JTAG/ADC unit, core and auxiliary power unit, ground unit; core decoupling |
| PSRAM | `th_storage.kicad_sch` | ESP-PSRAM64H (ciphertext only) |
| Ethernet PHY | `th_ext.kicad_sch` | LAN8742A on RMII, clocked from `SYS_CLK`; MDI pairs and LED lines go to J1 |
| Module connectors | `th_conn.kicad_sch` | J1 and J2, Hirose DF40C-80DP-0.4V(51), with the pinout in `hw/module-pinout.csv` |

What left the board when it became a module (all of it is now the carrier's): the USB-C and CH340N bridge, the two NAU88C22 CODECs and their jacks, the LCD and touch connector, the speaker driver,
the MicroSD socket, the RJ45 and magnetics, the sensor connector and its power switch, the SI5351A, the pushbutton and enclosure switch, the backup cells, the 5 V input jack and switched 5 V rail.
What was added: the two DF40 connectors, the TPM, the 25 MHz oscillator in place of the 24 MHz one and the PHY crystal.

### Bank assignment (324)

| Bank | Rail | What is on it |
|---|---|---|
| L5 (configuration) | 3V3 | QSPI flash data and `CS` (fixed-function balls), TPM SPI, PSRAM, RTC I2C and interrupt, `SYS_CLK` on the GSCLK ball |
| L4 | 3V3 | J2 audio (I2S × 2 with MCLK and I2C), LCD, touch, speaker PWM, carrier clocks on clock-capable balls, GPIO0..13 |
| L3 | 3V3 | Spare |
| R4 | 3V3 | PHY RMII with `ETH_REFCLK` on the GSCLK ball, SD, host UART, sensor link, pushbutton, tamper, seal loop, carrier ID, `PWR_HOLD`, `PGOOD` |
| R5 | 3V3 | GPIO14..31 |

The loader domain's pins (flash, TPM, PSRAM, RTC, the clock) are all on L5 so the partition's I/O stays inside one bank (`doc/fips.md`, F12).

### Things to check before layout

- H14: the TPM symbol's pin numbers against the ST33KTPM2X data sheet, and the `CS` capacitor and series resistors.
- H15: LAN8742A REF_CLK Out mode with an external 25 MHz clock on XTAL1.
- The core decoupling quantities on `th_fpga` against UG040012 tables 2-3 and 2-6 for the 324 package.
- `thriller_bom.csv` is from the one-board revision and is stale; regenerate from the schematic.

## tools/

| Script | What it does |
|---|---|
| `ksch.py` | Minimal KiCad 9 schematic s-expression toolkit: parse, serialize, pin geometry, net connectivity |
| `rework_module.py` | The one-board → module transformation. **Not idempotent**: run it from this directory on a clean `thriller/` (`git checkout thriller` first). It is kept as the record of what changed and why; from here on, edit the schematic in KiCad |
| `pinout_csv.py` | Writes `hw/module-pinout.csv` and `../pinout324-assignment.csv` from the assignments in `rework_module.py` |
| `render_sch.py` | Rough SVG/PNG preview of a sheet for checking generated geometry without KiCad |

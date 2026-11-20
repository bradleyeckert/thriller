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
| Power | `th_power.kicad_sch` (A3) | 5 V from J1, PTC and TVS, 3V3_AO LDO, 1V0/1V8/3V3 bucks, power control from `PB_N_AO` and `RTC_INT_N_AO`; the YSN8130E RTC; the FPGA's configuration/JTAG/ADC, core-power and ground units with their straps and decoupling |
| Base | `th_base.kicad_sch` | QSPI NOR flash, **ST33KTPM2X TPM** (SPI per DB5174 figure 3: RST pull-down, PIRQ pull-up, optional 56 pF on CS and 33 Ω series), ESP-PSRAM64H |
| FPGA banks | `th_userA.kicad_sch` (A3) | Units L3, L4, L5, R4, R5 with their nets as global labels; bank decoupling |
| Ethernet PHY | `th_ext.kicad_sch` | LAN8742A on RMII with the **25 MHz oscillator** (`SYS_CLK`, the module's only clock); MDI pairs and LED lines go to J1 |
| Module connectors | `th_conn.kicad_sch` | J1 and J2, Hirose DF40C-80DP-0.4V(51); the pinout is `hw/module-pinout.csv`, regenerated from this sheet by `tools/pinout_csv.py` |

What left the board when it became a module (all of it is now the carrier's): the USB-C and CH340N bridge, the two NAU88C22 CODECs and their jacks, the LCD and touch connector, the speaker driver,
the MicroSD socket, the RJ45 and magnetics, the sensor connector and its power switch, the SI5351A, the pushbutton and enclosure switch, the backup cells, the 5 V input jack and switched 5 V rail.
What was added: the two DF40 connectors, the TPM, the 25 MHz oscillator in place of the 24 MHz one and the PHY crystal.

### Bank assignment (324)

| Bank | Rail | What is on it |
|---|---|---|
| L5 (configuration) | 3V3 | QSPI flash data and `CS` (fixed-function balls), TPM SPI, PSRAM, RTC I2C and interrupt, `SYS_CLK` on the GSCLK ball |
| L4 | 3V3 | I2S × 2, LCD, touch interrupt, the carrier I2C (`SDA`/`SCL`), speaker PWM, the two carrier clocks on clock-capable balls, GPIO0..13 |
| L3 | 3V3 | GPIO32..41 (all ten of its I/O, the two VREF balls included; 3.3 V LVCMOS needs no VREF) |
| R4 | 3V3 | PHY RMII with `ETH_REFCLK` on the GSCLK ball, SD, host UART, sensor link, pushbutton, tamper, seal loop, `PWR_HOLD`, `PGOOD` |
| R5 | 3V3 | GPIO14..31 and GPIO42..59 (its VREF and clock-capable balls left free) |
| configuration | — | Straps, JTAG, `CFG_*`, `VCCB`, `VCCADC`, `ADC_5V_MON`, all on `th_power` |

The loader domain's pins (flash, TPM, PSRAM, RTC, the clock) are all on L5 so the partition's I/O stays inside one bank (`doc/fips.md`, F12).

### Things to check before layout

- The 3V3 rail's rise time at the TPM: DB5174 table 4 wants 2 V/ms or faster (H14).
- H15: LAN8742A REF_CLK Out mode with an external 25 MHz clock on XTAL1.
- Four stub wires on `th_userA` bank L4 (balls B13, B12, D12, B17) end in nothing; give them a net or a no-connect.
- The core decoupling quantities (now on `th_power`) against UG040012 tables 2-3 and 2-6 for the 324 package.
- `thriller_bom.csv` is from the one-board revision and is stale; regenerate from the schematic.

## tools/

| Script | What it does |
|---|---|
| `ksch.py` | Minimal KiCad 9 schematic s-expression toolkit: parse, serialize, pin geometry, net connectivity |
| `rework_module.py` | The one-board → module transformation of 2026-11-18 (its output was commit f718401; the schematic has been rearranged by hand since, so it is history, not a generator). Runs on the one-board revision (`git checkout f718401^ -- thriller`), reproducibly |
| `label_shapes.py` | Sets every global label's shape (input/output/bidirectional, the direction relative to the sheet it is on, from a per-net table of what the parts do) and 45 mil text. By default it only fills in labels still marked passive and keeps hand-set shapes; `--check` reports, `--force` applies the table everywhere |
| `edit_pins.py` | Text-level pin edits that keep eeschema's formatting (remove or add a global label with its stub, add or remove a no-connect); its `main` is the 2026-11-20 move of GPIO32..59 onto L3/R5 and the removal of `SENS_DET`, `SENS_27M`, `CARRIER_ID` |
| `pinout_csv.py` | Regenerates `hw/module-pinout.csv` from `th_conn` and the FPGA units (contact, net, ball, bank from the schematic; group, class and note kept from the existing CSV by net name), and `../pinout324-assignment.csv`. `--check` reports differences without writing |
| `render_sch.py` | Rough SVG/PNG preview of a sheet for checking generated geometry without KiCad |

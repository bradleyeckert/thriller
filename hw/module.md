# The thriller module

The chipset is a small mezzanine module: a 20 mm wide PCBA, about 40 mm long (as long as place-and-route needs), carrying two Hirose **DF40C-80DP-0.4V(51)** board-to-board connectors,
2 × 80 = 160 contacts at 0.4 mm pitch, mating with DF40 receptacles on the carrier. The card carries the FPGA, the TPM, the flash, the PSRAM, the RTC, the Ethernet PHY, the 25 MHz oscillator and the regulators, and is potted.
Everything with a connector, a transducer or a user interface sits on a **carrier**. The module is enrolled on a fixture carrier, stocked keyed, and installed in an application device under
tamper-evident seals (`doc/enrollment.md`). This document is the contract between the two boards: what is on which, what is potted, what crosses the connectors and under what rules, and what
the split changes in the security argument.

## Why a module

- **The module is the FIPS 140-3 module.** Boundary B (`doc/fips.md`) is the loader domain, the TPM and the flash, and that is the card. Its physical boundary is the potting, its ports are the
  connector contacts, and it is validated once for any number of carriers and application devices, none of which touch the validation.
- **A locked FPGA is swapped, not reworked.** A superseded, bricked or failed module unplugs from the carrier; the earlier plan accepted PCB rework.
- **Keys never meet the device factory.** Enrollment is a fixture carrier; enrolled modules are inventory; application-device assembly handles no secrets. Host enrollment happens later over the
  server, as already designed.
- **Power analysis stops at the regulators.** The carrier sees filtered 5 V; the FPGA's rails exist only under the potting.

## What is where

| On the module (potted) | FIPS standing | On the carrier (outside) |
|---|---|---|
| FPGA, PG2L50H-6IMBG324 (`../fpga/logos2/BGA.md`), with its heatsink | The loader domain is the module's logic; the supervisor and application domains are excluded logic on the same die | USB-C, 5 V in; the carrier's own 3.3 V regulator for its own parts |
| ST33KTPM2X TPM, on SPI with its reset from the FPGA | Embedded validated module (CMVP #5570) | MicroSD socket, TVS on the data lines |
| QSPI NOR flash, 32 MB | Module storage: ciphertext, public blobs, non-module images | FT2232H: UART, and JTAG on the fixture carrier only |
| Regulators: always-on 3.3 V LDO, 1.0 V, 1.8 V, 3.3 V switchers, power control (WAKE, PB, RTC alarm) | Module power; PGOOD and rail monitors feed the security block | Two SR44 cells for the RTC, through the `VBAT` finger |
| 25 MHz oscillator, clocking the FPGA's PLLs and the PHY | Security-relevant: the module's only clock source | RJ45 with magnetics; the MDI pairs cross the connector |
| LAN8742A PHY, RMII to the supervisor domain, reset from the security block | Excluded component | Sensor connector |
| ESP-PSRAM64H stream buffer | Excluded component (ciphertext only) | 2 × NAU88C22 CODECs, microphone front ends, speaker amplifier |
| YSN8130E RTC, on the supervisor's I2C, backup from `VBAT` | Excluded component (untrusted time; its alarm is a power control) | SI5351A clock generator and the 10 MHz reference input: application clocks only |
| Decoupling, pull resistors, the TPM's CS capacitor | — | LCD with touch, pushbutton, enclosure switch, seal loop |

Rule: a part goes on the module only if the module's security argument needs it under the potting (keys, clock, power, storage) or if it must sit within a few centimetres of the FPGA
(PSRAM, PHY). Everything else goes on the carrier, where it can change without touching the validated card.

## Potting

**What is potted:** the whole card, both sides, every component, with these exceptions:

- the two DF40 connectors and a keep-out around each for the mating receptacle, on the carrier-facing side; the potting on that side is kept below the mated height of the connector pair
  (the DF40 stack height is chosen for the carrier's receptacle variant, and the potting must not exceed it);
- the mounting holes, if the length warrants a standoff beyond the connectors;
- the heatsink's fins: the heatsink is bonded to the FPGA with thermal epoxy *before* potting, and the potting rises to its base plate, so the plate becomes part of the tamper-evident surface
  and the fins stay in the air.

**What is explicitly under the potting, and why:**

| Component | Reason |
|---|---|
| FPGA | The module's logic and the pairing keys |
| TPM, and the SPI traces to it | Keys, counters, identity; the bus carries encrypted parameters but also the HMAC exchanges a prober would like to interpose |
| QSPI flash, and its traces | Ciphertext, but a prober who can rewrite it can force fallbacks and recovery paths at will (R44) |
| Regulators and the FPGA's power planes | Keep the core rails out of reach of a power-analysis probe (R33) |
| 25 MHz oscillator | A swapped or driven clock is a glitching tool; the module's clock must be the module's own |
| PSRAM, PHY, RTC | Not security-relevant, but exposing them would require a window in the potting, and the PHY's reset line is the network policy's enforcement |
| Test points | There are none on the finished card; the fixture reaches everything through the connectors |

**Level 2 or Level 3.** For Level 2 the same geometry is covered by a tamper-evident coating or label set instead of hard potting, and the card stays reworkable at the factory. For Level 3 a
multi-chip embedded module must be covered by **hard, opaque potting** whose removal leaves evidence, so: a black, filled epoxy, Shore D in the 80s, opaque at visible wavelengths, with a
documented cure; underfill on the BGA (0.8 mm pitch) and the TPM's QFN before potting, so that thermal cycling of the hard compound does not fatigue the solder joints; and a potting shell
thickness the laboratory accepts (a few millimetres over the tallest part). Level 3 also asks for environmental failure protection or testing: the TPM monitors itself; the module adds rail
monitors into the security block and a temperature sensor the supervisor reads, and whether the Logos2 die exposes its own voltage or temperature sensing is a question for its documentation (H12).

**Heat.** A finned heatsink sized to the card (about 20 mm wide, as long as the card allows), bonded to the 15 × 15 mm BGA and overhanging the neighbouring parts above potting height,
dissipates the 1 to 2 W the module draws at perhaps 15 to 20 °C/W in still air: a 20 to 40 °C rise over ambient, so airflow or a thermal path from the heatsink to the enclosure is part of the carrier's design, acceptable in a device enclosure with any airflow. Potting conducts poorly (0.2 to 0.8 W/mK; thermally conductive
grades 1 to 2 W/mK), so the regulators rely on the ground planes and the heatsink, and the thermal design is checked with the chosen compound before the geometry is frozen (H12).

## The 160 contacts

The pinout is a **contract**: it is frozen before either module or carrier is laid out, every FPGA family's module presents the same one, and a change is a carrier revision. Counts by
group (individual pin numbers follow in `module-pinout.csv`; one connector carries power, the UART, JTAG, the card, the MDI pairs and the control lines, the other the audio, display, sensor,
clock and GPIO lines, so a minimal carrier can mate only the first):

| Group | Signals | Class | Notes |
|---|---|---|---|
| 5 V in, always on | 6 | Power | The only power the module takes. DF40 contacts are rated 0.3 A each, so six for margin |
| Ground | about 40 | Power | One ground contact adjacent to every signal group, and the DF40's ground plates where the variant has them; the return path for everything |
| `VBAT` | 1 | Power | RTC backup from the carrier's cells; its loss is the removal indicator (below) |
| MicroSD: CLK, CMD, D0 to D3, CD | 7 | Ciphertext | Driven by the supervisor's SD controller |
| UART: TX, RX | 2 | Ciphertext frames; plaintext status in recovery | The host UART, on the module (the boot ROM needs it) |
| JTAG: TCK, TMS, TDI, TDO | 4 | **Fixture only** | Connected on the fixture carrier; unconnected on production carriers; dead after the eFuse lock in any case |
| Ethernet MDI: TX±, RX±, two LEDs | 6 | Ciphertext (and the PHY's link) | The PHY is on the module, so RMII never leaves it and the network policy's reset is internal |
| I2S × 2: BCLK, LRCK, DIN, DOUT; MCLK; CODEC I2C | 11 | **Plaintext** | Accepted as before (R38), now with the connectors inside the device's seal |
| LCD SPI: SCK, MOSI, DC, CS, RST, backlight; touch I2C and IRQ | 9 | Plaintext | Supervisor and application domain |
| Speaker PWM | 1 | Plaintext | |
| Sensor link: TX, RX, power enable, detect | 4 | MAC'd frames | |
| Application clocks: SI5351A outputs, 10 MHz reference | 3 | Clock, untrusted | Enter the supervisor and application domains only; never the loader domain (Clocking, below) |
| Pushbutton, enclosure switch, seal loop (2), carrier identity (1-wire or I2C EEPROM) | 5 | Control | Tamper inputs into the security block; the seal loop opens when the application device is opened or the module is pulled |
| Carrier GPIO | 32 | Application | For carrier variants, no module change |
| Reserved | the remainder (about 20) | — | Unconnected on both sides until a pinout revision assigns them |

Rules:

1. **Nothing but signals leaves the module.** The carrier regulates its own 3.3 V from the 5 V input; the module's rails are never on a contact, so they cannot be loaded or probed from outside.
2. **Every plaintext line is one the old sealed board also carried in the clear**: I2S, LCD, touch, speaker. The split adds no new plaintext path; it makes the existing ones reachable through a
   mezzanine interposer, which is why the application device's seal must cover the module and its connectors (R38, R51).
3. **Misalignment must be harmless.** The two DF40 connectors are placed so the module cannot mate offset by one connector or rotated; the 5 V and ground contacts sit where a one-position
   misalignment shorts nothing.
4. **Fixture-only pins** (JTAG, and any test pins a family needs) are grouped, so a production carrier footprint can simply leave that region unrouted.
5. **Signal integrity** is undemanding (the fastest contact is SD at 50 MHz and the MDI pairs), but the MDI pairs get a ground contact each side and matched lengths.

## Clocking

The module's **25 MHz oscillator** is its only clock source: it drives the FPGA's PLLs (the core clock domain, the QSPI, the TPM SPI) and the PHY (which generates the 50 MHz RMII reference in
REF_CLK-out mode, or takes it from an FPGA PLL). It is under the potting. The security block's clock monitors watch the PLL lock and the reference frequency; loss of either is a lockdown cause.

Clocks that arrive from the carrier (the SI5351A outputs for audio and application use, the 10 MHz reference for sample-rate discipline) enter the supervisor and application domains only.
Nothing in the loader domain is clocked from a connector contact, and no core can reprogram the module's clock: the SI5351A is on the carrier's CODEC I2C, which belongs to the supervisor, and it clocks
nothing the module trusts.

## Which carrier the module is in

A module works in any carrier; that is the point of the split, and also its new risk: an enrolled module in an attacker's carrier records whatever that carrier's CODECs are fed, as an
authentic recording (R51). The module cannot authenticate a carrier by itself, so the design gives the server three signals and the owner one option:

1. **Removal is detectable.** The RTC's backup cells are on the carrier. Unplugging the module drops `VBAT`, the RTC's power-loss flag sets, and at the next boot the supervisor reads it and the
   module logs and attests *backup lost since last boot* (status block and `EVT_LIFECYCLE`, `doc/api.md`). A module that has been out of its carrier says so to every verifier until the event is acknowledged by the server.
2. **The seal loop and the enclosure switch** cross the connectors into the security block: opening the application device, or pulling the module, opens the loop, which is logged with the
   boot cause and, at Level 3, zeroizes.
3. **An installed state.** The server's `LIFECYCLE` message sets the *installed* bit in the TPM's lifecycle index when the module is commissioned in its application device, with a carrier
   identifier read from the carrier (a serial EEPROM; not an authenticator) recorded alongside. A later boot that reads a different identifier, or none, is reported.
4. **A carrier authenticator, if provenance of the analog front end must be cryptographic.** A small authentication IC on the carrier, challenged by the module each session, would let the
   module refuse to record in an unknown carrier. It is a product decision (H13), not a default: the three signals above make substitution visible, which is what the threat model asked for.

## Two carriers

| | Fixture carrier (breakout board) | Production carrier |
|---|---|---|
| Purpose | Bring-up, enrollment station, failure analysis before potting | The application device |
| JTAG | Connected to the FT2232H | Unrouted |
| Test access | Every contact on a header | None |
| Enrollment | Programs the FPGA's eFuses, runs the factory bitstream, provisions the TPM, installs the images, locks (`doc/enrollment.md`) | Receives an enrolled module |
| Seal loop, enclosure switch | Jumpered | Real |

Production order: assemble the card, test it unpotted on the fixture, bond the heatsink, underfill and pot, test again, then enroll through the connectors (potting happens before any key exists,
so a potting reject costs a board and no key material), stock, install, seal, commission (installed bit, host enrollment).

## What the split changes in the documents

- `doc/arch.md`: R38 names the connectors; R51 (carrier substitution) added; the physical boundary row names the potted card.
- `doc/fips.md`: the physical boundary is the potted module; the carrier is outside; EFP/EFT monitors on the module.
- `doc/hw.md`: the clock-source rule; the removal indicator; the seal loop and carrier identifier as inputs.
- `doc/tpm.md`: the *installed* lifecycle bit.
- `doc/api.md`: `backup_lost` and `carrier_id` in the status block; `EVT_LIFECYCLE` carries removal and carrier change.
- `hw/`: the KiCad project predates the split and draws one board; it is to be redrawn as `module/` and `carrier/` projects against the pinout contract.

## Open items

- H11: freeze the pinout (`module-pinout.csv`) across the two DF40 connectors, with the power-and-control connector sufficient for a minimal carrier.
- H12: potting compound, underfill, heatsink bond and the thermal check; rail and temperature monitors for EFP/EFT; whether the Logos2 die has its own sensors.
- H13: carrier authenticator, or the three removal signals alone.
- The DF40 receptacle variant on the carrier sets the stack height, and with it the potting allowed on the carrier-facing side; the heatsink goes on the other side.
